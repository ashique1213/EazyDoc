from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404

from django.utils import timezone
from apps.accounts.models import UserRole
from apps.audit_logs.services import log_audit_event
from .models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from .permissions import CanManageClinics, IsClinicOwner
from .serializers import (
    ClinicCreateSerializer,
    ClinicSerializer,
    ClinicUpdateSerializer,
    DoctorClinicInvitationCreateSerializer,
    DoctorClinicSerializer,
    DoctorClinicSettingsUpdateSerializer,
)


class ClinicListCreateView(APIView):
    """
    Endpoint for creating and listing clinics.
    Clinic owners can register new clinics and list their own clinics.
    Super Admins can view all clinics.
    """

    permission_classes = [CanManageClinics]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="Create Clinic",
        description="Creates a new clinic owned by the authenticated clinic owner. Status defaults to PENDING (or DRAFT if requested).",
        request=ClinicCreateSerializer,
        responses={
            201: ClinicSerializer,
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden."),
        },
    )
    def post(self, request):
        serializer = ClinicCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        clinic = serializer.save()

        log_audit_event(
            action="CLINIC_REGISTERED",
            resource_type="Clinic",
            resource_id=str(clinic.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"name": clinic.name, "status": clinic.status},
        )

        return Response(
            {
                "success": True,
                "message": "Clinic registered successfully.",
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="List Clinics",
        description="List clinics. Scoped to the authenticated owner's clinics, or all for Super Admin.",
        responses={200: ClinicSerializer(many=True)},
    )
    def get(self, request):
        if request.user.role == UserRole.SUPER_ADMIN:
            clinics = Clinic.objects.all().select_related("owner", "approved_by").order_by("-created_at")
        else:
            clinics = Clinic.objects.filter(owner=request.user).select_related("owner", "approved_by").order_by("-created_at")

        serializer = ClinicSerializer(clinics, many=True, context={"request": request})
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class MyClinicsListView(APIView):
    """
    Lists only clinics owned by the authenticated clinic owner.
    """

    permission_classes = [CanManageClinics]

    @extend_schema(
        summary="List My Clinics",
        description="Lists all clinics owned by the authenticated user with tenant isolation.",
        responses={200: ClinicSerializer(many=True)},
    )
    def get(self, request):
        clinics = Clinic.objects.filter(owner=request.user).select_related("owner", "approved_by").order_by("-created_at")
        serializer = ClinicSerializer(clinics, many=True, context={"request": request})
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicDetailView(APIView):
    """
    Retrieve or update a specific clinic.
    Tenant isolation guarantees only the clinic's owner or Super Admin can access.
    """

    permission_classes = [CanManageClinics, IsClinicOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        clinic = get_object_or_404(
            Clinic.objects.select_related("owner", "approved_by"), pk=pk
        )
        self.check_object_permissions(self.request, clinic)
        return clinic

    @extend_schema(
        summary="Get Clinic Details",
        description="Retrieve clinic profile details. Enforces owner or Super Admin authorization.",
        responses={
            200: ClinicSerializer,
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Not Found."),
        },
    )
    def get(self, request, pk):
        clinic = self.get_object(pk)
        return Response(
            {
                "success": True,
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update Clinic Profile",
        description="Update permitted clinic profile fields. Ownership, status, and approval fields cannot be altered.",
        request=ClinicUpdateSerializer,
        responses={
            200: ClinicSerializer,
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Forbidden."),
        },
    )
    def patch(self, request, pk):
        clinic = self.get_object(pk)
        serializer = ClinicUpdateSerializer(
            clinic, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_clinic = serializer.save()

        log_audit_event(
            action="CLINIC_UPDATED",
            resource_type="Clinic",
            resource_id=str(updated_clinic.id),
            clinic_id=str(updated_clinic.id),
            actor=request.user,
            request=request,
            details={"updated_fields": list(serializer.validated_data.keys())},
        )

        return Response(
            {
                "success": True,
                "message": "Clinic profile updated successfully.",
                "data": ClinicSerializer(updated_clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicSubmitView(APIView):
    """
    Submit a draft or rejected clinic for Super Admin verification.
    Transitions status: DRAFT -> PENDING or REJECTED -> PENDING.
    """

    permission_classes = [CanManageClinics, IsClinicOwner]

    @extend_schema(
        summary="Submit Clinic for Verification",
        description="Transitions a DRAFT or REJECTED clinic to PENDING status for Super Admin review.",
        responses={
            200: ClinicSerializer,
            400: OpenApiResponse(description="Invalid transition."),
            403: OpenApiResponse(description="Forbidden."),
        },
    )
    def post(self, request, pk):
        clinic = get_object_or_404(Clinic, pk=pk)
        self.check_object_permissions(request, clinic)

        if clinic.status == ClinicStatus.PENDING:
            return Response(
                {
                    "success": False,
                    "message": "Clinic is already pending verification.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if clinic.status == ClinicStatus.APPROVED:
            return Response(
                {
                    "success": False,
                    "message": "Clinic is already approved.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if clinic.status == ClinicStatus.SUSPENDED:
            return Response(
                {
                    "success": False,
                    "message": "Suspended clinic cannot be submitted for verification. Please contact support.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if clinic.status not in (ClinicStatus.DRAFT, ClinicStatus.REJECTED):
            return Response(
                {
                    "success": False,
                    "message": f"Cannot submit clinic with status '{clinic.status}'.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Transition status to PENDING
        previous_status = clinic.status
        clinic.status = ClinicStatus.PENDING
        clinic.save(update_fields=["status", "updated_at"])

        log_audit_event(
            action="CLINIC_SUBMITTED_FOR_VERIFICATION",
            resource_type="Clinic",
            resource_id=str(clinic.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"previous_status": previous_status, "new_status": clinic.status},
        )

        return Response(
            {
                "success": True,
                "message": "Clinic successfully submitted for verification.",
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicDoctorListView(APIView):
    """
    List doctors associated with the clinic.
    Allows filtering by status (e.g. ?status=ACTIVE).
    Restricted to clinic owner and Super Admins.
    """

    permission_classes = [CanManageClinics]

    @extend_schema(
        summary="List Clinic Doctors",
        description="Lists all doctor associations for the specified clinic.",
        responses={
            200: DoctorClinicSerializer(many=True),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Clinic not found."),
        },
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            return Response(
                {"success": False, "message": "You do not have permission to manage this clinic."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = DoctorClinic.objects.filter(clinic=clinic).select_related(
            "doctor", "clinic", "invited_by"
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        serializer = DoctorClinicSerializer(queryset, many=True, context={"request": request})
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class ClinicDoctorInvitationView(APIView):
    """
    Manage doctor invitations for a clinic.
    GET: List pending/filtered invitations for the clinic.
    POST: Invite an eligible, verified doctor to an approved clinic (with safe re-invitation).
    """

    permission_classes = [CanManageClinics]

    @extend_schema(
        summary="List Clinic Doctor Invitations",
        description="Lists invitations issued for doctors at the specified clinic.",
        responses={
            200: DoctorClinicSerializer(many=True),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Clinic not found."),
        },
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            return Response(
                {"success": False, "message": "You do not have permission to manage this clinic."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = DoctorClinic.objects.filter(clinic=clinic).select_related(
            "doctor", "clinic", "invited_by"
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        else:
            # Default to INVITED if not specified
            queryset = queryset.filter(status=DoctorClinicStatus.INVITED)

        serializer = DoctorClinicSerializer(queryset, many=True, context={"request": request})
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Invite Doctor to Clinic",
        description="Creates or updates an invitation for an eligible verified doctor to affiliate with this approved clinic.",
        request=DoctorClinicInvitationCreateSerializer,
        responses={
            201: DoctorClinicSerializer,
            400: OpenApiResponse(description="Invalid request or ineligible clinic/doctor."),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Clinic or doctor not found."),
        },
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            return Response(
                {"success": False, "message": "You do not have permission to manage this clinic."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Clinic must be approved to issue invitations
        if clinic.status != ClinicStatus.APPROVED:
            return Response(
                {
                    "success": False,
                    "message": f"Only approved clinics can invite doctors. Current clinic status: {clinic.status}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DoctorClinicInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor_id = serializer.validated_data["doctor_id"]
        invitation_message = serializer.validated_data.get("invitation_message", "")
        consultation_fee = serializer.validated_data.get("consultation_fee")
        follow_up_fee = serializer.validated_data.get("follow_up_fee")
        appointment_duration_minutes = serializer.validated_data.get("appointment_duration_minutes", 15)

        from apps.doctors.models import Doctor

        doctor = Doctor.objects.filter(id=doctor_id).select_related("user").first()
        if not doctor:
            return Response(
                {"success": False, "message": "Doctor profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check doctor eligibility
        if not doctor.is_eligible_for_clinics:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only verified doctors with active user accounts can be invited. "
                        f"Current doctor verification status: {doctor.verification_status}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import transaction

        with transaction.atomic():
            association = (
                DoctorClinic.objects.select_for_update()
                .filter(doctor=doctor, clinic=clinic)
                .first()
            )

            if association:
                if association.status == DoctorClinicStatus.ACTIVE:
                    return Response(
                        {
                            "success": False,
                            "message": "Doctor is already an active practitioner at this clinic.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if association.status == DoctorClinicStatus.INVITED:
                    return Response(
                        {
                            "success": False,
                            "message": "An invitation is already pending for this doctor at this clinic.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if association.status == DoctorClinicStatus.SUSPENDED:
                    return Response(
                        {
                            "success": False,
                            "message": "This doctor-clinic association is currently suspended.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Re-invitation workflow for REJECTED or REMOVED associations
                previous_status = association.status
                association.status = DoctorClinicStatus.INVITED
                association.invited_by = request.user
                association.invitation_message = invitation_message
                if consultation_fee is not None:
                    association.consultation_fee = consultation_fee
                if follow_up_fee is not None:
                    association.follow_up_fee = follow_up_fee
                association.appointment_duration_minutes = appointment_duration_minutes
                association.accepted_at = None
                association.rejected_at = None
                association.removed_at = None
                association.save()

                log_audit_event(
                    action="DOCTOR_CLINIC_REINVITED",
                    resource_type="DoctorClinic",
                    resource_id=str(association.id),
                    clinic_id=str(clinic.id),
                    actor=request.user,
                    request=request,
                    details={
                        "doctor_id": str(doctor.id),
                        "doctor_name": doctor.full_name,
                        "previous_status": previous_status,
                        "consultation_fee": str(association.consultation_fee),
                    },
                )
            else:
                association = DoctorClinic.objects.create(
                    doctor=doctor,
                    clinic=clinic,
                    status=DoctorClinicStatus.INVITED,
                    invited_by=request.user,
                    invitation_message=invitation_message,
                    consultation_fee=consultation_fee,
                    follow_up_fee=follow_up_fee,
                    appointment_duration_minutes=appointment_duration_minutes,
                )

                log_audit_event(
                    action="DOCTOR_CLINIC_INVITED",
                    resource_type="DoctorClinic",
                    resource_id=str(association.id),
                    clinic_id=str(clinic.id),
                    actor=request.user,
                    request=request,
                    details={
                        "doctor_id": str(doctor.id),
                        "doctor_name": doctor.full_name,
                        "consultation_fee": str(association.consultation_fee),
                        "appointment_duration_minutes": association.appointment_duration_minutes,
                    },
                )

        assoc_id = association.id
        from apps.notifications.services import handle_clinic_doctor_event
        transaction.on_commit(lambda: handle_clinic_doctor_event("clinic_invitation_sent", assoc_id))

        return Response(
            {
                "success": True,
                "message": "Invitation sent successfully to the doctor.",
                "data": DoctorClinicSerializer(association, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ClinicDoctorSettingsUpdateView(APIView):
    """
    Update clinic-specific commercial and scheduling settings for an active doctor.
    Protects status and global doctor verification from tampering.
    """

    permission_classes = [CanManageClinics]

    @extend_schema(
        summary="Update Clinic Doctor Settings",
        description="Configure consultation fee, follow-up fee, and slot duration for an active doctor association.",
        request=DoctorClinicSettingsUpdateSerializer,
        responses={
            200: DoctorClinicSerializer,
            400: OpenApiResponse(description="Invalid settings or association not active."),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Association not found at this clinic."),
        },
    )
    def patch(self, request, clinic_id, association_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            return Response(
                {"success": False, "message": "You do not have permission to manage this clinic."},
                status=status.HTTP_403_FORBIDDEN,
            )

        association = get_object_or_404(DoctorClinic, id=association_id, clinic=clinic)

        if association.status != DoctorClinicStatus.ACTIVE:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Clinic settings can only be modified for active doctor associations. "
                        f"Current status: {association.status}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DoctorClinicSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        update_fields = ["updated_at"]
        if "consultation_fee" in validated_data:
            association.consultation_fee = validated_data["consultation_fee"]
            update_fields.append("consultation_fee")
        if "follow_up_fee" in validated_data:
            association.follow_up_fee = validated_data["follow_up_fee"]
            update_fields.append("follow_up_fee")
        if "appointment_duration_minutes" in validated_data:
            association.appointment_duration_minutes = validated_data["appointment_duration_minutes"]
            update_fields.append("appointment_duration_minutes")

        association.save(update_fields=update_fields)

        log_audit_event(
            action="DOCTOR_CLINIC_SETTINGS_UPDATED",
            resource_type="DoctorClinic",
            resource_id=str(association.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={
                "doctor_id": str(association.doctor_id),
                "consultation_fee": str(association.consultation_fee),
                "follow_up_fee": str(association.follow_up_fee),
                "appointment_duration_minutes": association.appointment_duration_minutes,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Doctor association settings updated successfully.",
                "data": DoctorClinicSerializer(association, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class ClinicDoctorRemoveView(APIView):
    """
    Remove an active doctor from the clinic.
    Transitions association status from ACTIVE to REMOVED.
    Does not delete the doctor's global profile or affiliations with other clinics.
    """

    permission_classes = [CanManageClinics]

    @extend_schema(
        summary="Remove Doctor Association",
        description="Terminates an active association with a doctor for this clinic.",
        responses={
            200: DoctorClinicSerializer,
            400: OpenApiResponse(description="Association cannot be removed in current state."),
            403: OpenApiResponse(description="Forbidden."),
            404: OpenApiResponse(description="Association not found at this clinic."),
        },
    )
    def post(self, request, clinic_id, association_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            return Response(
                {"success": False, "message": "You do not have permission to manage this clinic."},
                status=status.HTTP_403_FORBIDDEN,
            )

        association = get_object_or_404(DoctorClinic, id=association_id, clinic=clinic)

        if association.status != DoctorClinicStatus.ACTIVE:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"Only active associations can be removed. Current status: {association.status}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        association.status = DoctorClinicStatus.REMOVED
        association.removed_at = timezone.now()
        association.save(update_fields=["status", "removed_at", "updated_at"])

        log_audit_event(
            action="DOCTOR_CLINIC_REMOVED",
            resource_type="DoctorClinic",
            resource_id=str(association.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={
                "doctor_id": str(association.doctor_id),
                "doctor_name": association.doctor.full_name,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Doctor association removed successfully.",
                "data": DoctorClinicSerializer(association, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
