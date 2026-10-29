from datetime import datetime
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.accounts.permissions import (
    IsAuthenticatedUser,
    IsClinicStaffOrOwner,
    IsDoctor,
    IsPatient,
)
from apps.audit_logs.services import log_audit_event
from apps.clinics.models import Clinic, ClinicStaffPermission
from apps.clinics.permissions import check_clinic_access
from apps.doctors.models import Doctor
from .models import Appointment, AppointmentHistory, AppointmentHistoryEventType, AppointmentStatus
from .permissions import CanAccessAppointment
from .serializers import (
    AppointmentBookingRequestSerializer,
    AppointmentCancelRequestSerializer,
    AppointmentDetailSerializer,
    AppointmentHistorySerializer,
    AppointmentListSerializer,
    AppointmentReportUnavailabilityRequestSerializer,
    AppointmentRescheduleRequestSerializer,
)
from .services import (
    book_appointment,
    cancel_appointment,
    complete_appointment,
    mark_no_show,
    reschedule_appointment,
    report_doctor_unavailability_for_appointment,
)


class AppointmentCreateView(APIView):
    """
    POST /api/v1/appointments/
    Creates a new patient appointment slot booking atomically with anti-double-booking protection.
    Accepts Idempotency-Key via header or body payload.
    """
    permission_classes = [IsAuthenticatedUser, IsPatient]

    @extend_schema(
        summary="Book Patient Appointment",
        description="Creates an appointment booking for the authenticated patient with concurrency protection and price snapshotting.",
        request=AppointmentBookingRequestSerializer,
        responses={
            201: AppointmentDetailSerializer,
            400: "Bad Request - invalid slot format or past date",
            409: "Conflict - slot already booked or travel buffer violation",
        },
    )
    def post(self, request):
        serializer = AppointmentBookingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        # Resolve idempotency key from header or body
        idempotency_key = (
            request.headers.get("Idempotency-Key")
            or request.headers.get("X-Idempotency-Key")
            or validated.get("idempotency_key")
        )

        appointment, is_new = book_appointment(
            patient=request.user,
            clinic_id=validated["clinic_id"],
            doctor_id=validated["doctor_id"],
            start_at=validated["start_at"],
            patient_note=validated.get("patient_note", ""),
            idempotency_key=idempotency_key,
        )

        resp_serializer = AppointmentDetailSerializer(appointment)
        http_status = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
        return Response(resp_serializer.data, status=http_status)


class PatientAppointmentsListView(generics.ListAPIView):
    """
    GET /api/v1/appointments/my/
    Returns the authenticated patient's booked appointments with filtering support.
    """
    permission_classes = [IsAuthenticatedUser, IsPatient]
    serializer_class = AppointmentListSerializer

    @extend_schema(
        summary="List My Appointments",
        description="Lists all appointments belonging to the authenticated patient.",
        parameters=[
            OpenApiParameter(name="filter", type=str, description="upcoming | past"),
            OpenApiParameter(name="status", type=str, description="AppointmentStatus value"),
            OpenApiParameter(name="date", type=str, description="YYYY-MM-DD"),
        ],
    )
    def get_queryset(self):
        qs = (
            Appointment.objects.filter(patient=self.request.user)
            .select_related("doctor", "clinic")
            .order_by("-start_at")
        )

        status_param = self.request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            qs = qs.filter(status=status_param.upper())

        time_filter = self.request.query_params.get("filter")
        now = timezone.now()
        if time_filter == "upcoming":
            qs = qs.filter(start_at__gte=now).order_by("start_at")
        elif time_filter == "past":
            qs = qs.filter(start_at__lt=now).order_by("-start_at")

        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                parsed_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                qs = qs.filter(start_at__date=parsed_date)
            except ValueError:
                pass

        return qs


class AppointmentDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/appointments/{appointment_id}/
    Retrieves full appointment details for authorized patient, clinic owner, staff, or doctor.
    """
    permission_classes = [IsAuthenticatedUser, CanAccessAppointment]
    serializer_class = AppointmentDetailSerializer
    queryset = Appointment.objects.select_related("doctor", "clinic", "patient").all()
    lookup_field = "id"
    lookup_url_kwarg = "appointment_id"


class ClinicAppointmentsListView(generics.ListAPIView):
    """
    GET /api/v1/clinics/{clinic_id}/appointments/
    Lists appointments for an authorized clinic owner or staff member with VIEW_APPOINTMENTS permission.
    Supports filtering by doctor, status, date, date range, upcoming/past, keyword search, and requires_attention.
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]
    serializer_class = AppointmentDetailSerializer

    @extend_schema(
        summary="List Clinic Appointments",
        description="Lists appointments for a specific clinic. Restricted to clinic owner and authorized staff.",
        parameters=[
            OpenApiParameter(name="doctor_id", type=str, description="Filter by doctor UUID"),
            OpenApiParameter(name="status", type=str, description="AppointmentStatus filter"),
            OpenApiParameter(name="date", type=str, description="Filter by YYYY-MM-DD"),
            OpenApiParameter(name="from_date", type=str, description="Start date YYYY-MM-DD"),
            OpenApiParameter(name="to_date", type=str, description="End date YYYY-MM-DD"),
            OpenApiParameter(name="filter", type=str, description="upcoming | past"),
            OpenApiParameter(name="requires_attention", type=bool, description="Filter appointments requiring attention"),
            OpenApiParameter(name="search", type=str, description="Search by booking reference or patient details"),
        ],
    )
    def get_queryset(self):
        clinic_id = self.kwargs["clinic_id"]
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        user = self.request.user
        if not check_clinic_access(user, clinic, required_permission=ClinicStaffPermission.VIEW_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to view appointments for this clinic.")

        qs = (
            Appointment.objects.filter(clinic_id=clinic_id)
            .select_related("doctor", "clinic", "patient", "doctor_clinic")
            .order_by("-start_at")
        )

        doctor_id = self.request.query_params.get("doctor_id")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)

        status_param = self.request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            qs = qs.filter(status=status_param.upper())

        time_filter = self.request.query_params.get("filter")
        now = timezone.now()
        if time_filter == "upcoming":
            qs = qs.filter(start_at__gte=now).order_by("start_at")
        elif time_filter == "past":
            qs = qs.filter(start_at__lt=now).order_by("-start_at")

        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                parsed_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                qs = qs.filter(start_at__date=parsed_date)
            except ValueError:
                pass

        from_date = self.request.query_params.get("from_date")
        if from_date:
            try:
                parsed_from = datetime.strptime(from_date, "%Y-%m-%d").date()
                qs = qs.filter(start_at__date__gte=parsed_from)
            except ValueError:
                pass

        to_date = self.request.query_params.get("to_date")
        if to_date:
            try:
                parsed_to = datetime.strptime(to_date, "%Y-%m-%d").date()
                qs = qs.filter(start_at__date__lte=parsed_to)
            except ValueError:
                pass

        requires_attention = self.request.query_params.get("requires_attention")
        if requires_attention is not None and str(requires_attention).lower() in ("true", "1"):
            qs = qs.filter(
                Q(reschedule_required=True)
                | Q(status=AppointmentStatus.RESCHEDULE_REQUIRED)
                | Q(status=AppointmentStatus.PENDING_CONFIRMATION)
            )

        search_param = self.request.query_params.get("search")
        if search_param:
            search_val = search_param.strip()
            qs = qs.filter(
                Q(booking_reference__icontains=search_val)
                | Q(patient__first_name__icontains=search_val)
                | Q(patient__last_name__icontains=search_val)
                | Q(patient__email__icontains=search_val)
                | Q(patient__phone__icontains=search_val)
            )

        return qs


