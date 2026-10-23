from decimal import Decimal
from django.db.models import Q
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin
from apps.audit_logs.models import AuditLog
from apps.audit_logs.services import log_audit_event
from apps.clinics.models import Clinic, ClinicStatus
from .admin_serializers import (
    AdminCommissionRecordSerializer,
    AdminCommissionSettingsUpdateSerializer,
    AdminPaymentSerializer,
)
from .models import CommissionRecord, Payment, PlatformSetting


class AdminPaymentPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminPaymentListView(APIView):
    """
    Super Admin endpoint to monitor all platform payments.
    Supports filtering by payment status, clinic, date range, and search keyword.
    """

    permission_classes = [IsSuperAdmin]
    pagination_class = AdminPaymentPagination

    @extend_schema(
        summary="Admin List Payments",
        description="Lists all payment records across platform with filters and pagination.",
        responses={200: AdminPaymentSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            Payment.objects.all()
            .select_related("clinic", "patient", "appointment")
            .prefetch_related("commission_record")
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            queryset = queryset.filter(status=status_param.upper())

        clinic_id = request.query_params.get("clinic_id")
        if clinic_id:
            queryset = queryset.filter(clinic_id=clinic_id)

        date_from = request.query_params.get("date_from")
        if date_from:
            d_from = parse_date(date_from)
            if d_from:
                queryset = queryset.filter(created_at__date__gte=d_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            d_to = parse_date(date_to)
            if d_to:
                queryset = queryset.filter(created_at__date__lte=d_to)

        search = request.query_params.get("search")
        if search:
            q = search.strip()
            queryset = queryset.filter(
                Q(gateway_order_id__icontains=q)
                | Q(gateway_payment_id__icontains=q)
                | Q(patient__email__icontains=q)
                | Q(patient__first_name__icontains=q)
                | Q(patient__last_name__icontains=q)
                | Q(clinic__name__icontains=q)
                | Q(appointment__booking_reference__icontains=q)
            )

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminPaymentSerializer(paginated_qs, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class AdminCommissionListView(APIView):
    """
    Super Admin endpoint to inspect internal platform commission records.
    """

    permission_classes = [IsSuperAdmin]
    pagination_class = AdminPaymentPagination

    @extend_schema(
        summary="Admin List Commission Records",
        description="Lists all internal commission and clinic share records with status and clinic filters.",
        responses={200: AdminCommissionRecordSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            CommissionRecord.objects.all()
            .select_related("clinic", "appointment", "payment")
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            queryset = queryset.filter(status=status_param.upper())

        clinic_id = request.query_params.get("clinic_id")
        if clinic_id:
            queryset = queryset.filter(clinic_id=clinic_id)

        date_from = request.query_params.get("date_from")
        if date_from:
            d_from = parse_date(date_from)
            if d_from:
                queryset = queryset.filter(created_at__date__gte=d_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            d_to = parse_date(date_to)
            if d_to:
                queryset = queryset.filter(created_at__date__lte=d_to)

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminCommissionRecordSerializer(paginated_qs, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class AdminCommissionSettingsView(APIView):
    """
    Super Admin endpoint to inspect and configure the platform's default commission rate
    as well as clinic-specific overrides.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Get Commission Settings",
        description="View current default platform commission rate, clinic overrides, and modification audit history.",
        responses={200: OpenApiResponse(description="Commission settings")},
    )
    def get(self, request):
        default_rate = PlatformSetting.get_default_commission_rate()

        # All clinics with custom overrides
        overrides_qs = Clinic.objects.filter(commission_rate__isnull=False).order_by("name")
        overrides = [
            {
                "clinic_id": str(c.id),
                "clinic_name": c.name,
                "slug": c.slug,
                "city": c.city,
                "status": c.status,
                "commission_rate": str(c.commission_rate),
                "effective_rate": str(c.commission_rate),
            }
            for c in overrides_qs
        ]

        # All approved clinics overview
        approved_clinics = Clinic.objects.filter(status=ClinicStatus.APPROVED).order_by("name")
        clinic_list = [
            {
                "clinic_id": str(c.id),
                "clinic_name": c.name,
                "slug": c.slug,
                "city": c.city,
                "has_override": c.commission_rate is not None,
                "override_rate": str(c.commission_rate) if c.commission_rate is not None else None,
                "effective_rate": str(c.commission_rate if c.commission_rate is not None else default_rate),
            }
            for c in approved_clinics
        ]

        # Audit log history for commission rate changes
        history_qs = AuditLog.objects.filter(
            action__in=["UPDATE_PLATFORM_COMMISSION_RATE", "UPDATE_CLINIC_COMMISSION_RATE"]
        ).select_related("actor")[:20]

        history = [
            {
                "id": str(log.id),
                "action": log.action,
                "actor_email": log.actor.email if log.actor else "System",
                "details": log.details,
                "created_at": log.created_at,
            }
            for log in history_qs
        ]

        return Response(
            {
                "success": True,
                "data": {
                    "default_rate": str(default_rate),
                    "clinic_overrides": overrides,
                    "clinics": clinic_list,
                    "history": history,
                },
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Admin Update Commission Settings",
        description="Update global platform default commission rate or clinic-specific override. Requires Super Admin.",
        request=AdminCommissionSettingsUpdateSerializer,
        responses={200: OpenApiResponse(description="Updated settings")},
    )
    def patch(self, request):
        serializer = AdminCommissionSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        reason = data.get("reason", "").strip() or "Administrative update"
        updated_items = {}

        # 1. Update platform default rate if provided
        if "default_rate" in data and data["default_rate"] is not None:
            new_default = data["default_rate"]
            old_default = PlatformSetting.get_default_commission_rate()

            PlatformSetting.set_default_commission_rate(new_default, user=request.user)
            log_audit_event(
                action="UPDATE_PLATFORM_COMMISSION_RATE",
                resource_type="PLATFORM_SETTING",
                resource_id="default_commission_rate",
                actor=request.user,
                request=request,
                details={
                    "previous_rate": str(old_default),
                    "new_rate": str(new_default),
                    "reason": reason,
                },
            )
            updated_items["default_rate"] = str(new_default)

        # 2. Update clinic-specific override if clinic_id provided
        if "clinic_id" in data and data["clinic_id"] is not None:
            clinic_id = data["clinic_id"]
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return Response(
                    {"success": False, "message": "Specified clinic not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            old_rate = clinic.commission_rate
            new_rate = data.get("clinic_rate")  # Can be None to reset override

            clinic.commission_rate = new_rate
            clinic.save(update_fields=["commission_rate", "updated_at"])

            log_audit_event(
                action="UPDATE_CLINIC_COMMISSION_RATE",
                resource_type="CLINIC",
                resource_id=str(clinic.id),
                clinic_id=str(clinic.id),
                actor=request.user,
                request=request,
                details={
                    "clinic_name": clinic.name,
                    "previous_rate": str(old_rate) if old_rate is not None else "DEFAULT",
                    "new_rate": str(new_rate) if new_rate is not None else "DEFAULT",
                    "reason": reason,
                },
            )
            updated_items["clinic_id"] = str(clinic.id)
            updated_items["clinic_rate"] = str(new_rate) if new_rate is not None else None

        current_default = PlatformSetting.get_default_commission_rate()
        return Response(
            {
                "success": True,
                "message": "Commission configuration successfully updated.",
                "data": {
                    "updated": updated_items,
                    "default_rate": str(current_default),
                },
            },
            status=status.HTTP_200_OK,
        )
