import os
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.services import log_audit_event
from .models import Doctor, DoctorDocument, DoctorVerificationStatus
from .permissions import IsSuperAdminOnly
from .serializers import (
    DoctorAdminActionSerializer,
    DoctorAdminDetailSerializer,
)


class AdminDoctorPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminDoctorListView(APIView):
    """
    Super Admin endpoint for platform-wide doctor verification oversight.
    Supports filtering by verification status, specialty, and keyword search.
    """

    permission_classes = [IsSuperAdminOnly]
    pagination_class = AdminDoctorPagination

    @extend_schema(
        summary="Admin List Doctors",
        description="Lists all doctor profiles with filtering by status and search queries. Paginated.",
        responses={200: DoctorAdminDetailSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            Doctor.objects.all()
            .select_related("user", "verified_by")
            .prefetch_related("documents")
            .order_by("-created_at")
        )

        status_filter = request.query_params.get("status")
        if status_filter and status_filter.upper() != "ALL":
            queryset = queryset.filter(verification_status=status_filter.upper())

        search_query = request.query_params.get("search")
        if search_query:
            q = search_query.strip()
            queryset = queryset.filter(
                Q(full_name__icontains=q)
                | Q(registration_number__icontains=q)
                | Q(registration_council__icontains=q)
                | Q(specialization__icontains=q)
                | Q(user__email__icontains=q)
            )

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = DoctorAdminDetailSerializer(paginated_qs, many=True, context={"request": request})

        return paginator.get_paginated_response(serializer.data)


class AdminDoctorDetailView(APIView):
    """
    Super Admin endpoint to inspect a doctor's full profile, credentials, and verification documents.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Get Doctor Details",
        description="Retrieve full doctor profile including verification audit and documents.",
        responses={200: DoctorAdminDetailSerializer, 404: OpenApiResponse(description="Not found.")},
    )
    def get(self, request, pk):
        doctor = get_object_or_404(
            Doctor.objects.select_related("user", "verified_by").prefetch_related("documents"),
            pk=pk,
        )
        return Response(
            {
                "success": True,
                "data": DoctorAdminDetailSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDoctorVerifyView(APIView):
    """
    Super Admin verification approval endpoint.
    Transitions status: PENDING -> VERIFIED.
    Enforces business rule: An admin cannot verify their own doctor profile.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Verify Doctor",
        description="Verify a pending doctor profile. Records verifying admin and timestamp.",
        responses={
            200: DoctorAdminDetailSerializer,
            400: OpenApiResponse(description="Invalid transition."),
            403: OpenApiResponse(description="Cannot self-verify."),
        },
    )
    def post(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)

        # Invariant: An administrator cannot verify their own doctor profile
        if doctor.user_id == request.user.id:
            return Response(
                {
                    "success": False,
                    "message": "An administrator cannot verify their own doctor profile.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if doctor.verification_status != DoctorVerificationStatus.PENDING:
            return Response(
                {
                    "success": False,
                    "message": f"Only doctor profiles in PENDING status can be verified (current status: '{doctor.verification_status}').",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor.verification_status = DoctorVerificationStatus.VERIFIED
        doctor.verified_at = timezone.now()
        doctor.verified_by = request.user
        doctor.is_verified = True
        doctor.save(update_fields=["verification_status", "verified_at", "verified_by", "is_verified", "updated_at"])

        log_audit_event(
            action="DOCTOR_VERIFIED",
            resource_type="Doctor",
            resource_id=str(doctor.id),
            actor=request.user,
            request=request,
            details={
                "verified_by": str(request.user.id),
                "verified_at": str(doctor.verified_at),
                "registration_number": doctor.registration_number,
            },
        )

        return Response(
            {
                "success": True,
                "message": f"Doctor '{doctor.full_name}' has been successfully verified.",
                "data": DoctorAdminDetailSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDoctorRejectView(APIView):
    """
    Super Admin rejection endpoint.
    Transitions status: PENDING -> REJECTED.
    Requires mandatory rejection reason explaining required corrections.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Reject Doctor",
        description="Reject a doctor profile currently in PENDING status with a reason.",
        request=DoctorAdminActionSerializer,
        responses={200: DoctorAdminDetailSerializer, 400: OpenApiResponse(description="Validation error.")},
    )
    def post(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)

        if doctor.verification_status != DoctorVerificationStatus.PENDING:
            return Response(
                {
                    "success": False,
                    "message": f"Only doctor profiles in PENDING status can be rejected (current status: '{doctor.verification_status}').",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DoctorAdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        doctor.verification_status = DoctorVerificationStatus.REJECTED
        doctor.verification_notes = reason
        doctor.is_verified = False
        doctor.verified_at = timezone.now()
        doctor.verified_by = request.user
        doctor.save(update_fields=["verification_status", "verification_notes", "is_verified", "verified_at", "verified_by", "updated_at"])

        log_audit_event(
            action="DOCTOR_REJECTED",
            resource_type="Doctor",
            resource_id=str(doctor.id),
            actor=request.user,
            request=request,
            details={"reason": reason, "rejected_by": str(request.user.id)},
        )

        return Response(
            {
                "success": True,
                "message": f"Doctor '{doctor.full_name}' profile has been rejected.",
                "data": DoctorAdminDetailSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDoctorSuspendView(APIView):
    """
    Super Admin suspension endpoint.
    Transitions status: VERIFIED -> SUSPENDED.
    Suspended doctors cannot be scheduled or affiliated with clinics.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Suspend Doctor",
        description="Suspend a doctor profile with a reason.",
        request=DoctorAdminActionSerializer,
        responses={200: DoctorAdminDetailSerializer, 400: OpenApiResponse(description="Validation error.")},
    )
    def post(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)

        if doctor.verification_status == DoctorVerificationStatus.SUSPENDED:
            return Response(
                {
                    "success": False,
                    "message": "Doctor profile is already suspended.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DoctorAdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        doctor.verification_status = DoctorVerificationStatus.SUSPENDED
        doctor.verification_notes = reason
        doctor.is_verified = False
        doctor.verified_at = timezone.now()
        doctor.verified_by = request.user
        doctor.save(update_fields=["verification_status", "verification_notes", "is_verified", "verified_at", "verified_by", "updated_at"])

        log_audit_event(
            action="DOCTOR_SUSPENDED",
            resource_type="Doctor",
            resource_id=str(doctor.id),
            actor=request.user,
            request=request,
            details={"reason": reason, "suspended_by": str(request.user.id)},
        )

        return Response(
            {
                "success": True,
                "message": f"Doctor '{doctor.full_name}' profile has been suspended.",
                "data": DoctorAdminDetailSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDoctorReactivateView(APIView):
    """
    Super Admin reactivation endpoint.
    Transitions status: SUSPENDED -> VERIFIED.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Reactivate Doctor",
        description="Reactivates a suspended doctor back to VERIFIED.",
        responses={200: DoctorAdminDetailSerializer, 400: OpenApiResponse(description="Validation error.")},
    )
    def post(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)

        if doctor.verification_status != DoctorVerificationStatus.SUSPENDED:
            return Response(
                {
                    "success": False,
                    "message": f"Only SUSPENDED doctor profiles can be reactivated (current status: '{doctor.verification_status}').",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor.verification_status = DoctorVerificationStatus.VERIFIED
        doctor.is_verified = True
        doctor.verified_at = timezone.now()
        doctor.verified_by = request.user
        doctor.verification_notes = "Reactivated by platform administrator."
        doctor.save(update_fields=["verification_status", "is_verified", "verified_at", "verified_by", "verification_notes", "updated_at"])

        log_audit_event(
            action="DOCTOR_REACTIVATED",
            resource_type="Doctor",
            resource_id=str(doctor.id),
            actor=request.user,
            request=request,
            details={"reactivated_by": str(request.user.id)},
        )

        return Response(
            {
                "success": True,
                "message": f"Doctor '{doctor.full_name}' has been reactivated.",
                "data": DoctorAdminDetailSerializer(doctor, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDoctorDocumentDownloadView(APIView):
    """
    Secure file streaming endpoint for reviewing administrators to inspect verification evidence.
    """

    permission_classes = [IsSuperAdminOnly]

    def get(self, request, pk, doc_id):
        document = get_object_or_404(DoctorDocument, pk=doc_id, doctor_id=pk)

        if not document.file or not os.path.exists(document.file.path):
            raise Http404("Document file not found on disk.")

        response = FileResponse(open(document.file.path, "rb"), content_type=document.mime_type or "application/octet-stream")
        response["Content-Disposition"] = f'inline; filename="{document.file_name}"'
        return response