class DoctorAppointmentsListView(generics.ListAPIView):
    """
    GET /api/v1/doctors/me/appointments/
    Lists appointments associated with the authenticated doctor's profile across all their clinic affiliations.
    """
    permission_classes = [IsAuthenticatedUser, IsDoctor]
    serializer_class = AppointmentDetailSerializer

    @extend_schema(
        summary="List Doctor Appointments",
        description="Lists appointments for the authenticated doctor.",
        parameters=[
            OpenApiParameter(name="clinic_id", type=str, description="Filter by clinic UUID"),
            OpenApiParameter(name="status", type=str, description="AppointmentStatus filter"),
            OpenApiParameter(name="date", type=str, description="Filter by YYYY-MM-DD"),
            OpenApiParameter(name="filter", type=str, description="upcoming | past"),
        ],
    )
    def get_queryset(self):
        doctor = Doctor.objects.filter(user=self.request.user).first()
        if not doctor:
            raise NotFound("Doctor profile not found for authenticated user.")

        qs = (
            Appointment.objects.filter(doctor=doctor)
            .select_related("doctor", "clinic", "patient")
            .order_by("-start_at")
        )

        clinic_id = self.request.query_params.get("clinic_id")
        if clinic_id:
            qs = qs.filter(clinic_id=clinic_id)

        status_param = self.request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            qs = qs.filter(status=status_param.upper())

        time_filter = self.request.query_params.get("filter")
        now = timezone.now()
        if time_filter == "upcoming":
            qs = qs.filter(start_at__gte=now).order_by("start_at")
        elif time_filter == "past":
            qs = qs.filter(start_at__lt=now).order_by("-start_at")

        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                parsed_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                qs = qs.filter(start_at__date=parsed_date)
            except ValueError:
                pass

        return qs


class AppointmentCancelView(APIView):
    """
    POST /api/v1/appointments/{appointment_id}/cancel/
    Allows an authorized patient (or authorized clinic owner/staff/doctor/admin) to cancel an eligible appointment.
    Enforces clinic timezone cutoff rules for patient actions.
    """
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        summary="Cancel Appointment",
        description="Cancels an eligible appointment with clinic timezone cutoff enforcement.",
        request=AppointmentCancelRequestSerializer,
        responses={
            200: AppointmentDetailSerializer,
            400: "Bad Request - invalid request",
            403: "Permission Denied - cannot cancel another patient's appointment",
            404: "Not Found",
            409: "Conflict - cutoff exceeded or invalid appointment state",
        },
    )
    def post(self, request, appointment_id):
        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment:
            raise NotFound("Appointment not found.")

        user = request.user
        if user.role == UserRole.PATIENT:
            if appointment.patient_id != user.id:
                raise PermissionDenied("You can only cancel your own appointments.")
        elif user.role == UserRole.CLINIC_OWNER:
            if appointment.clinic.owner_id != user.id:
                raise PermissionDenied("You do not have permission to manage appointments for this clinic.")
        elif user.role == UserRole.STAFF:
            if (
                not hasattr(user, "staff_profile")
                or not user.staff_profile.is_active
                or user.staff_profile.clinic_id != appointment.clinic_id
                or not user.staff_profile.has_permission(ClinicStaffPermission.MANAGE_APPOINTMENTS)
            ):
                raise PermissionDenied("You do not have permission to manage appointments for this clinic.")
        elif user.role == UserRole.DOCTOR:
            if appointment.doctor.user_id != user.id:
                raise PermissionDenied("You can only manage appointments assigned to your doctor profile.")
        elif user.role != UserRole.SUPER_ADMIN:
            raise PermissionDenied("You do not have permission to cancel this appointment.")

        serializer = AppointmentCancelRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        is_exception = (user.role != UserRole.PATIENT)
        cancelled_appt = cancel_appointment(
            appointment=appointment,
            cancelled_by=user,
            reason=reason,
            is_exception=is_exception,
            actor_role=user.role,
        )
        return Response(AppointmentDetailSerializer(cancelled_appt).data, status=status.HTTP_200_OK)


