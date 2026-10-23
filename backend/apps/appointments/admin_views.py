from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin
from apps.audit_logs.services import log_audit_event
from .admin_serializers import (
    AdminAppointmentCancelActionSerializer,
    AdminAppointmentHistorySerializer,
    AdminAppointmentSerializer,
)
from .models import (
    Appointment,
    AppointmentHistory,
    AppointmentHistoryEventType,
    AppointmentStatus,
)


class AdminAppointmentPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminAppointmentListView(APIView):
    """
    Super Admin endpoint to monitor all appointments platform-wide.
    Supports filtering by clinic, doctor, appointment status, payment status, and date range.
    """

    permission_classes = [IsSuperAdmin]
    pagination_class = AdminAppointmentPagination

    @extend_schema(
        summary="Admin List Appointments",
        description="Lists all appointments across platform with search, filters, and pagination.",
        responses={200: AdminAppointmentSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            Appointment.objects.all()
            .select_related("patient", "doctor", "clinic")
            .order_by("-start_at")
        )

        clinic_id = request.query_params.get("clinic_id")
        if clinic_id:
            queryset = queryset.filter(clinic_id=clinic_id)

        doctor_id = request.query_params.get("doctor_id")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        status_param = request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            queryset = queryset.filter(status=status_param.upper())

        payment_status_param = request.query_params.get("payment_status")
        if payment_status_param and payment_status_param.upper() != "ALL":
            queryset = queryset.filter(payment_status=payment_status_param.upper())

        date_from = request.query_params.get("date_from")
        if date_from:
            d_from = parse_date(date_from)
            if d_from:
                queryset = queryset.filter(start_at__date__gte=d_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            d_to = parse_date(date_to)
            if d_to:
                queryset = queryset.filter(start_at__date__lte=d_to)

        search = request.query_params.get("search")
        if search:
            q = search.strip()
            queryset = queryset.filter(
                Q(booking_reference__icontains=q)
                | Q(patient__email__icontains=q)
                | Q(patient__first_name__icontains=q)
                | Q(patient__last_name__icontains=q)
                | Q(doctor__full_name__icontains=q)
                | Q(clinic__name__icontains=q)
            )

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminAppointmentSerializer(paginated_qs, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class AdminAppointmentDetailView(APIView):
    """
    Super Admin endpoint to inspect full details of an appointment.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Get Appointment Details",
        description="Retrieve full details for an appointment.",
        responses={200: AdminAppointmentSerializer, 404: OpenApiResponse(description="Not Found.")},
    )
    def get(self, request, pk):
        appointment = get_object_or_404(
            Appointment.objects.select_related("patient", "doctor", "clinic"),
            pk=pk,
        )
        return Response(
            {
                "success": True,
                "data": AdminAppointmentSerializer(appointment, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminAppointmentHistoryView(APIView):
    """
    Super Admin endpoint to inspect the complete state transition and event history of an appointment.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Get Appointment History",
        description="Retrieve chronological audit and state change history for an appointment.",
        responses={200: AdminAppointmentHistorySerializer(many=True)},
    )
    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        history = AppointmentHistory.objects.filter(appointment=appointment).select_related("actor").order_by("-created_at")
        serializer = AdminAppointmentHistorySerializer(history, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class AdminAppointmentCancelView(APIView):
    """
    Super Admin endpoint to cancel an appointment under exceptional circumstances.
    Requires an explicit reason, logs state change in history, and creates an audit record.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Cancel Appointment",
        description="Administratively cancel an appointment with an explicit reason.",
        request=AdminAppointmentCancelActionSerializer,
        responses={
            200: AdminAppointmentSerializer,
            400: OpenApiResponse(description="Invalid state or validation error."),
        },
    )
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)

        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
            return Response(
                {
                    "success": False,
                    "message": f"Cannot cancel appointment with status '{appointment.status}'.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminAppointmentCancelActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        prev_status = appointment.status
        now = timezone.now()

        with transaction.atomic():
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = now
            appointment.cancelled_by = request.user
            appointment.cancellation_reason = f"[ADMIN OVERRIDE]: {reason}"
            appointment.save(update_fields=["status", "cancelled_at", "cancelled_by", "cancellation_reason", "updated_at"])

            AppointmentHistory.objects.create(
                appointment=appointment,
                event_type=AppointmentHistoryEventType.ADMIN_OVERRIDE,
                previous_status=prev_status,
                new_status=AppointmentStatus.CANCELLED,
                previous_start_at=appointment.start_at,
                previous_end_at=appointment.end_at,
                new_start_at=appointment.start_at,
                new_end_at=appointment.end_at,
                actor=request.user,
                actor_role="SUPER_ADMIN",
                reason=reason,
                is_exception=True,
            )

            log_audit_event(
                action="ADMIN_CANCEL_APPOINTMENT",
                resource_type="APPOINTMENT",
                resource_id=str(appointment.id),
                clinic_id=str(appointment.clinic_id),
                actor=request.user,
                request=request,
                details={
                    "booking_reference": appointment.booking_reference,
                    "previous_status": prev_status,
                    "reason": reason,
                },
            )

        return Response(
            {
                "success": True,
                "message": f"Appointment '{appointment.booking_reference}' has been cancelled by administrator.",
                "data": AdminAppointmentSerializer(appointment, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
