import hashlib
import hmac
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, UserRole, UserStatus
from apps.appointments.models import (
    Appointment,
    AppointmentHistory,
    AppointmentHistoryEventType,
    AppointmentStatus,
)
from apps.clinics.models import Clinic
from .exceptions import (
    CommissionCalculationException,
    PaymentConflictException,
    PaymentException,
    PaymentOrderException,
    PaymentSignatureException,
    PaymentVerificationException,
    ReservationExpiredException,
    WebhookVerificationException,
)
from .models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentAuditAction,
    PaymentAuditLog,
    PaymentStatus,
    PaymentWebhookEvent,
    WebhookProcessingStatus,
)

logger = logging.getLogger("apps.payments")


def rupees_to_paise(amount: Decimal) -> int:
    """
    Converts INR rupee amount (Decimal) to paise (smallest currency unit integer).
    Uses strict ROUND_HALF_UP arithmetic to prevent precision loss.
    """
    if amount is None or amount < Decimal("0.00"):
        raise ValueError(_("Amount must be a non-negative decimal value."))
    paise_decimal = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise_decimal)


def paise_to_rupees(paise: int) -> Decimal:
    """Converts paise integer to INR rupee Decimal quantized to 2 decimal places."""
    if paise is None or paise < 0:
        raise ValueError(_("Paise must be a non-negative integer."))
    return (Decimal(paise) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_commission(
    gross_amount: Decimal,
    clinic: Optional[Clinic] = None,
    custom_rate: Optional[Decimal] = None,
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Computes platform commission and clinic share using decimal arithmetic.
    Enforces the precedence rule:
      1. custom_rate if explicitly provided
      2. clinic.commission_rate if set on the clinic
      3. PLATFORM_DEFAULT_COMMISSION_RATE (default 5.00%)

    Enforces the accounting invariant:
      gross_amount == commission_amount + clinic_share

    Returns:
      Tuple[Decimal, Decimal, Decimal]: (commission_rate_snapshot, commission_amount, clinic_share)
    """
    if gross_amount is None or gross_amount < Decimal("0.00"):
        raise CommissionCalculationException(_("Gross amount cannot be negative or null."))

    # 1. Resolve applicable rate snapshot
    if custom_rate is not None:
        effective_rate = Decimal(str(custom_rate))
    elif clinic and clinic.commission_rate is not None:
        effective_rate = Decimal(str(clinic.commission_rate))
    else:
        default_rate = getattr(settings, "PLATFORM_DEFAULT_COMMISSION_RATE", Decimal("5.00"))
        effective_rate = Decimal(str(default_rate))

    # Validate range [0.00, 100.00]
    if effective_rate < Decimal("0.00") or effective_rate > Decimal("100.00"):
        raise CommissionCalculationException(
            _("Commission rate %(rate)s is outside permitted range (0.00 to 100.00).") % {"rate": effective_rate}
        )

    # 2. Financial calculation with ROUND_HALF_UP
    rate_factor = effective_rate / Decimal("100")
    commission_raw = gross_amount * rate_factor
    commission_amount = commission_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    clinic_share = gross_amount - commission_amount

    # 3. Assert invariant
    if commission_amount + clinic_share != gross_amount:
        raise CommissionCalculationException(_("Accounting invariant violated during commission calculation."))

    return effective_rate, commission_amount, clinic_share


def get_razorpay_client():
    """Instantiates the official Razorpay client with backend credentials."""
    import razorpay
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "rzp_test_placeholder_key_id")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "placeholder_secret_key")
    return razorpay.Client(auth=(key_id, key_secret))


def create_payment_order(
    patient: User,
    appointment_id: Any,
    idempotency_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> Payment:
    """
    Creates or reuses an idempotent Razorpay payment order for an eligible appointment.
    Derives amount strictly from trusted backend appointment snapshot.
    """
    if not patient or not patient.is_authenticated:
        raise PaymentOrderException(_("Authentication required to initiate payment."))
    if not patient.is_active or patient.status != UserStatus.ACTIVE:
        raise PaymentOrderException(_("Patient account is inactive or suspended."))

    with transaction.atomic():
        try:
            appointment = (
                Appointment.objects.select_for_update()
                .select_related("doctor", "clinic", "patient")
                .get(id=appointment_id)
            )
        except Appointment.DoesNotExist:
            raise PaymentOrderException(_("Appointment not found."))

        # Verify patient ownership
        if str(appointment.patient_id) != str(patient.id):
            raise PaymentOrderException(_("You do not have permission to pay for this appointment."))

        # Verify eligibility
        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
            raise PaymentOrderException(
                _("Cannot initiate payment for an appointment with status '%(status)s'.") % {"status": appointment.status}
            )

        # Check existing paid status
        if appointment.payment_status == PaymentStatus.PAID:
            raise PaymentOrderException(_("This appointment is already paid."))

        # Check reservation expiration
        if appointment.is_reservation_expired:
            raise ReservationExpiredException(_("Appointment reservation has expired. Please select a new slot."))

        # Determine trusted amount
        consultation_fee = appointment.consultation_fee
        if consultation_fee <= Decimal("0.00"):
            # Zero-fee consultation: mark NOT_REQUIRED immediately
            payment, is_created = Payment.objects.get_or_create(
                appointment=appointment,
                patient=patient,
                clinic=appointment.clinic,
                amount=Decimal("0.00"),
                currency=appointment.currency or "INR",
                gateway_order_id=f"free_order_{appointment.booking_reference}",
                defaults={"status": PaymentStatus.NOT_REQUIRED, "paid_at": timezone.now()},
            )
            appointment.payment_status = PaymentStatus.NOT_REQUIRED
            appointment.save(update_fields=["payment_status", "updated_at"])
            return payment

        # Idempotency check: Reuse existing active PENDING order if present
        existing_payment = Payment.objects.filter(
            appointment=appointment,
            patient=patient,
            status=PaymentStatus.PENDING,
        ).first()

        if existing_payment:
            if idempotency_key and existing_payment.idempotency_key != idempotency_key:
                # Same appointment with a new idempotency key: update the key
                existing_payment.idempotency_key = idempotency_key
                existing_payment.save(update_fields=["idempotency_key", "updated_at"])
            return existing_payment

        # Create Razorpay order via SDK
        if client is None:
            client = get_razorpay_client()

        amount_paise = rupees_to_paise(consultation_fee)
        order_payload = {
            "amount": amount_paise,
            "currency": appointment.currency or "INR",
            "receipt": f"rcpt_{appointment.booking_reference}",
            "notes": {
                "appointment_id": str(appointment.id),
                "booking_reference": appointment.booking_reference,
                "patient_id": str(patient.id),
                "clinic_id": str(appointment.clinic_id),
            },
        }

        try:
            razorpay_order = client.order.create(data=order_payload)
        except Exception as e:
            logger.error("Razorpay order creation failed for appointment %s: %s", appointment.id, str(e))
            raise PaymentOrderException(_("Failed to create order with payment gateway: %(err)s") % {"err": str(e)})

        gateway_order_id = razorpay_order.get("id")
        if not gateway_order_id:
            raise PaymentOrderException(_("Invalid response received from payment gateway."))

        # Persist Payment record
        payment = Payment.objects.create(
            appointment=appointment,
            patient=patient,
            clinic=appointment.clinic,
            gateway_name="RAZORPAY",
            gateway_order_id=gateway_order_id,
            amount=consultation_fee,
            currency=appointment.currency or "INR",
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            metadata={
                "receipt": razorpay_order.get("receipt", ""),
                "created_at_gateway": razorpay_order.get("created_at"),
            },
        )

        # Audit log
        PaymentAuditLog.objects.create(
            payment=payment,
            appointment=appointment,
            event_type=PaymentAuditAction.ORDER_CREATED,
            actor=patient,
            data={"gateway_order_id": gateway_order_id, "amount": str(consultation_fee)},
        )

        return payment


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    patient: Optional[User] = None,
    client: Optional[Any] = None,
) -> Payment:
    """
    Cryptographically verifies the payment signature and transitions the payment
    and appointment states atomically.
    Recognizes platform commission without duplication.
    Protects against late-payment slot conflicts.
    """
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        raise PaymentSignatureException(_("Missing payment verification parameters."))

    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    data_to_verify = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(key_secret.encode("utf-8"), data_to_verify, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature):
        # Audit invalid attempt if payment exists
        PaymentAuditLog.objects.create(
            event_type=PaymentAuditAction.PAYMENT_FAILED,
            actor=patient,
            data={"reason": "signature_mismatch", "order_id": razorpay_order_id, "payment_id": razorpay_payment_id},
        )
        raise PaymentSignatureException(_("Invalid payment signature."))

    with transaction.atomic():
        try:
            payment = (
                Payment.objects.select_for_update()
                .select_related("appointment", "clinic", "patient", "appointment__doctor")
                .get(gateway_order_id=razorpay_order_id)
            )
        except Payment.DoesNotExist:
            raise PaymentVerificationException(_("Payment record for this order was not found."))

        appointment = payment.appointment

        # Verify patient ownership if authenticated user provided
        if patient and str(payment.patient_id) != str(patient.id):
            raise PaymentVerificationException(_("You do not have permission to verify this payment."))

        # Idempotency: If already paid, return existing payment without duplicating commission
        if payment.status == PaymentStatus.PAID:
            logger.info("Payment %s is already verified and marked PAID.", payment.id)
            return payment

        # Verify amount & currency
        if payment.amount != appointment.consultation_fee:
            raise PaymentVerificationException(_("Payment amount mismatch with trusted appointment fee."))

        # Check late payment / slot collision scenario
        now_dt = timezone.now()
        is_expired = appointment.reservation_expires_at and appointment.reservation_expires_at <= now_dt
        slot_conflict = False

        if is_expired:
            # Check if doctor has another confirmed appointment in this slot
            blocking_conflict = Appointment.objects.filter(
                doctor=appointment.doctor,
                status__in=[AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED],
                start_at__lt=appointment.end_at,
                end_at__gt=appointment.start_at,
            ).exclude(id=appointment.id).exists()

            if blocking_conflict:
                slot_conflict = True

        if slot_conflict:
            # Late payment arrived after reservation expired and slot was taken by someone else
            payment.status = PaymentStatus.PAID
            payment.gateway_payment_id = razorpay_payment_id
            payment.gateway_signature = razorpay_signature
            payment.paid_at = now_dt
            payment.metadata["late_payment_conflict"] = True
            payment.metadata["manual_review_required"] = True
            payment.save(update_fields=["status", "gateway_payment_id", "gateway_signature", "paid_at", "metadata", "updated_at"])

            appointment.payment_status = PaymentStatus.PAID
            appointment.reschedule_required = True
            appointment.save(update_fields=["payment_status", "reschedule_required", "updated_at"])

            AppointmentHistory.objects.create(
                appointment=appointment,
                event_type=AppointmentHistoryEventType.LATE_PAYMENT_CONFLICT,
                previous_status=appointment.status,
                new_status=appointment.status,
                actor=patient,
                actor_role=UserRole.PATIENT if patient else "SYSTEM",
                reason="Payment received after reservation expired. Slot was claimed by another patient; flagged for reschedule/refund.",
            )

            PaymentAuditLog.objects.create(
                payment=payment,
                appointment=appointment,
                event_type=PaymentAuditAction.RECONCILIATION_DISCREPANCY,
                actor=patient,
                data={"reason": "late_payment_slot_conflict", "order_id": razorpay_order_id},
            )
            return payment

        # Standard successful verification
        payment.status = PaymentStatus.PAID
        payment.gateway_payment_id = razorpay_payment_id
        payment.gateway_signature = razorpay_signature
        payment.paid_at = now_dt
        payment.save(update_fields=["status", "gateway_payment_id", "gateway_signature", "paid_at", "updated_at"])

        # Confirm appointment
        prev_status = appointment.status
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.payment_status = PaymentStatus.PAID
        appointment.save(update_fields=["status", "payment_status", "updated_at"])

        # Calculate and record commission (idempotently)
        if not hasattr(payment, "commission_record"):
            rate_snap, comm_amt, clinic_net = calculate_commission(
                gross_amount=payment.amount,
                clinic=payment.clinic,
            )
            CommissionRecord.objects.create(
                payment=payment,
                appointment=appointment,
                clinic=payment.clinic,
                gross_amount=payment.amount,
                commission_rate=rate_snap,
                commission_amount=comm_amt,
                clinic_share=clinic_net,
                currency=payment.currency,
                status=CommissionStatus.PENDING_SETTLEMENT,
            )
            PaymentAuditLog.objects.create(
                payment=payment,
                appointment=appointment,
                event_type=PaymentAuditAction.COMMISSION_CALCULATED,
                actor=patient,
                data={
                    "rate": str(rate_snap),
                    "commission": str(comm_amt),
                    "clinic_share": str(clinic_net),
                },
            )

        # Record history & audit
        AppointmentHistory.objects.create(
            appointment=appointment,
            event_type=AppointmentHistoryEventType.PAYMENT_COMPLETED,
            previous_status=prev_status,
            new_status=AppointmentStatus.CONFIRMED,
            actor=patient,
            actor_role=UserRole.PATIENT if patient else "SYSTEM",
            reason=f"Payment verified successfully via Razorpay (Order: {razorpay_order_id}, Pay: {razorpay_payment_id})",
        )

        PaymentAuditLog.objects.create(
            payment=payment,
            appointment=appointment,
            event_type=PaymentAuditAction.PAYMENT_VERIFIED,
            actor=patient,
            data={"order_id": razorpay_order_id, "payment_id": razorpay_payment_id},
        )

        return payment


def process_razorpay_webhook(
    raw_body: bytes,
    signature: str,
    client: Optional[Any] = None,
) -> Tuple[PaymentWebhookEvent, bool]:
    """
    Validates webhook signature from raw request bytes and processes payment
    lifecycle events with strict idempotency and safe state machine transitions.
    """
    if not signature:
        raise WebhookVerificationException(_("Missing X-Razorpay-Signature header."))

    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    expected = hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning("Razorpay webhook signature verification failed.")
        raise WebhookVerificationException(_("Webhook signature verification failed."))

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        raise WebhookVerificationException(_("Malformed webhook JSON payload: %(err)s") % {"err": str(e)})

    event_id = payload.get("event_id") or payload.get("id")
    event_type = payload.get("event") or ""

    # Sanitize payload for audit storage (strip any credentials or tokens)
    sanitized_payload = {
        "event": event_type,
        "contains": payload.get("contains", []),
        "entity": payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id"),
        "order_id": payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id"),
        "amount": payload.get("payload", {}).get("payment", {}).get("entity", {}).get("amount"),
        "status": payload.get("payload", {}).get("payment", {}).get("entity", {}).get("status"),
    }

    with transaction.atomic():
        # Deduplication check
        if event_id:
            existing = PaymentWebhookEvent.objects.filter(event_id=event_id).first()
            if existing and existing.status == WebhookProcessingStatus.PROCESSED:
                logger.info("Webhook event %s already processed. Skipping.", event_id)
                return existing, False

        webhook_event = PaymentWebhookEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            status=WebhookProcessingStatus.RECEIVED,
            payload=sanitized_payload,
        )

        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id") or payload.get("payload", {}).get("order", {}).get("entity", {}).get("id")
        gateway_payment_id = payment_entity.get("id")

        if not order_id:
            webhook_event.status = WebhookProcessingStatus.IGNORED
            webhook_event.error_message = "No order_id associated with event"
            webhook_event.save(update_fields=["status", "error_message"])
            return webhook_event, True

        payment = Payment.objects.select_for_update().filter(gateway_order_id=order_id).first()
        if not payment:
            webhook_event.status = WebhookProcessingStatus.IGNORED
            webhook_event.error_message = f"No local payment found for order {order_id}"
            webhook_event.save(update_fields=["status", "error_message"])
            return webhook_event, True

        now_dt = timezone.now()

        if event_type in ("payment.captured", "order.paid"):
            # Avoid regressing or re-processing already PAID payment
            if payment.status != PaymentStatus.PAID:
                payment.status = PaymentStatus.PAID
                if gateway_payment_id:
                    payment.gateway_payment_id = gateway_payment_id
                payment.paid_at = now_dt
                payment.save(update_fields=["status", "gateway_payment_id", "paid_at", "updated_at"])

                # Confirm appointment
                appointment = payment.appointment
                prev_status = appointment.status
                appointment.status = AppointmentStatus.CONFIRMED
                appointment.payment_status = PaymentStatus.PAID
                appointment.save(update_fields=["status", "payment_status", "updated_at"])

                # Calculate commission
                if not hasattr(payment, "commission_record"):
                    rate_snap, comm_amt, clinic_net = calculate_commission(
                        gross_amount=payment.amount,
                        clinic=payment.clinic,
                    )
                    CommissionRecord.objects.create(
                        payment=payment,
                        appointment=appointment,
                        clinic=payment.clinic,
                        gross_amount=payment.amount,
                        commission_rate=rate_snap,
                        commission_amount=comm_amt,
                        clinic_share=clinic_net,
                        currency=payment.currency,
                        status=CommissionStatus.PENDING_SETTLEMENT,
                    )

                AppointmentHistory.objects.create(
                    appointment=appointment,
                    event_type=AppointmentHistoryEventType.PAYMENT_COMPLETED,
                    previous_status=prev_status,
                    new_status=AppointmentStatus.CONFIRMED,
                    reason=f"Payment captured via webhook: {event_type} ({gateway_payment_id})",
                )

                PaymentAuditLog.objects.create(
                    payment=payment,
                    appointment=payment.appointment,
                    event_type=PaymentAuditAction.WEBHOOK_PROCESSED,
                    data={"event_type": event_type, "order_id": order_id, "payment_id": gateway_payment_id},
                )

        elif event_type == "payment.failed":
            # Avoid regressing a PAID transaction to FAILED (safe state machine against out-of-order events)
            if payment.status == PaymentStatus.PAID:
                logger.warning("Ignoring payment.failed webhook for already PAID transaction %s", payment.id)
            else:
                error_code = payment_entity.get("error_code") or ""
                error_desc = payment_entity.get("error_description") or "Payment failed at gateway"
                payment.status = PaymentStatus.FAILED
                payment.failure_code = error_code[:100]
                payment.failure_description = error_desc[:500]
                payment.save(update_fields=["status", "failure_code", "failure_description", "updated_at"])

                payment.appointment.payment_status = PaymentStatus.FAILED
                payment.appointment.save(update_fields=["payment_status", "updated_at"])

                PaymentAuditLog.objects.create(
                    payment=payment,
                    appointment=payment.appointment,
                    event_type=PaymentAuditAction.PAYMENT_FAILED,
                    data={"error_code": error_code, "error_description": error_desc},
                )

        webhook_event.status = WebhookProcessingStatus.PROCESSED
        webhook_event.processed_at = now_dt
        webhook_event.save(update_fields=["status", "processed_at"])

        return webhook_event, True


def expire_pending_reservations() -> int:
    """
    Finds and expires pending reservations past their timeout.
    Cancels unconfirmed appointments and marks their pending payments as FAILED.
    Returns the count of expired reservations.
    """
    now_dt = timezone.now()
    expired_appts = Appointment.objects.filter(
        status=AppointmentStatus.PENDING_CONFIRMATION,
        reservation_expires_at__lte=now_dt,
    )

    count = 0
    for appt in expired_appts:
        with transaction.atomic():
            appt.status = AppointmentStatus.CANCELLED
            appt.cancellation_reason = "Reservation timed out without payment confirmation."
            appt.cancelled_at = now_dt
            appt.save(update_fields=["status", "cancellation_reason", "cancelled_at", "updated_at"])

            # Cancel associated pending payments
            Payment.objects.filter(
                appointment=appt,
                status=PaymentStatus.PENDING,
            ).update(
                status=PaymentStatus.FAILED,
                failure_code="RESERVATION_EXPIRED",
                failure_description="Payment window expired before completion.",
                updated_at=now_dt,
            )

            AppointmentHistory.objects.create(
                appointment=appt,
                event_type=AppointmentHistoryEventType.RESERVATION_EXPIRED,
                previous_status=AppointmentStatus.PENDING_CONFIRMATION,
                new_status=AppointmentStatus.CANCELLED,
                reason="Reservation timed out without payment completion.",
            )
            count += 1

    return count