class AppointmentRescheduleView(APIView):
    """
    POST /api/v1/appointments/{appointment_id}/reschedule/
    Allows an authorized patient (or authorized staff) to reschedule an eligible appointment to a new slot.
    Doctor, clinic, fee, and patient identity cannot be changed.
    """
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        summary="Reschedule Appointment",
        description="Atomically reschedules an appointment to a destination slot for the same doctor and clinic.",
        request=AppointmentRescheduleRequestSerializer,
        responses={
            200: AppointmentDetailSerializer,
            400: "Bad Request - invalid parameters or past date",
            403: "Permission Denied",
            404: "Not Found",
            409: "Conflict - slot unavailable, travel buffer conflict, or cutoff exceeded",
        },
    )
    def post(self, request, appointment_id):
        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "doctor_clinic", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment:
            raise NotFound("Appointment not found.")

        user = request.user
        if user.role == UserRole.PATIENT:
            if appointment.patient_id != user.id:
                raise PermissionDenied("You can only reschedule your own appointments.")
        elif user.role == UserRole.CLINIC_OWNER:
            if appointment.clinic.owner_id != user.id:
                raise PermissionDenied("You do not have permission to manage appointments for this clinic.")
        elif user.role == UserRole.STAFF:
            if (
                not hasattr(user, "staff_profile")
                or not user.staff_profile.is_active
                or user.staff_profile.clinic_id != appointment.clinic_id
                or not user.staff_profile.has_permission(ClinicStaffPermission.MANAGE_APPOINTMENTS)
            ):
                raise PermissionDenied("You do not have permission to manage appointments for this clinic.")
        elif user.role != UserRole.SUPER_ADMIN:
            raise PermissionDenied("You do not have permission to reschedule this appointment.")

        serializer = AppointmentRescheduleRequestSerializer(
            data=request.data,
            context={"appointment": appointment},
        )
        serializer.is_valid(raise_exception=True)
        new_start_at = serializer.validated_data["start_at"]
        reason = serializer.validated_data.get("reason", "")

        is_exception = (user.role != UserRole.PATIENT)
        rescheduled_appt = reschedule_appointment(
            appointment=appointment,
            rescheduled_by=user,
            new_start_at=new_start_at,
            reason=reason,
            is_exception=is_exception,
            actor_role=user.role,
        )
        return Response(AppointmentDetailSerializer(rescheduled_appt).data, status=status.HTTP_200_OK)


class AppointmentHistoryListView(APIView):
    """
    GET /api/v1/appointments/{appointment_id}/history/
    Returns the chronological audit trail for the specified appointment.
    Strictly enforces tenant and ownership isolation.
    """
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        summary="Get Appointment History",
        description="Retrieves the append-only audit trail for an appointment.",
        responses={
            200: AppointmentHistorySerializer(many=True),
            403: "Permission Denied - cannot access another user's appointment history",
            404: "Not Found",
        },
    )
    def get(self, request, appointment_id):
        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment:
            raise NotFound("Appointment not found.")

        user = request.user
        if user.role == UserRole.PATIENT:
            if appointment.patient_id != user.id:
                raise PermissionDenied("You cannot view the history of an appointment that does not belong to you.")
        elif user.role == UserRole.CLINIC_OWNER:
            if appointment.clinic.owner_id != user.id:
                raise PermissionDenied("You do not have permission to view appointments for this clinic.")
        elif user.role == UserRole.STAFF:
            if (
                not hasattr(user, "staff_profile")
                or not user.staff_profile.is_active
                or user.staff_profile.clinic_id != appointment.clinic_id
                or not user.staff_profile.has_permission(ClinicStaffPermission.VIEW_APPOINTMENTS)
            ):
                raise PermissionDenied("You do not have permission to view appointments for this clinic.")
        elif user.role == UserRole.DOCTOR:
            if appointment.doctor.user_id != user.id:
                raise PermissionDenied("You can only view history for appointments assigned to your doctor profile.")
        elif user.role != UserRole.SUPER_ADMIN:
            raise PermissionDenied("You do not have permission to view this appointment history.")

        history_qs = appointment.history.select_related("actor").order_by("-created_at")
        serializer = AppointmentHistorySerializer(history_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClinicAppointmentCancelView(APIView):
    """
    POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/cancel/
    Authorized clinic management endpoint to cancel an appointment (authorized exception).
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]

    @extend_schema(
        summary="Clinic Cancel Appointment",
        description="Cancels an appointment within the clinic's tenant scope with documented reason.",
        request=AppointmentCancelRequestSerializer,
        responses={
            200: AppointmentDetailSerializer,
            403: "Permission Denied",
            404: "Not Found",
        },
    )
    def post(self, request, clinic_id, appointment_id):
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        user = request.user
        if not check_clinic_access(user, clinic, required_permission=ClinicStaffPermission.MANAGE_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to manage appointments for this clinic.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.clinic_id) != str(clinic.id):
            raise NotFound("Appointment not found for this clinic.")

        serializer = AppointmentCancelRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        cancelled_appt = cancel_appointment(
            appointment=appointment,
            cancelled_by=user,
            reason=reason,
            is_exception=True,
            actor_role=user.role,
        )
        return Response(AppointmentDetailSerializer(cancelled_appt).data, status=status.HTTP_200_OK)


class ClinicAppointmentRescheduleView(APIView):
    """
    POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/reschedule/
    Authorized clinic management endpoint to reschedule an appointment (authorized exception).
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]

    @extend_schema(
        summary="Clinic Reschedule Appointment",
        description="Reschedules an appointment within the clinic's tenant scope.",
        request=AppointmentRescheduleRequestSerializer,
        responses={
            200: AppointmentDetailSerializer,
            403: "Permission Denied",
            404: "Not Found",
            409: "Conflict",
        },
    )
    def post(self, request, clinic_id, appointment_id):
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        user = request.user
        if not check_clinic_access(user, clinic, required_permission=ClinicStaffPermission.MANAGE_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to manage appointments for this clinic.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "doctor_clinic", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.clinic_id) != str(clinic.id):
            raise NotFound("Appointment not found for this clinic.")

        serializer = AppointmentRescheduleRequestSerializer(
            data=request.data,
            context={"appointment": appointment},
        )
        serializer.is_valid(raise_exception=True)
        new_start_at = serializer.validated_data["start_at"]
        reason = serializer.validated_data.get("reason", "")

        rescheduled_appt = reschedule_appointment(
            appointment=appointment,
            rescheduled_by=user,
            new_start_at=new_start_at,
            reason=reason,
            is_exception=True,
            actor_role=user.role,
        )
        return Response(AppointmentDetailSerializer(rescheduled_appt).data, status=status.HTTP_200_OK)


