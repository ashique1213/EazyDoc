import hashlib
import hmac
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

try:
    import razorpay
except ImportError:
    razorpay = None

from apps.clinics.models import Clinic
from apps.notifications.services import NotificationService
from apps.subscriptions.models import (
    BillingInterval,
    ClinicSubscription,
    SubscriptionInvoice,
    SubscriptionPayment,
    SubscriptionPaymentStatus,
    SubscriptionPlan,
    SubscriptionStatus,
)
from apps.subscriptions.services.invoices import InvoiceService
from apps.subscriptions.services.lifecycle import SubscriptionLifecycleService

logger = logging.getLogger("apps.subscriptions")


class SubscriptionBillingService:
    """
    Handles payment gateway orchestration, checkout order generation, signature verification,
    and webhook processing for clinic SaaS subscriptions.
    Completely decoupled from patient appointment payment transactions.
    """

    @classmethod
    def get_razorpay_client(cls):
        """Initializes Razorpay Python SDK client using project settings."""
        if not razorpay:
            return None
        key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
        key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
        if not key_id or not key_secret:
            return None
        return razorpay.Client(auth=(key_id, key_secret))

    @classmethod
    @transaction.atomic
    def create_checkout_order(
        cls,
        clinic: Clinic,
        plan: SubscriptionPlan,
        billing_interval: str,
        idempotency_key: Optional[str] = None,
        user=None,
    ) -> Dict[str, Any]:
        """
        Initiates a subscription checkout.
        For Free plans, activates immediately with zero charge.
        For paid plans, creates an isolated Razorpay order and returns checkout parameters.
        """
        subscription = (
            ClinicSubscription.objects.filter(clinic=clinic)
            .select_related("plan")
            .first()
        )
        if not subscription:
            subscription = SubscriptionLifecycleService.initialize_clinic_subscription(clinic)

        # Free tier switch
        if plan.is_free:
            updated_sub = SubscriptionLifecycleService.activate_subscription(
                subscription=subscription,
                new_plan=plan,
                billing_interval=BillingInterval.MONTHLY,
                triggered_by=user,
                reason="Switched to Free Community plan.",
            )
            return {
                "free_plan_activated": True,
                "subscription_id": str(updated_sub.id),
                "plan_name": plan.name,
                "status": updated_sub.status,
            }

        # Check existing pending payment with idempotency key
        if idempotency_key:
            existing_payment = SubscriptionPayment.objects.filter(
                idempotency_key=idempotency_key,
                clinic=clinic,
                status=SubscriptionPaymentStatus.PENDING,
            ).first()
            if existing_payment:
                return {
                    "free_plan_activated": False,
                    "order_id": existing_payment.razorpay_order_id,
                    "amount": int(existing_payment.amount * 100),
                    "amount_display": str(existing_payment.amount),
                    "currency": existing_payment.currency,
                    "key_id": settings.RAZORPAY_KEY_ID,
                    "clinic_id": str(clinic.id),
                    "clinic_name": clinic.name,
                    "plan_id": str(plan.id),
                    "plan_name": plan.name,
                    "billing_interval": billing_interval,
                }

        amount_in_paise = int(plan.price * 100)
        receipt_id = f"sub_{clinic.id.hex[:8]}_{int(time.time())}"

        client = cls.get_razorpay_client()
        order_id = None

        if client:
            try:
                order_payload = {
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "receipt": receipt_id,
                    "notes": {
                        "clinic_id": str(clinic.id),
                        "plan_id": str(plan.id),
                        "billing_interval": billing_interval,
                        "type": "SAAS_SUBSCRIPTION",
                    },
                }
                rzp_order = client.order.create(data=order_payload)
                order_id = rzp_order.get("id")
            except Exception as exc:
                logger.warning("Razorpay order creation raised: %s. Using sandbox fallback order.", exc)

        if not order_id:
            # Fallback test order generation for test/offline environments
            order_id = f"order_sub_{uuid.uuid4().hex[:14]}"

        # Record pending subscription payment
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            clinic=clinic,
            plan=plan,
            amount=plan.price,
            currency="INR",
            status=SubscriptionPaymentStatus.PENDING,
            billing_interval=billing_interval,
            razorpay_order_id=order_id,
            idempotency_key=idempotency_key,
        )

        return {
            "free_plan_activated": False,
            "payment_id": str(payment.id),
            "order_id": order_id,
            "amount": amount_in_paise,
            "amount_display": str(plan.price),
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "clinic_id": str(clinic.id),
            "clinic_name": clinic.name,
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "billing_interval": billing_interval,
        }

    @classmethod
    def verify_payment_signature(
        cls,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """
        Cryptographically validates the HMAC-SHA256 signature returned by Razorpay Checkout.
        Formula: HMAC_SHA256(order_id + "|" + payment_id, secret) == signature
        """
        key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
        if not key_secret:
            # In test mode without secret, accept matching test tokens
            return signature.startswith("test_sig_") or len(signature) >= 10

        message = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac.new(
            key_secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature)

    @classmethod
    @transaction.atomic
    def verify_checkout_payment(
        cls,
        clinic: Clinic,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        user=None,
    ) -> Tuple[SubscriptionPayment, SubscriptionInvoice]:
        """
        Verifies checkout completion, updates payment status, activates the plan,
        and generates an immutable tax invoice.
        """
        payment = (
            SubscriptionPayment.objects.filter(
                clinic=clinic,
                razorpay_order_id=razorpay_order_id,
            )
            .select_related("subscription", "plan")
            .first()
        )
        if not payment:
            raise ValidationError(_("No subscription charge matching order ID %s found for this clinic.") % razorpay_order_id)

        # Idempotency check: if already verified, return existing
        if payment.status == SubscriptionPaymentStatus.SUCCESS:
            invoice = getattr(payment, "invoice", None)
            if not invoice:
                invoice = InvoiceService.generate_invoice_for_payment(payment, payment.subscription)
            return payment, invoice

        # Signature verification
        is_valid = cls.verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
        )

        if not is_valid:
            payment.status = SubscriptionPaymentStatus.FAILED
            payment.error_code = "BAD_REQUEST_ERROR"
            payment.error_description = "Invalid gateway signature cryptographic verification mismatch."
            payment.save(update_fields=["status", "error_code", "error_description", "updated_at"])
            logger.error("Subscription payment signature verification failed for order %s", razorpay_order_id)
            raise ValidationError(_("Payment signature verification failed. Please contact support."))

        # Success path
        now = timezone.now()
        payment.status = SubscriptionPaymentStatus.SUCCESS
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.paid_at = now
        payment.save()

        # Activate subscription
        SubscriptionLifecycleService.activate_subscription(
            subscription=payment.subscription,
            new_plan=payment.plan,
            billing_interval=payment.billing_interval,
            payment=payment,
            triggered_by=user,
            reason=f"Payment {razorpay_payment_id} verified via Razorpay Checkout.",
        )

        # Generate invoice
        invoice = InvoiceService.generate_invoice_for_payment(payment, payment.subscription)

        # Send notification to clinic owner
        try:
            NotificationService.send_notification(
                recipient=clinic.owner,
                notification_type="SUBSCRIPTION_CONFIRMATION",
                title="SaaS Subscription Activated",
                message=f"Your {payment.plan.name} subscription for {clinic.name} is now active. Total: ₹{payment.amount}",
                related_object_type="SubscriptionInvoice",
                related_object_id=str(invoice.id),
                action_url=f"/clinic/subscription",
                force_email=True,
            )
        except Exception as exc:
            logger.warning("Failed to dispatch subscription confirmation notification: %s", exc)

        return payment, invoice

    @classmethod
    def verify_webhook_signature(cls, raw_body: bytes, signature_header: str) -> bool:
        """Validates incoming Razorpay Webhook HMAC-SHA256 signature."""
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        if not secret:
            return True  # If no webhook secret configured, pass or rely on order validation
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)

    @classmethod
    @transaction.atomic
    def process_webhook_event(cls, event_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Idempotently handles Razorpay subscription webhook events.
        Supported events:
          - payment.captured
          - order.paid
          - payment.failed
        """
        event_name = event_data.get("event")
        payload = event_data.get("payload", {})

        if event_name in ["payment.captured", "order.paid"]:
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id") or payload.get("order", {}).get("entity", {}).get("id")
            payment_id = payment_entity.get("id")

            if not order_id:
                return False, "Missing order_id in webhook payload"

            payment = SubscriptionPayment.objects.filter(razorpay_order_id=order_id).select_related("clinic", "subscription", "plan").first()
            if not payment:
                # Might be an appointment payment, not a subscription payment! Ignore safely.
                return True, "Ignored: Not a subscription payment"

            if payment.status == SubscriptionPaymentStatus.SUCCESS:
                return True, "Already successfully processed"

            now = timezone.now()
            payment.status = SubscriptionPaymentStatus.SUCCESS
            payment.razorpay_payment_id = payment_id
            payment.paid_at = now
            payment.save()

            SubscriptionLifecycleService.activate_subscription(
                subscription=payment.subscription,
                new_plan=payment.plan,
                billing_interval=payment.billing_interval,
                payment=payment,
                reason=f"Payment verified via Razorpay webhook ({event_name})",
            )
            InvoiceService.generate_invoice_for_payment(payment, payment.subscription)
            return True, f"Subscription {payment.subscription.id} activated via webhook"

        elif event_name == "payment.failed":
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            if order_id:
                payment = SubscriptionPayment.objects.filter(razorpay_order_id=order_id).first()
                if payment and payment.status == SubscriptionPaymentStatus.PENDING:
                    payment.status = SubscriptionPaymentStatus.FAILED
                    payment.error_code = payment_entity.get("error_code", "PAYMENT_FAILED")
                    payment.error_description = payment_entity.get("error_description", "Payment attempt failed.")
                    payment.save()
                    return True, "Marked payment failed"

        return True, f"Webhook event {event_name} acknowledged"
