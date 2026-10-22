import logging
from decimal import Decimal
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedUser, IsPatient
from apps.audit_logs.models import AuditLog
from apps.clinics.models import Clinic
from .exceptions import (
    PaymentException,
    PaymentOrderException,
    PaymentSignatureException,
    PaymentVerificationException,
    ReservationExpiredException,
    WebhookVerificationException,
)
from .models import CommissionRecord, Payment, PaymentStatus
from .serializers import (
    AdminClinicCommissionUpdateSerializer,
    ClinicCommissionRecordSerializer,
    CreatePaymentOrderInputSerializer,
    PatientPaymentStatusSerializer,
    PaymentOrderOutputSerializer,
    VerifyPaymentInputSerializer,
)
from .services import (
    create_payment_order,
    process_razorpay_webhook,
    rupees_to_paise,
    verify_payment_signature,
)

logger = logging.getLogger("apps.payments")


class CreatePaymentOrderView(APIView):
    """
    POST /api/v1/payments/create-order/
    Creates or reuses an idempotent Razorpay order for an eligible appointment.
    """
    permission_classes = [IsAuthenticatedUser, IsPatient]

    @extend_schema(
        summary="Create Payment Order",
        description="Creates an authorized Razorpay payment order for the patient's appointment. Derives amount strictly from trusted backend fee.",
        request=CreatePaymentOrderInputSerializer,
        responses={
            200: PaymentOrderOutputSerializer,
            201: PaymentOrderOutputSerializer,
            400: OpenApiResponse(description="Invalid request or appointment not eligible"),
            409: OpenApiResponse(description="Reservation expired or slot conflict"),
        },
    )
    def post(self, request):
        serializer = CreatePaymentOrderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        idempotency_key = (
            request.headers.get("Idempotency-Key")
            or request.headers.get("X-Idempotency-Key")
            or validated.get("idempotency_key")
        )

        payment = create_payment_order(
            patient=request.user,
            appointment_id=validated["appointment_id"],
            idempotency_key=idempotency_key,
        )

        out_data = {
            "order_id": payment.gateway_order_id,
            "amount": payment.amount,
            "amount_paise": rupees_to_paise(payment.amount),
            "currency": payment.currency,
            "key_id": getattr(settings, "RAZORPAY_KEY_ID", "rzp_test_placeholder_key_id"),
            "appointment_id": payment.appointment_id,
            "booking_reference": payment.appointment.booking_reference,
            "doctor_name": payment.appointment.doctor.full_name,
            "clinic_name": payment.appointment.clinic.name,
        }
        return Response(PaymentOrderOutputSerializer(out_data).data, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    """
    POST /api/v1/payments/verify/
    Verifies Razorpay HMAC signature and confirms payment and appointment state atomically.
    """
    permission_classes = [IsAuthenticatedUser, IsPatient]

    @extend_schema(
        summary="Verify Payment",
        description="Verifies the payment signature submitted by the frontend after checkout completion.",
        request=VerifyPaymentInputSerializer,
        responses={
            200: PatientPaymentStatusSerializer,
            400: OpenApiResponse(description="Invalid signature or mismatched payment reference"),
            409: OpenApiResponse(description="Reservation expired or late payment conflict"),
        },
    )
    def post(self, request):
        serializer = VerifyPaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        payment = verify_payment_signature(
            razorpay_order_id=validated["razorpay_order_id"],
            razorpay_payment_id=validated["razorpay_payment_id"],
            razorpay_signature=validated["razorpay_signature"],
            patient=request.user,
        )

        resp_serializer = PatientPaymentStatusSerializer(payment)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)


