from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin
from apps.audit_logs.services import log_audit_event
from .admin_serializers import AdminUserActionSerializer, AdminUserSerializer
from .models import User, UserRole, UserStatus


class AdminUserPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminUserListView(APIView):
    """
    Super Admin endpoint for platform-wide user account management.
    Allows filtering by role, account status, active flag, and keyword search.
    """

    permission_classes = [IsSuperAdmin]
    pagination_class = AdminUserPagination

    @extend_schema(
        summary="Admin List Users",
        description="Lists all user accounts across platform with filtering and search.",
        responses={200: AdminUserSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            User.objects.all()
            .select_related("doctor_profile")
            .prefetch_related("owned_clinics")
            .order_by("-created_at")
        )

        role_filter = request.query_params.get("role")
        if role_filter and role_filter.upper() != "ALL":
            queryset = queryset.filter(role=role_filter.upper())

        status_filter = request.query_params.get("status")
        if status_filter and status_filter.upper() != "ALL":
            queryset = queryset.filter(status=status_filter.upper())

        is_active_filter = request.query_params.get("is_active")
        if is_active_filter is not None:
            if is_active_filter.lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif is_active_filter.lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        search = request.query_params.get("search")
        if search:
            q = search.strip()
            queryset = queryset.filter(
                Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminUserSerializer(paginated_qs, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class AdminUserDetailView(APIView):
    """
    Super Admin endpoint to inspect full sanitized details of a user account.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Get User Details",
        description="Retrieve full sanitized account details for a user.",
        responses={200: AdminUserSerializer, 404: OpenApiResponse(description="Not Found.")},
    )
    def get(self, request, pk):
        user = get_object_or_404(
            User.objects.select_related("doctor_profile").prefetch_related("owned_clinics"),
            pk=pk,
        )
        return Response(
            {
                "success": True,
                "data": AdminUserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserActivateView(APIView):
    """
    Super Admin endpoint to activate an account.
    Transitions status to ACTIVE and is_active to True.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Activate User",
        description="Activates an existing user account.",
        responses={200: AdminUserSerializer},
    )
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.save(update_fields=["status", "is_active", "updated_at"])

        log_audit_event(
            action="USER_ACTIVATED",
            resource_type="USER",
            resource_id=str(user.id),
            actor=request.user,
            request=request,
            details={"email": user.email, "role": user.role},
        )

        return Response(
            {
                "success": True,
                "message": f"Account for '{user.email}' has been activated.",
                "data": AdminUserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserDeactivateView(APIView):
    """
    Super Admin endpoint to deactivate an account.
    Guards against self-lockout.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Deactivate User",
        description="Deactivates an existing user account. Admin cannot deactivate their own account.",
        responses={200: AdminUserSerializer, 400: OpenApiResponse(description="Self-lockout prevented.")},
    )
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if user.id == request.user.id:
            return Response(
                {
                    "success": False,
                    "message": "You cannot deactivate your own administrative account.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.status = UserStatus.INACTIVE
        user.is_active = False
        user.save(update_fields=["status", "is_active", "updated_at"])

        log_audit_event(
            action="USER_DEACTIVATED",
            resource_type="USER",
            resource_id=str(user.id),
            actor=request.user,
            request=request,
            details={"email": user.email, "role": user.role},
        )

        return Response(
            {
                "success": True,
                "message": f"Account for '{user.email}' has been deactivated.",
                "data": AdminUserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserSuspendView(APIView):
    """
    Super Admin endpoint to suspend an account with a mandatory or recorded reason.
    Guards against self-lockout.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Suspend User",
        description="Suspends a user account. Admin cannot suspend their own account.",
        request=AdminUserActionSerializer,
        responses={200: AdminUserSerializer, 400: OpenApiResponse(description="Validation or self-lockout error.")},
    )
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if user.id == request.user.id:
            return Response(
                {
                    "success": False,
                    "message": "You cannot suspend your own administrative account.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminUserActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "").strip() or "Administrative suspension"

        user.status = UserStatus.SUSPENDED
        user.is_active = False
        user.save(update_fields=["status", "is_active", "updated_at"])

        log_audit_event(
            action="USER_SUSPENDED",
            resource_type="USER",
            resource_id=str(user.id),
            actor=request.user,
            request=request,
            details={"email": user.email, "role": user.role, "reason": reason},
        )

        return Response(
            {
                "success": True,
                "message": f"Account for '{user.email}' has been suspended.",
                "data": AdminUserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
