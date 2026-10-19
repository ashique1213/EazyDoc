from datetime import datetime
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from apps.accounts.permissions import (
    IsAuthenticatedUser,
    IsClinicStaffOrOwner,
    IsDoctor,
    IsPatient,
)
from apps.clinics.models import Clinic
from apps.doctors.models import Doctor
from .models import Appointment, AppointmentStatus
from .permissions import CanAccessAppointment
from .serializers import (
    AppointmentBookingRequestSerializer,
    AppointmentDetailSerializer,
    AppointmentListSerializer,
)
from .services import book_appointment


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
    Lists appointments for an authorized clinic owner or staff member.
    """
    permission_classes = [IsAuthenticatedUser, IsClinicStaffOrOwner]
    serializer_class = AppointmentDetailSerializer

    @extend_schema(
        summary="List Clinic Appointments",
        description="Lists appointments for a specific clinic. Restricted to clinic owner and staff.",
        parameters=[
            OpenApiParameter(name="doctor_id", type=str, description="Filter by doctor UUID"),
            OpenApiParameter(name="status", type=str, description="AppointmentStatus filter"),
            OpenApiParameter(name="date", type=str, description="Filter by YYYY-MM-DD"),
            OpenApiParameter(name="filter", type=str, description="upcoming | past"),
        ],
    )
    def get_queryset(self):
        clinic_id = self.kwargs["clinic_id"]
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            raise NotFound("Clinic not found.")

        # Ensure requesting user is owner or superadmin
        user = self.request.user
        if user.role != "SUPER_ADMIN" and clinic.owner_id != user.id:
            raise PermissionDenied("You do not have permission to view appointments for this clinic.")

        qs = (
            Appointment.objects.filter(clinic_id=clinic_id)
            .select_related("doctor", "clinic", "patient")
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
