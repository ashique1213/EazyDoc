from datetime import date, datetime
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from apps.accounts.models import UserRole
from apps.audit_logs.services import log_audit_event
from apps.clinics.models import Clinic, DoctorClinic
from apps.doctors.models import Doctor
from .exceptions import ScheduleConflictException
from .models import BlockedSlot, DoctorSchedule, DoctorUnavailability, Weekday
from .permissions import CanManageClinicSchedules, CanManageDoctorUnavailability, CanViewSchedules
from .serializers import (
    BlockedSlotSerializer,
    DoctorScheduleCreateUpdateSerializer,
    DoctorScheduleSerializer,
    DoctorUnavailabilitySerializer,
    ScheduleConflictCheckSerializer,
)
from .services import check_schedule_conflicts, generate_doctor_availability_slots


class ScheduleListCreateView(APIView):
    """
    List and create doctor recurring weekly working shifts.
    - Clinic Owners & Staff configure shifts for their clinic.
    - Doctors view their shifts across affiliated clinics.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [CanManageClinicSchedules()]
        return [CanViewSchedules()]

    @extend_schema(
        summary="List Doctor Schedules",
        description="List active recurring shifts filtered by clinic_id, doctor_clinic_id, or doctor_id.",
        parameters=[
            OpenApiParameter(name="clinic_id", type=str, required=False),
            OpenApiParameter(name="doctor_clinic_id", type=str, required=False),
            OpenApiParameter(name="doctor_id", type=str, required=False),
            OpenApiParameter(name="day_of_week", type=int, required=False),
            OpenApiParameter(name="is_active", type=bool, required=False),
        ],
        responses={200: DoctorScheduleSerializer(many=True)},
    )
    def get(self, request):
        user = request.user
        qs = DoctorSchedule.objects.select_related(
            "doctor_clinic__clinic",
            "doctor_clinic__doctor",
        ).all()

        # Multi-tenant and role-based scoping (Rules 1, 2, 5, 6)
        if user.role == UserRole.CLINIC_OWNER:
            qs = qs.filter(doctor_clinic__clinic__owner=user)
        elif user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
            qs = qs.filter(doctor_clinic__clinic_id=user.staff_profile.clinic_id)
        elif user.role == UserRole.DOCTOR:
            qs = qs.filter(doctor_clinic__doctor__user=user)
        elif user.role != UserRole.SUPER_ADMIN:
            qs = qs.none()

        # Optional filters
        clinic_id = request.query_params.get("clinic_id")
        if clinic_id:
            qs = qs.filter(doctor_clinic__clinic_id=clinic_id)

        doctor_clinic_id = request.query_params.get("doctor_clinic_id")
        if doctor_clinic_id:
            qs = qs.filter(doctor_clinic_id=doctor_clinic_id)

        doctor_id = request.query_params.get("doctor_id")
        if doctor_id:
            qs = qs.filter(doctor_clinic__doctor_id=doctor_id)

        day_of_week = request.query_params.get("day_of_week")
        if day_of_week is not None:
            try:
                qs = qs.filter(day_of_week=int(day_of_week))
            except ValueError:
                pass

        is_active_param = request.query_params.get("is_active")
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1")
            qs = qs.filter(is_active=is_active)
        else:
            # Default to active shifts unless specified
            qs = qs.filter(is_active=True)

        serializer = DoctorScheduleSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create Doctor Schedule Shift",
        description="Creates a recurring working shift for an active doctor-clinic association, validating conflicts and travel buffers.",
        request=DoctorScheduleCreateUpdateSerializer,
        responses={
            201: DoctorScheduleSerializer,
            400: OpenApiResponse(description="Validation error."),
            409: OpenApiResponse(description="Schedule conflict or travel buffer collision."),
        },
    )
    def post(self, request):
        serializer = DoctorScheduleCreateUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Enforce clinic ownership / tenant isolation (Rule 6)
        doctor_clinic = serializer.validated_data["doctor_clinic"]
        user = request.user
        if user.role == UserRole.CLINIC_OWNER and doctor_clinic.clinic.owner_id != user.id:
            raise PermissionDenied("You do not have permission to configure schedules for this clinic.")
        elif user.role == UserRole.STAFF and (not hasattr(user, "staff_profile") or user.staff_profile.clinic_id != doctor_clinic.clinic_id):
            raise PermissionDenied("You do not have permission to configure schedules for this clinic.")

        schedule = serializer.save()

        log_audit_event(
            action="SCHEDULE_CREATED",
            resource_type="DoctorSchedule",
            resource_id=str(schedule.id),
            clinic_id=str(doctor_clinic.clinic_id),
            actor=request.user,
            request=request,
            details={
                "doctor_clinic_id": str(doctor_clinic.id),
                "doctor_id": str(doctor_clinic.doctor_id),
                "day_of_week": schedule.day_of_week,
                "start_time": schedule.start_time.strftime("%H:%M"),
                "end_time": schedule.end_time.strftime("%H:%M"),
            },
        )

        read_serializer = DoctorScheduleSerializer(schedule)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class ScheduleDetailView(APIView):
    """Retrieve, update, or soft-deactivate an existing doctor schedule shift."""

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [CanManageClinicSchedules()]
        return [CanViewSchedules()]

    def get_object(self, pk):
        schedule = get_object_or_404(
            DoctorSchedule.objects.select_related("doctor_clinic__clinic", "doctor_clinic__doctor"),
            pk=pk,
        )
        self.check_object_permissions(self.request, schedule)
        return schedule

    @extend_schema(
        summary="Retrieve Doctor Schedule",
        responses={200: DoctorScheduleSerializer},
    )
    def get(self, request, pk):
        schedule = self.get_object(pk)
        return Response(DoctorScheduleSerializer(schedule).data)

    @extend_schema(
        summary="Update Doctor Schedule Shift",
        request=DoctorScheduleCreateUpdateSerializer,
        responses={200: DoctorScheduleSerializer, 409: OpenApiResponse(description="Schedule conflict.")},
    )
    def put(self, request, pk):
        schedule = self.get_object(pk)
        serializer = DoctorScheduleCreateUpdateSerializer(
            schedule,
            data=request.data,
            partial=False,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated_schedule = serializer.save()

        log_audit_event(
            action="SCHEDULE_UPDATED",
            resource_type="DoctorSchedule",
            resource_id=str(updated_schedule.id),
            clinic_id=str(updated_schedule.doctor_clinic.clinic_id),
            actor=request.user,
            request=request,
            details={
                "day_of_week": updated_schedule.day_of_week,
                "start_time": updated_schedule.start_time.strftime("%H:%M"),
                "end_time": updated_schedule.end_time.strftime("%H:%M"),
            },
        )

        return Response(DoctorScheduleSerializer(updated_schedule).data)

    @extend_schema(
        summary="Partial Update Doctor Schedule Shift",
        request=DoctorScheduleCreateUpdateSerializer,
        responses={200: DoctorScheduleSerializer, 409: OpenApiResponse(description="Schedule conflict.")},
    )
    def patch(self, request, pk):
        schedule = self.get_object(pk)
        serializer = DoctorScheduleCreateUpdateSerializer(
            schedule,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated_schedule = serializer.save()

        log_audit_event(
            action="SCHEDULE_UPDATED",
            resource_type="DoctorSchedule",
            resource_id=str(updated_schedule.id),
            clinic_id=str(updated_schedule.doctor_clinic.clinic_id),
            actor=request.user,
            request=request,
            details={
                "day_of_week": updated_schedule.day_of_week,
                "start_time": updated_schedule.start_time.strftime("%H:%M"),
                "end_time": updated_schedule.end_time.strftime("%H:%M"),
                "is_active": updated_schedule.is_active,
            },
        )

        return Response(DoctorScheduleSerializer(updated_schedule).data)

    @extend_schema(
        summary="Deactivate Doctor Schedule Shift",
        description="Soft-deactivates the recurring shift preserving schedule audit history (Rule 16).",
        responses={200: OpenApiResponse(description="Schedule deactivated.")},
    )
    def delete(self, request, pk):
        schedule = self.get_object(pk)
        schedule.is_active = False
        schedule.save(update_fields=["is_active", "updated_at"])

        log_audit_event(
            action="SCHEDULE_DEACTIVATED",
            resource_type="DoctorSchedule",
            resource_id=str(schedule.id),
            clinic_id=str(schedule.doctor_clinic.clinic_id),
            actor=request.user,
            request=request,
            details={"is_active": False},
        )

        return Response(
            {
                "success": True,
                "message": "Schedule shift deactivated successfully.",
                "schedule_id": str(schedule.id),
            },
            status=status.HTTP_200_OK,
        )


class ScheduleConflictCheckView(APIView):
    """
    Pre-validation endpoint allowing clinic owners to dry-run shift timings
    against other clinics before saving (Rule 11, Rule 13).
    """

    permission_classes = [CanManageClinicSchedules]

    @extend_schema(
        summary="Check Schedule Conflicts",
        description="Dry-run conflict check across all affiliated clinics and travel buffer requirements.",
        request=ScheduleConflictCheckSerializer,
        responses={
            200: OpenApiResponse(description="Conflict evaluation result."),
        },
    )
    def post(self, request):
        serializer = ScheduleConflictCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        doctor_clinic = data["doctor_clinic"]
        user = request.user
        if user.role == UserRole.CLINIC_OWNER and doctor_clinic.clinic.owner_id != user.id:
            raise PermissionDenied("You do not have permission to check schedules for this clinic.")

        has_conflict, conflict_details = check_schedule_conflicts(
            doctor_id=doctor_clinic.doctor_id,
            day_of_week=data["day_of_week"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            clinic_id=doctor_clinic.clinic_id,
            exclude_schedule_id=data.get("exclude_schedule_id"),
            buffer_minutes=data.get("buffer_minutes", 0),
        )

        return Response({
            "has_conflict": has_conflict,
            "conflict": conflict_details,
        }, status=status.HTTP_200_OK)


class DoctorUnavailabilityListCreateView(APIView):
    """
    List and create doctor leave periods / unavailability.
    Doctors manage their own leaves; Clinic Owners can record clinic closures or doctor leaves.
    """

    permission_classes = [CanManageDoctorUnavailability]

    @extend_schema(
        summary="List Doctor Unavailability Periods",
        parameters=[
            OpenApiParameter(name="doctor_id", type=str, required=False),
            OpenApiParameter(name="clinic_id", type=str, required=False),
        ],
        responses={200: DoctorUnavailabilitySerializer(many=True)},
    )
    def get(self, request):
        user = request.user
        qs = DoctorUnavailability.objects.select_related("doctor", "clinic").all()

        if user.role == UserRole.DOCTOR:
            qs = qs.filter(doctor__user=user)
        elif user.role == UserRole.CLINIC_OWNER:
            qs = qs.filter(clinic__owner=user)
        elif user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
            qs = qs.filter(clinic_id=user.staff_profile.clinic_id)
        elif user.role != UserRole.SUPER_ADMIN:
            qs = qs.none()

        clinic_id = request.query_params.get("clinic_id")
        if clinic_id:
            qs = qs.filter(clinic_id=clinic_id)

        doctor_id = request.query_params.get("doctor_id")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)

        serializer = DoctorUnavailabilitySerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create Doctor Unavailability / Leave",
        request=DoctorUnavailabilitySerializer,
        responses={201: DoctorUnavailabilitySerializer},
    )
    def post(self, request):
        user = request.user
        data = request.data.copy()

        # If requesting as doctor, force doctor reference to authenticated doctor
        if user.role == UserRole.DOCTOR:
            if not hasattr(user, "doctor_profile"):
                raise ValidationError("User does not have an active doctor profile.")
            data["doctor"] = str(user.doctor_profile.id)

        serializer = DoctorUnavailabilitySerializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Enforce tenant scoping if clinic is provided
        clinic = serializer.validated_data.get("clinic")
        if user.role == UserRole.CLINIC_OWNER:
            if not clinic or clinic.owner_id != user.id:
                raise PermissionDenied("Clinic owners can only create leaves scoped to their own clinic.")

        unavail = serializer.save()

        log_audit_event(
            action="LEAVE_CREATED",
            resource_type="DoctorUnavailability",
            resource_id=str(unavail.id),
            clinic_id=str(unavail.clinic_id) if unavail.clinic_id else None,
            actor=request.user,
            request=request,
            details={
                "doctor_id": str(unavail.doctor_id),
                "reason": unavail.reason,
                "start": unavail.start_datetime.isoformat(),
                "end": unavail.end_datetime.isoformat(),
            },
        )

        return Response(DoctorUnavailabilitySerializer(unavail).data, status=status.HTTP_201_CREATED)


class DoctorUnavailabilityDetailView(APIView):
    """Delete or view specific doctor unavailability / leave."""

    permission_classes = [CanManageDoctorUnavailability]

    def get_object(self, pk):
        obj = get_object_or_404(
            DoctorUnavailability.objects.select_related("doctor", "clinic"),
            pk=pk,
        )
        self.check_object_permissions(self.request, obj)
        return obj

    @extend_schema(summary="Retrieve Doctor Unavailability", responses={200: DoctorUnavailabilitySerializer})
    def get(self, request, pk):
        unavail = self.get_object(pk)
        return Response(DoctorUnavailabilitySerializer(unavail).data)

    @extend_schema(summary="Delete Doctor Unavailability / Leave", responses={204: None})
    def delete(self, request, pk):
        unavail = self.get_object(pk)
        log_audit_event(
            action="LEAVE_DELETED",
            resource_type="DoctorUnavailability",
            resource_id=str(unavail.id),
            clinic_id=str(unavail.clinic_id) if unavail.clinic_id else None,
            actor=request.user,
            request=request,
            details={"doctor_id": str(unavail.doctor_id), "reason": unavail.reason},
        )
        unavail.delete()
        return Response({"success": True, "message": "Leave period cancelled."}, status=status.HTTP_200_OK)


class BlockedSlotListCreateView(APIView):
    """List and block individual time slots on specific dates."""

    permission_classes = [CanManageClinicSchedules]

    @extend_schema(
        summary="List Blocked Slots",
        parameters=[
            OpenApiParameter(name="doctor_clinic_id", type=str, required=False),
            OpenApiParameter(name="date", type=str, required=False),
        ],
        responses={200: BlockedSlotSerializer(many=True)},
    )
    def get(self, request):
        user = request.user
        qs = BlockedSlot.objects.select_related("doctor_clinic__clinic", "doctor_clinic__doctor").all()

        if user.role == UserRole.CLINIC_OWNER:
            qs = qs.filter(doctor_clinic__clinic__owner=user)
        elif user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
            qs = qs.filter(doctor_clinic__clinic_id=user.staff_profile.clinic_id)
        elif user.role != UserRole.SUPER_ADMIN:
            qs = qs.none()

        dc_id = request.query_params.get("doctor_clinic_id")
        if dc_id:
            qs = qs.filter(doctor_clinic_id=dc_id)

        date_param = request.query_params.get("date")
        if date_param:
            parsed = parse_date(date_param)
            if parsed:
                qs = qs.filter(date=parsed)

        return Response(BlockedSlotSerializer(qs, many=True).data)

    @extend_schema(
        summary="Block Specific Time Slot",
        request=BlockedSlotSerializer,
        responses={201: BlockedSlotSerializer},
    )
    def post(self, request):
        serializer = BlockedSlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doctor_clinic = serializer.validated_data["doctor_clinic"]
        user = request.user
        if user.role == UserRole.CLINIC_OWNER and doctor_clinic.clinic.owner_id != user.id:
            raise PermissionDenied("You do not have permission to block slots for this clinic.")

        blocked = serializer.save()

        log_audit_event(
            action="BLOCKED_SLOT_CREATED",
            resource_type="BlockedSlot",
            resource_id=str(blocked.id),
            clinic_id=str(doctor_clinic.clinic_id),
            actor=request.user,
            request=request,
            details={
                "date": blocked.date.isoformat(),
                "start_time": blocked.start_time.strftime("%H:%M"),
                "reason": blocked.reason,
            },
        )

        return Response(BlockedSlotSerializer(blocked).data, status=status.HTTP_201_CREATED)


class BlockedSlotDetailView(APIView):
    """Remove a previously blocked slot."""

    permission_classes = [CanManageClinicSchedules]

    def get_object(self, pk):
        obj = get_object_or_404(
            BlockedSlot.objects.select_related("doctor_clinic__clinic"),
            pk=pk,
        )
        self.check_object_permissions(self.request, obj)
        return obj

    @extend_schema(summary="Unblock Time Slot", responses={200: None})
    def delete(self, request, pk):
        obj = self.get_object(pk)
        log_audit_event(
            action="BLOCKED_SLOT_DELETED",
            resource_type="BlockedSlot",
            resource_id=str(obj.id),
            clinic_id=str(obj.doctor_clinic.clinic_id),
            actor=request.user,
            request=request,
            details={"date": obj.date.isoformat(), "start_time": obj.start_time.strftime("%H:%M")},
        )
        obj.delete()
        return Response({"success": True, "message": "Slot unblocked."}, status=status.HTTP_200_OK)


class AvailabilitySlotsView(APIView):
    """
    Computes real-time discrete bookable slots for a doctor at a clinic on a specific date.
    Integrates recurring shifts, leaves, blocked slots, and operating timezone.
    """

    permission_classes = [CanViewSchedules]

    @extend_schema(
        summary="Query Doctor Availability Slots",
        description="Returns generated candidate slots with availability flags and reasons for a given doctor_clinic and date.",
        parameters=[
            OpenApiParameter(name="doctor_clinic_id", type=str, required=True),
            OpenApiParameter(name="date", type=str, required=True, description="YYYY-MM-DD date"),
        ],
        responses={200: OpenApiResponse(description="Generated availability slots.")},
    )
    def get(self, request):
        dc_id = request.query_params.get("doctor_clinic_id") or request.query_params.get("doctor_clinic")
        if not dc_id:
            raise ValidationError({"doctor_clinic_id": "doctor_clinic_id parameter is required."})

        date_str = request.query_params.get("date")
        if not date_str:
            raise ValidationError({"date": "date parameter (YYYY-MM-DD) is required."})

        target_date = parse_date(date_str)
        if not target_date:
            raise ValidationError({"date": "Invalid date format. Use YYYY-MM-DD."})

        doctor_clinic = get_object_or_404(
            DoctorClinic.objects.select_related("doctor__user", "clinic"),
            pk=dc_id,
        )

        availability = generate_doctor_availability_slots(
            doctor_clinic=doctor_clinic,
            target_date=target_date,
        )

        return Response(availability, status=status.HTTP_200_OK)


class DoctorMasterScheduleView(APIView):
    """
    Unified multi-clinic weekly schedule view for the authenticated doctor.
    Groups all recurring shifts across all affiliated clinics by day of the week.
    """

    @extend_schema(
        summary="Doctor Unified Multi-Clinic Weekly Schedule",
        description="Returns doctor's complete weekly schedule across all affiliated clinics grouped by day of week.",
        responses={200: OpenApiResponse(description="Doctor master schedule.")},
    )
    def get(self, request):
        user = request.user
        if not hasattr(user, "doctor_profile"):
            raise ValidationError("User does not have an active doctor profile.")

        doctor = user.doctor_profile
        schedules = DoctorSchedule.objects.filter(
            doctor_clinic__doctor=doctor,
            is_active=True,
        ).select_related(
            "doctor_clinic__clinic",
        ).order_by("day_of_week", "start_time")

        serialized = DoctorScheduleSerializer(schedules, many=True).data

        grouped = {w.value: {"day_of_week": w.value, "day_name": w.label, "shifts": []} for w in Weekday}
        for item in serialized:
            grouped[item["day_of_week"]]["shifts"].append(item)

        return Response({
            "doctor": {
                "id": str(doctor.id),
                "full_name": doctor.full_name,
                "specialization": doctor.specialization,
            },
            "total_active_shifts": len(serialized),
            "weekly_schedule": list(grouped.values()),
        }, status=status.HTTP_200_OK)
