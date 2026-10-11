from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404

from apps.accounts.models import UserRole
from apps.audit_logs.services import log_audit_event
from .models import Clinic, ClinicStatus
from .permissions import CanManageClinics, IsClinicOwner
from .serializers import (
    ClinicCreateSerializer,
    ClinicSerializer,
    ClinicUpdateSerializer,
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
