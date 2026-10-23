from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiResponse, extend_schema
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.services import log_audit_event
from .models import Clinic, ClinicStatus
from .permissions import IsSuperAdminOnly
from .serializers import (
    ClinicAdminActionSerializer,
    ClinicSerializer,
)


class AdminClinicPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminClinicListView(APIView):
    """
    Super Admin endpoint for platform-wide clinic oversight.
    Supports filtering by verification status, city search, or clinic/owner keywords.
    """

    permission_classes = [IsSuperAdminOnly]
    pagination_class = AdminClinicPagination

    @extend_schema(
        summary="Admin List Clinics",
        description="Lists all clinics with filtering by status and keyword search. Paginated.",
        responses={200: ClinicSerializer(many=True)},
    )
    def get(self, request):
        queryset = Clinic.objects.all().select_related("owner", "approved_by").order_by("-created_at")

        # Status filter
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        # Date range filters
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

        # Keyword search
        search_query = request.query_params.get("search")
        if search_query:
            query = search_query.strip()
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(city__icontains=query)
                | Q(email__icontains=query)
                | Q(owner__email__icontains=query)
                | Q(owner__first_name__icontains=query)
                | Q(owner__last_name__icontains=query)
            )

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ClinicSerializer(paginated_qs, many=True, context={"request": request})

        return paginator.get_paginated_response(serializer.data)


class AdminClinicDetailView(APIView):
    """
    Super Admin endpoint to inspect any clinic's full profile and verification audit trail.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Get Clinic Details",
        description="Retrieve full clinic details for Super Admin verification.",
        responses={200: ClinicSerializer, 404: OpenApiResponse(description="Not Found.")},
    )
    def get(self, request, pk):
        clinic = get_object_or_404(
            Clinic.objects.select_related("owner", "approved_by"), pk=pk
        )
        return Response(
            {
                "success": True,
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminClinicApproveView(APIView):
    """
    Super Admin approval endpoint.
    Transitions status: PENDING -> APPROVED.
    Enforces business rule: A clinic owner cannot approve their own clinic.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Approve Clinic",
        description="Approve a clinic currently in PENDING status. Records approver and approval timestamp.",
        responses={
            200: ClinicSerializer,
            400: OpenApiResponse(description="Invalid transition."),
            403: OpenApiResponse(description="Owner cannot self-approve."),
        },
    )
    def post(self, request, pk):
        clinic = get_object_or_404(Clinic, pk=pk)

        # Invariant: Owner cannot approve their own clinic
        if clinic.owner_id == request.user.id:
            return Response(
                {
                    "success": False,
                    "message": "A clinic owner cannot approve their own clinic.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if clinic.status != ClinicStatus.PENDING:
            return Response(
                {
                    "success": False,
                    "message": f"Only clinics with PENDING status can be approved (current status: '{clinic.status}').",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        clinic.status = ClinicStatus.APPROVED
        clinic.approved_at = timezone.now()
        clinic.approved_by = request.user
        clinic.is_verified = True
        clinic.save(update_fields=["status", "approved_at", "approved_by", "is_verified", "updated_at"])

        log_audit_event(
            action="CLINIC_APPROVED",
            resource_type="Clinic",
            resource_id=str(clinic.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"approved_by": str(request.user.id), "approved_at": str(clinic.approved_at)},
        )

        return Response(
            {
                "success": True,
                "message": f"Clinic '{clinic.name}' has been successfully approved.",
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminClinicRejectView(APIView):
    """
    Super Admin rejection endpoint.
    Transitions status: PENDING -> REJECTED.
    Requires mandatory rejection reason explaining required corrections.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Reject Clinic",
        description="Reject a clinic currently in PENDING status. Requires a clear reason for the owner to correct.",
        request=ClinicAdminActionSerializer,
        responses={
            200: ClinicSerializer,
            400: OpenApiResponse(description="Validation or transition error."),
        },
    )
    def post(self, request, pk):
        clinic = get_object_or_404(Clinic, pk=pk)

        if clinic.status != ClinicStatus.PENDING:
            return Response(
                {
                    "success": False,
                    "message": f"Only clinics with PENDING status can be rejected (current status: '{clinic.status}').",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClinicAdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        clinic.status = ClinicStatus.REJECTED
        clinic.verification_notes = reason
        clinic.is_verified = False
        clinic.save(update_fields=["status", "verification_notes", "is_verified", "updated_at"])

        log_audit_event(
            action="CLINIC_REJECTED",
            resource_type="Clinic",
            resource_id=str(clinic.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"reason": reason},
        )

        return Response(
            {
                "success": True,
                "message": f"Clinic '{clinic.name}' has been rejected with feedback.",
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminClinicSuspendView(APIView):
    """
    Super Admin suspension endpoint.
    Transitions status: APPROVED -> SUSPENDED.
    Requires mandatory suspension reason. Suspended clinics cannot accept bookings.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Suspend Clinic",
        description="Suspend an APPROVED clinic. Requires mandatory reason.",
        request=ClinicAdminActionSerializer,
        responses={
            200: ClinicSerializer,
            400: OpenApiResponse(description="Validation or transition error."),
        },
    )
    def post(self, request, pk):
        clinic = get_object_or_404(Clinic, pk=pk)

        if clinic.status != ClinicStatus.APPROVED:
            return Response(
                {
                    "success": False,
                    "message": f"Only APPROVED clinics can be suspended (current status: '{clinic.status}').",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClinicAdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        clinic.status = ClinicStatus.SUSPENDED
        clinic.verification_notes = reason
        clinic.is_verified = False
        clinic.save(update_fields=["status", "verification_notes", "is_verified", "updated_at"])

        log_audit_event(
            action="CLINIC_SUSPENDED",
            resource_type="Clinic",
            resource_id=str(clinic.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"reason": reason},
        )

        return Response(
            {
                "success": True,
                "message": f"Clinic '{clinic.name}' has been suspended.",
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminClinicReactivateView(APIView):
    """
    Super Admin reactivation endpoint.
    Transitions status: SUSPENDED -> APPROVED.
    """

    permission_classes = [IsSuperAdminOnly]

    @extend_schema(
        summary="Admin Reactivate Clinic",
        description="Reactivates a SUSPENDED clinic back to APPROVED status.",
        responses={
            200: ClinicSerializer,
            400: OpenApiResponse(description="Invalid transition."),
        },
    )
    def post(self, request, pk):
        clinic = get_object_or_404(Clinic, pk=pk)

        if clinic.status != ClinicStatus.SUSPENDED:
            return Response(
                {
                    "success": False,
                    "message": f"Only SUSPENDED clinics can be reactivated (current status: '{clinic.status}').",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        clinic.status = ClinicStatus.APPROVED
        clinic.is_verified = True
        clinic.save(update_fields=["status", "is_verified", "updated_at"])

        log_audit_event(
            action="CLINIC_REACTIVATED",
            resource_type="Clinic",
            resource_id=str(clinic.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={"reactivated_by": str(request.user.id)},
        )

        return Response(
            {
                "success": True,
                "message": f"Clinic '{clinic.name}' has been successfully reactivated.",
                "data": ClinicSerializer(clinic, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
