from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.appointments.models import Appointment, AppointmentHistory, AppointmentHistoryEventType, AppointmentStatus
from apps.audit_logs.services import log_audit_event
from apps.clinics.models import Clinic, ClinicClosure, ClinicStaffPermission, DoctorClinicStatus
from apps.clinics.permissions import check_clinic_access
from apps.clinics.management_serializers import (
    ClinicClosureCreateSerializer,
    ClinicClosureSerializer,
    ClinicManagementUpdateSerializer,
)
from apps.schedules.models import BlockedSlot, DoctorSchedule, DoctorUnavailability


class ClinicManagementProfileView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/management/
    PATCH /api/v1/clinics/{clinic_id}/management/
    Retrieves or updates permitted clinic profile and operational fields.
    Clinic owners or staff with MANAGE_CLINIC_PROFILE can update.
    Verification status, approvals, and commission rates are strictly read-only.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="Get Clinic Management Profile",
        description="Returns full operational profile for an authorized clinic.",
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic):
            raise PermissionDenied("You do not have permission to view management details for this clinic.")

        serializer = ClinicManagementUpdateSerializer(clinic, context={"request": request})
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update Clinic Management Profile",
        description="Updates operational clinic details. Status, verification, and commission rate cannot be modified.",
        request=ClinicManagementUpdateSerializer,
    )
    def patch(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.MANAGE_CLINIC_PROFILE):
            raise PermissionDenied("You do not have permission to modify this clinic's profile.")

        # Reject any attempt to directly modify protected fields
        for forbidden_field in ("status", "is_verified", "commission_rate", "owner_id", "owner"):
            if forbidden_field in request.data:
                raise ValidationError({forbidden_field: "This field cannot be modified through the clinic management endpoint."})

        prev_timezone = clinic.timezone
        serializer = ClinicManagementUpdateSerializer(clinic, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated_clinic = serializer.save()

        # Audit event
        details = {"updated_fields": list(serializer.validated_data.keys())}
        if "timezone" in serializer.validated_data and prev_timezone != updated_clinic.timezone:
            details["previous_timezone"] = prev_timezone
            details["new_timezone"] = updated_clinic.timezone

        log_audit_event(
            action="CLINIC_PROFILE_UPDATED",
            resource_type="Clinic",
            resource_id=str(updated_clinic.id),
            clinic_id=str(updated_clinic.id),
            actor=request.user,
            request=request,
            details=details,
        )

        return Response(
            {
                "success": True,
                "message": "Clinic profile updated successfully.",
                "data": ClinicManagementUpdateSerializer(updated_clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicClosurePreviewView(APIView):
    """
    POST /api/v1/clinics/{clinic_id}/closures/preview/
    Previews appointments affected by a proposed clinic closure range without applying changes.
    """

    @extend_schema(
        summary="Preview Affected Appointments for Closure",
        description="Checks and returns existing appointments that fall into the specified closure interval.",
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.MANAGE_SCHEDULES):
            raise PermissionDenied("You do not have permission to manage closures for this clinic.")

        serializer = ClinicClosureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]

        try:
            clinic_tz = ZoneInfo(clinic.timezone)
        except Exception:
            clinic_tz = ZoneInfo("Asia/Kolkata")

        start_utc = datetime.combine(start_date, time.min, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))
        end_utc = datetime.combine(end_date, time.max, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))

        affected_appts = (
            Appointment.objects.filter(
                clinic_id=clinic.id,
                start_at__range=(start_utc, end_utc),
                status__in=[
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.PENDING_CONFIRMATION,
                    AppointmentStatus.RESCHEDULE_REQUIRED,
                ],
            )
            .select_related("doctor", "patient")
            .order_by("start_at")
        )

        appt_list = [
            {
                "id": str(a.id),
                "booking_reference": a.booking_reference,
                "doctor_name": a.doctor.full_name,
                "patient_name": f"{a.patient.first_name} {a.patient.last_name}".strip() or a.patient.email,
                "start_at": a.start_at.astimezone(clinic_tz).isoformat(),
                "status": a.status,
            }
            for a in affected_appts
        ]

        return Response(
            {
                "success": True,
                "data": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "affected_count": len(appt_list),
                    "requires_confirmation": len(appt_list) > 0,
                    "affected_appointments": appt_list,
                },
            },
            status=status.HTTP_200_OK,
        )