class ClinicAppointmentReportUnavailabilityView(APIView):
    """
    POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/report-unavailability/
    Allows clinic staff or owner to report doctor or clinic unavailability for an appointment.
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]

    @extend_schema(
        summary="Clinic Report Unavailability",
        description="Reports doctor/clinic unavailability for an appointment, triggering resolution workflow.",
        request=AppointmentReportUnavailabilityRequestSerializer,
        responses={
            200: AppointmentDetailSerializer,
            403: "Permission Denied",
            404: "Not Found",
        },
    )
    def post(self, request, clinic_id, appointment_id):
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        user = request.user
        if not check_clinic_access(user, clinic, required_permission=ClinicStaffPermission.MANAGE_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to manage appointments for this clinic.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.clinic_id) != str(clinic.id):
            raise NotFound("Appointment not found for this clinic.")

        serializer = AppointmentReportUnavailabilityRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]
        action = serializer.validated_data.get("action", "RESCHEDULE_REQUIRED")

        updated_appt = report_doctor_unavailability_for_appointment(
            appointment=appointment,
            reported_by=user,
            reason=reason,
            action=action,
        )
        return Response(AppointmentDetailSerializer(updated_appt).data, status=status.HTTP_200_OK)


class ClinicAppointmentDetailView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/
    Detailed representation of a specific clinic appointment including audit history.
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]

    @extend_schema(
        summary="Get Clinic Appointment Detail",
        description="Retrieves full appointment details and event history scoped to the clinic.",
    )
    def get(self, request, clinic_id, appointment_id):
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.VIEW_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to view appointments for this clinic.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "doctor_clinic", "patient")
            .prefetch_related("history", "history__actor")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.clinic_id) != str(clinic.id):
            raise NotFound("Appointment not found for this clinic.")

        data = AppointmentDetailSerializer(appointment).data
        history_qs = appointment.history.select_related("actor").order_by("-created_at")
        data["history"] = AppointmentHistorySerializer(history_qs, many=True).data

        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class ClinicAppointmentConfirmView(APIView):
    """
    POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/confirm/
    Confirms an appointment that is pending confirmation.
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]

    @extend_schema(
        summary="Confirm Clinic Appointment",
        description="Transitions an appointment from PENDING_CONFIRMATION to CONFIRMED.",
    )
    def post(self, request, clinic_id, appointment_id):
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.MANAGE_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to manage appointments for this clinic.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.clinic_id) != str(clinic.id):
            raise NotFound("Appointment not found for this clinic.")

        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
            raise ValidationError(f"Cannot confirm an appointment that is already {appointment.status.lower()}.")

        with transaction.atomic():
            locked = Appointment.objects.select_for_update().get(id=appointment.id)
            prev_status = locked.status
            locked.status = AppointmentStatus.CONFIRMED
            locked.reschedule_required = False
            locked.save(update_fields=["status", "reschedule_required", "updated_at"])

            AppointmentHistory.objects.create(
                appointment=locked,
                event_type=AppointmentHistoryEventType.CONFIRMED,
                previous_status=prev_status,
                new_status=AppointmentStatus.CONFIRMED,
                actor=request.user,
                actor_role=getattr(request.user, "role", ""),
                reason="Confirmed by clinic reception / administration.",
            )

            log_audit_event(
                action="APPOINTMENT_CONFIRMED",
                resource_type="Appointment",
                resource_id=str(locked.id),
                clinic_id=str(clinic.id),
                actor=request.user,
                request=request,
                details={"booking_reference": locked.booking_reference},
            )

        return Response(
            {
                "success": True,
                "message": "Appointment confirmed successfully.",
                "data": AppointmentDetailSerializer(locked).data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicAppointmentCompleteView(APIView):
    """
    POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/complete/
    Marks a completed consultation.
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]

    @extend_schema(
        summary="Complete Clinic Appointment",
        description="Marks an active consultation as COMPLETED.",
    )
    def post(self, request, clinic_id, appointment_id):
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.MANAGE_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to manage appointments for this clinic.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.clinic_id) != str(clinic.id):
            raise NotFound("Appointment not found for this clinic.")

        completed_appt = complete_appointment(appointment, request.user)

        log_audit_event(
            action="APPOINTMENT_COMPLETED",
            resource_type="Appointment",
            resource_id=str(completed_appt.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"booking_reference": completed_appt.booking_reference},
        )

        return Response(
            {
                "success": True,
                "message": "Appointment marked as completed.",
                "data": AppointmentDetailSerializer(completed_appt).data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicAppointmentNoShowView(APIView):
    """
    POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/no-show/
    Marks an appointment where the patient failed to attend as NO_SHOW.
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]

    @extend_schema(
        summary="Mark Clinic Appointment No-Show",
        description="Marks an unattended appointment as NO_SHOW.",
    )
    def post(self, request, clinic_id, appointment_id):
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.MANAGE_APPOINTMENTS):
            raise PermissionDenied("You do not have permission to manage appointments for this clinic.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.clinic_id) != str(clinic.id):
            raise NotFound("Appointment not found for this clinic.")

        no_show_appt = mark_no_show(appointment, request.user)

        log_audit_event(
            action="APPOINTMENT_MARKED_NO_SHOW",
            resource_type="Appointment",
            resource_id=str(no_show_appt.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"booking_reference": no_show_appt.booking_reference},
        )

        return Response(
            {
                "success": True,
                "message": "Appointment marked as No-Show.",
                "data": AppointmentDetailSerializer(no_show_appt).data,
            },
            status=status.HTTP_200_OK,
        )


class DoctorAppointmentReportUnavailabilityView(APIView):
    """
    POST /api/v1/doctors/me/appointments/{appointment_id}/report-unavailability/
    Allows an authenticated doctor to report unavailability for an appointment,
    marking it as requiring resolution and granting the patient exception rescheduling rights.
    """
    permission_classes = [IsAuthenticatedUser, IsDoctor]

    @extend_schema(
        summary="Doctor Report Unavailability",
        description="Reports doctor unavailability for a specific appointment.",
        request=AppointmentReportUnavailabilityRequestSerializer,
        responses={
            200: AppointmentDetailSerializer,
            403: "Permission Denied",
            404: "Not Found",
        },
    )
    def post(self, request, appointment_id):
        doctor = Doctor.objects.filter(user=request.user).first()
        if not doctor:
            raise NotFound("Doctor profile not found for authenticated user.")

        appointment = (
            Appointment.objects.select_related("clinic", "doctor", "patient")
            .filter(id=appointment_id)
            .first()
        )
        if not appointment or str(appointment.doctor_id) != str(doctor.id):
            raise NotFound("Appointment not found or not assigned to your doctor profile.")

        serializer = AppointmentReportUnavailabilityRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]
        action = serializer.validated_data.get("action", "RESCHEDULE_REQUIRED")

        updated_appt = report_doctor_unavailability_for_appointment(
            appointment=appointment,
            reported_by=request.user,
            reason=reason,
            action=action,
        )
        return Response(AppointmentDetailSerializer(updated_appt).data, status=status.HTTP_200_OK)