class AppointmentPaymentStatusView(APIView):
    """
    GET /api/v1/payments/appointment/<uuid:appointment_id>/status/
    Returns the payment status for an appointment. Private to authorized patient or clinic owner.
    """
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        summary="Get Appointment Payment Status",
        description="Retrieves the current payment status for an appointment. Strictly excludes internal commission details for patients.",
        responses={
            200: PatientPaymentStatusSerializer,
            403: OpenApiResponse(description="Forbidden - cannot access another patient's payment"),
            404: OpenApiResponse(description="Payment record not found"),
        },
    )
    def get(self, request, appointment_id):
        payment = Payment.objects.filter(appointment_id=appointment_id).select_related("appointment").first()
        if not payment:
            return Response(
                {"detail": _("No payment record found for this appointment.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Ownership authorization check
        is_patient_owner = str(payment.patient_id) == str(request.user.id)
        is_clinic_owner = str(payment.clinic.owner_id) == str(request.user.id)
        is_staff = request.user.is_staff or getattr(request.user, "role", None) == "SUPER_ADMIN"

        if not (is_patient_owner or is_clinic_owner or is_staff):
            raise PermissionDenied(_("You do not have permission to view payment status for this appointment."))

        return Response(PatientPaymentStatusSerializer(payment).data, status=status.HTTP_200_OK)


class RazorpayWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/razorpay/
    Idempotent gateway webhook handler for Razorpay payment lifecycle notifications.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # Bypass user JWT authentication for webhook calls

    @extend_schema(
        summary="Razorpay Webhook Handler",
        description="Public webhook endpoint listening for signature-verified Razorpay events.",
        responses={
            200: OpenApiResponse(description="Webhook processed successfully"),
            400: OpenApiResponse(description="Invalid signature or payload"),
        },
    )
    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature") or ""
        raw_body = request.body

        try:
            event, processed = process_razorpay_webhook(raw_body=raw_body, signature=signature)
            return Response(
                {"status": "ok", "event_id": event.event_id, "processed": processed},
                status=status.HTTP_200_OK,
            )
        except WebhookVerificationException as e:
            return Response({"error": str(e.detail)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error in Razorpay webhook handler: %s", str(e))
            return Response({"error": "Internal processing error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClinicFinancialRecordsListView(generics.ListAPIView):
    """
    GET /api/v1/payments/clinics/<uuid:clinic_id>/financial-records/
    Returns commission records and settlement ledger for an authorized clinic.
    Strictly isolated between clinics.
    """
    permission_classes = [IsAuthenticatedUser]
    serializer_class = ClinicCommissionRecordSerializer

    @extend_schema(
        summary="List Clinic Financial Records",
        description="Returns platform commission snapshots and net clinic allocations. Only accessible by clinic owner or platform admin.",
    )
    def get_queryset(self):
        clinic_id = self.kwargs.get("clinic_id")
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            return CommissionRecord.objects.none()

        is_owner = str(clinic.owner_id) == str(self.request.user.id)
        is_staff = self.request.user.is_staff or getattr(self.request.user, "role", None) == "SUPER_ADMIN"

        if not (is_owner or is_staff):
            raise PermissionDenied(_("You do not have permission to access financial records for this clinic."))

        return CommissionRecord.objects.filter(clinic_id=clinic_id).select_related(
            "appointment", "payment", "appointment__doctor"
        ).order_by("-created_at")


class AdminClinicCommissionUpdateView(APIView):
    """
    PATCH /api/v1/payments/admin/clinics/<uuid:clinic_id>/commission-rate/
    Super Admin endpoint to configure clinic-specific commission rate.
    """
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        summary="Update Clinic Commission Rate",
        description="Allows platform super administrators to set a custom commission percentage for a clinic.",
        request=AdminClinicCommissionUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Commission rate updated successfully"),
            403: OpenApiResponse(description="Forbidden - only super admins can change commission settings"),
            404: OpenApiResponse(description="Clinic not found"),
        },
    )
    def patch(self, request, clinic_id):
        # Only Super Admins / is_staff can edit financial commission settings
        is_admin = request.user.is_staff or getattr(request.user, "role", None) == "SUPER_ADMIN"
        if not is_admin:
            raise PermissionDenied(_("Only platform administrators may modify clinic commission rates."))

        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            return Response({"detail": _("Clinic not found.")}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminClinicCommissionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_rate = serializer.validated_data["commission_rate"]
        old_rate = clinic.commission_rate

        clinic.commission_rate = new_rate
        clinic.save(update_fields=["commission_rate", "updated_at"])

        # Audit change
        AuditLog.objects.create(
            actor=request.user,
            clinic_id=clinic.id,
            action="UPDATE_CLINIC_COMMISSION_RATE",
            resource_type="CLINIC",
            resource_id=str(clinic.id),
            details={
                "previous_rate": str(old_rate) if old_rate is not None else "DEFAULT",
                "new_rate": str(new_rate),
            },
        )

        return Response(
            {
                "message": _("Clinic commission rate updated successfully."),
                "clinic_id": str(clinic.id),
                "commission_rate": str(clinic.commission_rate),
            },
            status=status.HTTP_200_OK,
        )