class ClinicClosureListCreateView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/closures/
    POST /api/v1/clinics/{clinic_id}/closures/
    List and create operational clinic closures (e.g. public holidays, emergency closure, maintenance).
    If appointments are affected and `confirmed` is False, prompts for confirmation.
    """

    @extend_schema(
        summary="List Clinic Closures",
        description="Returns all active and historical closure periods for the clinic.",
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic):
            raise PermissionDenied("You do not have permission to view closures for this clinic.")

        closures = ClinicClosure.objects.filter(clinic_id=clinic.id).select_related("created_by").order_by("-start_date")
        serializer = ClinicClosureSerializer(closures, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create Clinic Closure",
        description="Creates an operational closure. If appointments exist and confirmed is False, requires confirmation.",
        request=ClinicClosureCreateSerializer,
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.MANAGE_SCHEDULES):
            raise PermissionDenied("You do not have permission to create closures for this clinic.")

        serializer = ClinicClosureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]
        reason = serializer.validated_data["reason"]
        notes = serializer.validated_data.get("notes", "")
        confirmed = serializer.validated_data.get("confirmed", False)

        try:
            clinic_tz = ZoneInfo(clinic.timezone)
        except Exception:
            clinic_tz = ZoneInfo("Asia/Kolkata")

        start_utc = datetime.combine(start_date, time.min, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))
        end_utc = datetime.combine(end_date, time.max, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))

        affected_appts = (
            Appointment.objects.filter(
                clinic_id=clinic.id,
                start_at__range=(start_utc, end_utc),
                status__in=[
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.PENDING_CONFIRMATION,
                    AppointmentStatus.RESCHEDULE_REQUIRED,
                ],
            )
            .select_related("doctor", "patient")
            .order_by("start_at")
        )

        affected_count = affected_appts.count()
        if affected_count > 0 and not confirmed:
            appt_list = [
                {
                    "id": str(a.id),
                    "booking_reference": a.booking_reference,
                    "doctor_name": a.doctor.full_name,
                    "patient_name": f"{a.patient.first_name} {a.patient.last_name}".strip() or a.patient.email,
                    "start_at": a.start_at.astimezone(clinic_tz).isoformat(),
                    "status": a.status,
                }
                for a in affected_appts
            ]
            return Response(
                {
                    "success": False,
                    "requires_confirmation": True,
                    "message": f"This closure interval affects {affected_count} existing appointment(s). Please confirm to proceed.",
                    "data": {
                        "affected_count": affected_count,
                        "affected_appointments": appt_list,
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            closure = ClinicClosure.objects.create(
                clinic=clinic,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                notes=notes,
                created_by=request.user,
                is_active=True,
            )

            # Flag affected appointments for rescheduling
            if affected_count > 0:
                for appt in affected_appts:
                    prev_status = appt.status
                    appt.reschedule_required = True
                    appt.status = AppointmentStatus.RESCHEDULE_REQUIRED
                    appt.cancellation_reason = f"Clinic closure ({reason})"
                    appt.save(update_fields=["reschedule_required", "status", "cancellation_reason", "updated_at"])

                    AppointmentHistory.objects.create(
                        appointment=appt,
                        event_type=AppointmentHistoryEventType.RESCHEDULED,
                        previous_status=prev_status,
                        new_status=AppointmentStatus.RESCHEDULE_REQUIRED,
                        actor=request.user,
                        actor_role=request.user.role,
                        reason=f"Clinic Closure: {reason}",
                    )

            log_audit_event(
                action="CLINIC_CLOSURE_CREATED",
                resource_type="ClinicClosure",
                resource_id=str(closure.id),
                clinic_id=str(clinic.id),
                actor=request.user,
                request=request,
                details={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "reason": reason,
                    "affected_appointments_count": affected_count,
                },
            )

        return Response(
            {
                "success": True,
                "message": "Clinic closure created successfully.",
                "data": ClinicClosureSerializer(closure).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ClinicClosureDetailView(APIView):
    """
    DELETE /api/v1/clinics/{clinic_id}/closures/{closure_id}/
    Deactivates or removes an operational clinic closure.
    """

    @extend_schema(
        summary="Delete Clinic Closure",
        description="Removes or deactivates an active clinic closure interval.",
    )
    def delete(self, request, clinic_id, closure_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.MANAGE_SCHEDULES):
            raise PermissionDenied("You do not have permission to remove closures for this clinic.")

        closure = get_object_or_404(ClinicClosure, id=closure_id, clinic_id=clinic.id)
        closure.delete()

        log_audit_event(
            action="CLINIC_CLOSURE_REMOVED",
            resource_type="ClinicClosure",
            resource_id=str(closure_id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"closure_id": str(closure_id)},
        )

        return Response({"success": True, "message": "Clinic closure removed successfully."}, status=status.HTTP_200_OK)


class ClinicCalendarView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/calendar/
    Provides comprehensive calendar data for the clinic:
    - Recurring shifts
    - Booked appointments
    - Doctor unavailabilities
    - Blocked slots
    - Clinic closures
    Strictly scoped to the clinic and converted to clinic operating timezone.
    """

    @extend_schema(
        summary="Clinic Calendar Data",
        description="Returns shifts, appointments, leaves, and closures for calendar visualization.",
        parameters=[
            OpenApiParameter(name="start_date", type=str, description="YYYY-MM-DD (defaults to today)"),
            OpenApiParameter(name="end_date", type=str, description="YYYY-MM-DD (defaults to 7 days from start)"),
            OpenApiParameter(name="doctor_id", type=str, description="Optional filter by doctor UUID"),
        ],
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic):
            raise PermissionDenied("You do not have permission to view calendar data for this clinic.")

        try:
            clinic_tz = ZoneInfo(clinic.timezone)
        except Exception:
            clinic_tz = ZoneInfo("Asia/Kolkata")

        today_local = timezone.now().astimezone(clinic_tz).date()
        start_date_param = request.query_params.get("start_date")
        end_date_param = request.query_params.get("end_date")

        try:
            start_date = datetime.strptime(start_date_param, "%Y-%m-%d").date() if start_date_param else today_local
        except ValueError:
            start_date = today_local

        try:
            end_date = datetime.strptime(end_date_param, "%Y-%m-%d").date() if end_date_param else (start_date + timedelta(days=6))
        except ValueError:
            end_date = start_date + timedelta(days=6)

        if start_date > end_date:
            end_date = start_date

        start_utc = datetime.combine(start_date, time.min, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))
        end_utc = datetime.combine(end_date, time.max, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))

        doctor_id = request.query_params.get("doctor_id")

        # 1. Doctor recurring shifts
        shifts_qs = DoctorSchedule.objects.filter(
            doctor_clinic__clinic_id=clinic.id,
            is_active=True,
        ).select_related("doctor_clinic__doctor")
        if doctor_id:
            shifts_qs = shifts_qs.filter(doctor_clinic__doctor_id=doctor_id)

        shifts_data = [
            {
                "id": str(s.id),
                "doctor_id": str(s.doctor_clinic.doctor_id),
                "doctor_name": s.doctor_clinic.doctor.full_name,
                "day_of_week": s.day_of_week,
                "start_time": s.start_time.strftime("%H:%M"),
                "end_time": s.end_time.strftime("%H:%M"),
                "slot_duration_minutes": s.effective_slot_duration,
            }
            for s in shifts_qs
        ]

        # 2. Booked Appointments
        appts_qs = Appointment.objects.filter(
            clinic_id=clinic.id,
            start_at__range=(start_utc, end_utc),
        ).select_related("doctor", "patient").order_by("start_at")
        if doctor_id:
            appts_qs = appts_qs.filter(doctor_id=doctor_id)

        appts_data = [
            {
                "id": str(a.id),
                "booking_reference": a.booking_reference,
                "doctor_id": str(a.doctor_id),
                "doctor_name": a.doctor.full_name,
                "patient_name": f"{a.patient.first_name} {a.patient.last_name}".strip() or a.patient.email,
                "start_at": a.start_at.astimezone(clinic_tz).isoformat(),
                "end_at": a.end_at.astimezone(clinic_tz).isoformat(),
                "status": a.status,
                "payment_status": a.payment_status,
                "reschedule_required": a.reschedule_required,
            }
            for a in appts_qs
        ]

        # 3. Doctor Unavailabilities
        unavail_qs = DoctorUnavailability.objects.filter(
            Q(clinic_id=clinic.id) | Q(clinic__isnull=True),
            doctor__clinic_associations__clinic_id=clinic.id,
            doctor__clinic_associations__status=DoctorClinicStatus.ACTIVE,
            start_datetime__lt=end_utc,
            end_datetime__gt=start_utc,
        ).select_related("doctor")
        if doctor_id:
            unavail_qs = unavail_qs.filter(doctor_id=doctor_id)

        unavail_data = [
            {
                "id": str(u.id),
                "doctor_id": str(u.doctor_id),
                "doctor_name": u.doctor.full_name,
                "start_datetime": u.start_datetime.astimezone(clinic_tz).isoformat(),
                "end_datetime": u.end_datetime.astimezone(clinic_tz).isoformat(),
                "reason": u.reason,
                "notes": u.notes,
            }
            for u in unavail_qs
        ]

        # 4. Blocked slots
        blocked_qs = BlockedSlot.objects.filter(
            doctor_clinic__clinic_id=clinic.id,
            date__range=(start_date, end_date),
        ).select_related("doctor_clinic__doctor")
        if doctor_id:
            blocked_qs = blocked_qs.filter(doctor_clinic__doctor_id=doctor_id)

        blocked_data = [
            {
                "id": str(b.id),
                "doctor_id": str(b.doctor_clinic.doctor_id),
                "doctor_name": b.doctor_clinic.doctor.full_name,
                "date": b.date.isoformat(),
                "start_time": b.start_time.strftime("%H:%M"),
                "end_time": b.end_time.strftime("%H:%M") if b.end_time else "",
                "reason": b.reason,
            }
            for b in blocked_qs
        ]

        # 5. Clinic Closures
        closures_qs = ClinicClosure.objects.filter(
            clinic_id=clinic.id,
            is_active=True,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        closures_data = [
            {
                "id": str(c.id),
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat(),
                "reason": c.reason,
                "notes": c.notes,
            }
            for c in closures_qs
        ]

        return Response(
            {
                "success": True,
                "data": {
                    "clinic": {
                        "id": str(clinic.id),
                        "name": clinic.name,
                        "timezone": clinic.timezone,
                    },
                    "range": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                    "shifts": shifts_data,
                    "appointments": appts_data,
                    "unavailabilities": unavail_data,
                    "blocked_slots": blocked_data,
                    "closures": closures_data,
                },
            },
            status=status.HTTP_200_OK,
        )
