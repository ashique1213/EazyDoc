import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clinics.models import Clinic
from apps.subscriptions.models import (
    ClinicSubscription,
    SubscriptionInvoice,
    SubscriptionPlan,
)
from apps.subscriptions.permissions import IsClinicOwnerOrSuperAdmin
from apps.subscriptions.serializers import (
    ClinicSubscriptionSerializer,
    SubscriptionCancelRequestSerializer,
    SubscriptionCheckoutRequestSerializer,
    SubscriptionEventSerializer,
    SubscriptionInvoiceSerializer,
    SubscriptionPlanSerializer,
    SubscriptionVerifyPaymentRequestSerializer,
)
from apps.subscriptions.services.billing import SubscriptionBillingService
from apps.subscriptions.services.entitlements import EntitlementService
from apps.subscriptions.services.invoices import InvoiceService
from apps.subscriptions.services.lifecycle import SubscriptionLifecycleService

logger = logging.getLogger("apps.subscriptions")


class SubscriptionPlansListView(APIView):
    """
    Public and clinic-facing catalog listing all active, selectable SaaS subscription plans.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="List Subscription Plans",
        description="Returns all active SaaS plans (Free, Starter, Professional, Enterprise) and billing intervals.",
        responses={200: SubscriptionPlanSerializer(many=True)},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True, is_public=True).order_by("sort_order", "price")
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicSubscriptionDetailView(APIView):
    """
    Returns the active subscription, billing status, and real-time entitlement limits for a clinic.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="Retrieve Clinic Subscription & Entitlements",
        description="Returns plan status, trial information, and live quota usage for doctors, staff, and bookings.",
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        summary = EntitlementService.get_clinic_entitlements_summary(clinic)
        return Response(
            {
                "success": True,
                "data": summary,
            },
            status=status.HTTP_200_OK,
        )


class ClinicSubscriptionCheckoutView(APIView):
    """
    Initiates subscription purchase, upgrade, or interval change.
    Creates a Razorpay checkout order for paid plans, or immediately switches for Free plan.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="Create Subscription Checkout Order",
        description="Generates an isolated Razorpay order for clinic subscription checkout.",
        request=SubscriptionCheckoutRequestSerializer,
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        serializer = SubscriptionCheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = serializer.validated_data["plan_id"]
        billing_interval = serializer.validated_data["billing_interval"]
        idempotency_key = serializer.validated_data.get("idempotency_key")

        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

        try:
            checkout_data = SubscriptionBillingService.create_checkout_order(
                clinic=clinic,
                plan=plan,
                billing_interval=billing_interval,
                idempotency_key=idempotency_key,
                user=request.user,
            )
            return Response(
                {
                    "success": True,
                    "message": "Checkout order created successfully.",
                    "data": checkout_data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.error("Checkout creation failed: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class ClinicSubscriptionVerifyPaymentView(APIView):
    """
    Verifies Razorpay Checkout signature and activates clinic subscription.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="Verify Subscription Payment",
        description="Cryptographically verifies payment signature and activates the clinic's SaaS subscription.",
        request=SubscriptionVerifyPaymentRequestSerializer,
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        serializer = SubscriptionVerifyPaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data["razorpay_order_id"]
        payment_id = serializer.validated_data["razorpay_payment_id"]
        signature = serializer.validated_data["razorpay_signature"]

        try:
            payment, invoice = SubscriptionBillingService.verify_checkout_payment(
                clinic=clinic,
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=signature,
                user=request.user,
            )
            return Response(
                {
                    "success": True,
                    "message": "Payment verified and subscription activated successfully.",
                    "data": {
                        "payment_id": str(payment.id),
                        "invoice_id": str(invoice.id),
                        "invoice_number": invoice.invoice_number,
                        "plan_name": payment.plan.name,
                        "status": payment.subscription.status,
                        "current_period_end": payment.subscription.current_period_end.isoformat() if payment.subscription.current_period_end else None,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as exc:
            return Response(
                {
                    "success": False,
                    "message": exc.messages if hasattr(exc, "messages") else str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("Verification error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Payment verification failed. Please contact support.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class ClinicSubscriptionCancelView(APIView):
    """
    Requests subscription cancellation at period end.
    Access remains active until current_period_end.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="Cancel Subscription",
        description="Schedules cancellation at the end of the current billing cycle without immediate data deletion.",
        request=SubscriptionCancelRequestSerializer,
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        serializer = SubscriptionCancelRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        subscription = EntitlementService.get_clinic_subscription(clinic)
        try:
            updated_sub = SubscriptionLifecycleService.request_cancellation(
                subscription=subscription,
                reason=reason,
                triggered_by=request.user,
            )
            return Response(
                {
                    "success": True,
                    "message": "Cancellation scheduled. You maintain full access until your billing period ends.",
                    "data": ClinicSubscriptionSerializer(updated_sub).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ClinicSubscriptionInvoicesListView(APIView):
    """
    Lists past billing invoices for the clinic.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="List Clinic Invoices",
        description="Returns historical billing invoices and tax breakdowns for the clinic.",
        responses={200: SubscriptionInvoiceSerializer(many=True)},
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        invoices = SubscriptionInvoice.objects.filter(clinic=clinic).order_by("-created_at")
        serializer = SubscriptionInvoiceSerializer(invoices, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicSubscriptionInvoiceDetailView(APIView):
    """
    Retrieves full details for a single invoice.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="Get Invoice Detail",
        description="Returns line items and GST tax breakdown for a specific invoice.",
        responses={200: SubscriptionInvoiceSerializer},
    )
    def get(self, request, clinic_id, invoice_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        invoice = get_object_or_404(SubscriptionInvoice, id=invoice_id, clinic=clinic)
        serializer = SubscriptionInvoiceSerializer(invoice)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicSubscriptionInvoiceDownloadView(APIView):
    """
    Returns printable HTML view of the tax invoice for downloading or printing to PDF.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="Download Printable Invoice",
        description="Returns formatted standalone HTML invoice.",
    )
    def get(self, request, clinic_id, invoice_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        invoice = get_object_or_404(SubscriptionInvoice, id=invoice_id, clinic=clinic)
        html_content = InvoiceService.render_invoice_html(invoice)
        return HttpResponse(html_content, content_type="text/html; charset=utf-8")


class ClinicSubscriptionAuditLogsView(APIView):
    """
    Returns audit trail of subscription events for the clinic.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicOwnerOrSuperAdmin]

    @extend_schema(
        summary="List Subscription Events",
        description="Returns audit log of all plan changes, renewals, and cancellations for the clinic.",
        responses={200: SubscriptionEventSerializer(many=True)},
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        self.check_object_permissions(request, clinic)

        events = clinic.subscription_events.select_related("triggered_by").order_by("-created_at")[:50]
        serializer = SubscriptionEventSerializer(events, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
