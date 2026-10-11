import os
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.services import log_audit_event
from .models import (
    Doctor,
    DoctorDocument,
    DoctorVerificationStatus,
    Specialization,
)
from .permissions import (
    CanLookupDoctorRegistration,
    IsDoctorDocumentOwnerOrAdmin,
    IsDoctorProfileOwner,
    IsDoctorUser,
)
from .serializers import (
    DoctorDocumentSerializer,
    DoctorDocumentUploadSerializer,
    DoctorProfileCreateSerializer,
    DoctorProfileSerializer,
    DoctorProfileUpdateSerializer,
    DoctorRegistrationLookupSerializer,
    SpecializationSerializer,
)
from .validators import normalize_council_name, normalize_registration_number


class DoctorProfileCreateView(APIView):
    """
    Endpoint for creating an initial Doctor profile for the authenticated DOCTOR user.
    """

    permission_classes = [IsDoctorUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="Create Doctor Profile",
        description="Creates a practitioner profile for the authenticated doctor user in DRAFT status.",
        request=DoctorProfileCreateSerializer,
        responses={
            201: DoctorProfileSerializer,
            400: OpenApiResponse(description="Validation error or profile already exists."),
            403: OpenApiResponse(description="Forbidden."),
        },
    )
    def post(self, request):
        if Doctor.objects.filter(user=request.user).exists():
            return Response(
                {
                    "success": False,
                    "message": "A doctor profile already exists for this account.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DoctorProfileCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()

        log_audit_event(
            action="DOCTOR_PROFILE_CREATED",
            resource_type="Doctor",
            resource_id=str(doctor.id),
            actor=request.user,
            request=request,
            details={
                "full_name": doctor.full_name,
                "registration_council": doctor.registration_council,
                "status": doctor.verification_status,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Doctor profile created successfully.",
                "data": DoctorProfileSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DoctorMeView(APIView):
    """
    Endpoint for the authenticated doctor to retrieve or update their profile.
    """

    permission_classes = [IsDoctorUser, IsDoctorProfileOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="Get My Doctor Profile",
        description="Retrieves the authenticated doctor's full profile including verification status.",
        responses={
            200: DoctorProfileSerializer,
            404: OpenApiResponse(description="Profile not found."),
        },
    )
    def get(self, request):
        doctor = Doctor.objects.filter(user=request.user).select_related(
            "user", "verified_by"
        ).prefetch_related("documents").first()

        if not doctor:
            return Response(
                {
                    "success": False,
                    "message": "Doctor profile has not been created yet.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "data": DoctorProfileSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update My Doctor Profile",
        description="Updates permitted profile fields for the authenticated doctor.",
        request=DoctorProfileUpdateSerializer,
        responses={
            200: DoctorProfileSerializer,
            400: OpenApiResponse(description="Validation error."),
            404: OpenApiResponse(description="Profile not found."),
        },
    )
    def patch(self, request):
        doctor = Doctor.objects.filter(user=request.user).first()
        if not doctor:
            return Response(
                {
                    "success": False,
                    "message": "Doctor profile has not been created yet.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DoctorProfileUpdateSerializer(
            doctor, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_doctor = serializer.save()

        log_audit_event(
            action="DOCTOR_PROFILE_UPDATED",
            resource_type="Doctor",
            resource_id=str(updated_doctor.id),
            actor=request.user,
            request=request,
            details={
                "updated_fields": list(request.data.keys()),
                "status": updated_doctor.verification_status,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Doctor profile updated successfully.",
                "data": DoctorProfileSerializer(updated_doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class DoctorSubmitVerificationView(APIView):
    """
    Doctor submits their completed profile for Super Admin verification review.
    Transitions: DRAFT -> PENDING or REJECTED -> PENDING.
    """

    permission_classes = [IsDoctorUser]

    @extend_schema(
        summary="Submit Doctor Profile for Verification",
        description="Submits the authenticated doctor's profile for verification review.",
        responses={
            200: DoctorProfileSerializer,
            400: OpenApiResponse(description="Cannot submit in current state."),
            404: OpenApiResponse(description="Profile not found."),
        },
    )
    def post(self, request):
        doctor = Doctor.objects.filter(user=request.user).first()
        if not doctor:
            return Response(
                {
                    "success": False,
                    "message": "Doctor profile has not been created yet.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if doctor.verification_status == DoctorVerificationStatus.VERIFIED:
            return Response(
                {
                    "success": False,
                    "message": "Your profile is already verified.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if doctor.verification_status == DoctorVerificationStatus.PENDING:
            return Response(
                {
                    "success": False,
                    "message": "Your profile is already pending administrative verification.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if doctor.verification_status == DoctorVerificationStatus.SUSPENDED:
            return Response(
                {
                    "success": False,
                    "message": "Suspended doctor profiles cannot be submitted. Please contact platform administration.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate mandatory details before submission
        missing_fields = []
        if not doctor.registration_number:
            missing_fields.append("registration_number")
        if not doctor.registration_council:
            missing_fields.append("registration_council")
        if not doctor.specialization:
            missing_fields.append("specialization")
        if not doctor.qualifications:
            missing_fields.append("qualifications")
        if not doctor.full_name:
            missing_fields.append("full_name")

        if missing_fields:
            return Response(
                {
                    "success": False,
                    "message": f"Please complete all required fields before submitting: {', '.join(missing_fields)}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor.verification_status = DoctorVerificationStatus.PENDING
        doctor.submitted_at = timezone.now()
        doctor.verification_notes = ""  # Clear previous rejection notes on fresh submission
        doctor.is_verified = False
        doctor.save(update_fields=["verification_status", "submitted_at", "verification_notes", "is_verified", "updated_at"])

        log_audit_event(
            action="DOCTOR_SUBMITTED_VERIFICATION",
            resource_type="Doctor",
            resource_id=str(doctor.id),
            actor=request.user,
            request=request,
            details={
                "registration_number": doctor.registration_number,
                "registration_council": doctor.registration_council,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Doctor profile submitted successfully for verification.",
                "data": DoctorProfileSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class DoctorRegistrationLookupView(APIView):
    """
    Privacy-preserving lookup endpoint for Clinic Owners to check if a doctor
    is registered and verified before sending clinic invitations.
    Never exposes phone number, email, internal documents, or notes.
    """

    permission_classes = [CanLookupDoctorRegistration]

    @extend_schema(
        summary="Lookup Doctor by Registration Number",
        description="Search for a doctor by medical registration number and optional council. Scoped for Clinic Owners.",
        responses={
            200: DoctorRegistrationLookupSerializer,
            400: OpenApiResponse(description="Missing parameters or ambiguous query."),
            403: OpenApiResponse(description="Forbidden."),
        },
    )
    def get(self, request):
        reg_number = request.query_params.get("registration_number")
        if not reg_number or not reg_number.strip():
            return Response(
                {
                    "success": False,
                    "message": "The 'registration_number' query parameter is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        norm_number = normalize_registration_number(reg_number)
        council = request.query_params.get("registration_council")

        queryset = Doctor.objects.select_related("user")
        if council and council.strip():
            norm_council = normalize_council_name(council)
            queryset = queryset.filter(
                normalized_registration_number=norm_number,
                normalized_registration_council=norm_council,
            )
        else:
            queryset = queryset.filter(normalized_registration_number=norm_number)

        matches_count = queryset.count()
        if matches_count > 1:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Multiple registration records match this identifier across different medical councils. "
                        "Please provide the 'registration_council' parameter to specify the authority."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = queryset.first()
        if not doctor:
            data = {
                "found": False,
                "doctor_id": None,
                "full_name": None,
                "specialization": None,
                "registration_council": None,
                "registration_number": None,
                "is_verified": False,
                "is_eligible_for_invitation": False,
                "message": "No matching doctor profile found for the provided registration details.",
            }
        else:
            data = {
                "found": True,
                "doctor_id": doctor.id,
                "full_name": doctor.full_name,
                "specialization": doctor.specialization,
                "registration_council": doctor.registration_council,
                "registration_number": doctor.registration_number,
                "is_verified": doctor.is_verified,
                "is_eligible_for_invitation": doctor.is_eligible_for_clinics,
                "message": None,
            }

        return Response(
            {
                "success": True,
                "data": DoctorRegistrationLookupSerializer(data).data,
            },
            status=status.HTTP_200_OK,
        )


class DoctorDocumentListCreateView(APIView):
    """
    Endpoint for doctors to manage private registration evidence documents.
    """

    permission_classes = [IsDoctorUser]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="List Doctor Documents",
        description="Lists all verification documents uploaded by the authenticated doctor.",
        responses={200: DoctorDocumentSerializer(many=True)},
    )
    def get(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)
        documents = doctor.documents.all().order_by("-uploaded_at")
        serializer = DoctorDocumentSerializer(documents, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Upload Doctor Document",
        description="Uploads a registration certificate or qualification proof privately.",
        request=DoctorDocumentUploadSerializer,
        responses={201: DoctorDocumentSerializer, 400: OpenApiResponse(description="Validation error.")},
    )
    def post(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)
        serializer = DoctorDocumentUploadSerializer(
            data=request.data, context={"request": request, "doctor": doctor}
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        log_audit_event(
            action="DOCTOR_DOCUMENT_UPLOADED",
            resource_type="DoctorDocument",
            resource_id=str(document.id),
            actor=request.user,
            request=request,
            details={"document_type": document.document_type, "file_name": document.file_name},
        )

        return Response(
            {
                "success": True,
                "message": "Document uploaded successfully.",
                "data": DoctorDocumentSerializer(document).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DoctorDocumentDeleteView(APIView):
    """
    Allows a doctor to delete an uploaded verification document.
    """

    permission_classes = [IsDoctorUser, IsDoctorDocumentOwnerOrAdmin]

    @extend_schema(
        summary="Delete Doctor Document",
        description="Deletes an uploaded verification document.",
        responses={200: OpenApiResponse(description="Deleted successfully."), 404: OpenApiResponse(description="Not found.")},
    )
    def delete(self, request, pk):
        document = get_object_or_404(DoctorDocument, pk=pk)
        self.check_object_permissions(request, document)

        # Remove physical file if present
        try:
            if document.file and os.path.isfile(document.file.path):
                os.remove(document.file.path)
        except Exception:
            pass

        document.delete()
        return Response({"success": True, "message": "Document removed successfully."}, status=status.HTTP_200_OK)


class DoctorDocumentDownloadView(APIView):
    """
    Secure file streaming endpoint for doctors to view their private uploaded documents.
    """

    permission_classes = [IsDoctorUser, IsDoctorDocumentOwnerOrAdmin]

    def get(self, request, pk):
        document = get_object_or_404(DoctorDocument, pk=pk)
        self.check_object_permissions(request, document)

        if not document.file or not os.path.exists(document.file.path):
            raise Http404("Document file not found on disk.")

        response = FileResponse(open(document.file.path, "rb"), content_type=document.mime_type or "application/octet-stream")
        response["Content-Disposition"] = f'inline; filename="{document.file_name}"'
        return response


class SpecializationListView(APIView):
    """
    Catalog of medical specializations for dropdown selectors.
    """

    def get(self, request):
        specializations = Specialization.objects.all().order_by("name")
        serializer = SpecializationSerializer(specializations, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)
