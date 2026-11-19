import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.clinics.models import Clinic
from apps.subscriptions.models import (
    ClinicSubscription,
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionPlan,
    SubscriptionStatus,
)
from apps.subscriptions.serializers import (
    AdminSubscriptionOverrideSerializer,
    ClinicSubscriptionSerializer,
    SubscriptionEventSerializer,
    SubscriptionPlanAdminSerializer,
)
from apps.subscriptions.services.analytics import SubscriptionAnalyticsService
from apps.subscriptions.services.lifecycle import SubscriptionLifecycleService

logger = logging.getLogger("apps.subscriptions")


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.SUPER_ADMIN)


class AdminSubscriptionDashboardView(APIView):
    """
    Super Admin SaaS Metrics: MRR, ARR, churn rate, plan distribution, and active counts.
    """
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Super Admin SaaS Metrics",
        description="Returns platform-level SaaS KPIs including MRR, ARR, churn rate, and active clinic counts.",
    )
    def get(self, request):
        metrics = SubscriptionAnalyticsService.get_subscription_metrics()
        return Response({"success": True, "data": metrics}, status=status.HTTP_200_OK)


class AdminSubscriptionPlansListCreateView(APIView):
    """
    Super Admin endpoint to list all plans (including hidden/inactive) and create new plans.
    """
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="List All SaaS Plans (Admin)",
        description="Returns all plans including active and inactive configurations.",
        responses={200: SubscriptionPlanAdminSerializer(many=True)},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.all().order_by("sort_order", "price")
        serializer = SubscriptionPlanAdminSerializer(plans, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create SaaS Plan",
        description="Creates a new subscription plan with custom quotas and pricing.",
        request=SubscriptionPlanAdminSerializer,
        responses={201: SubscriptionPlanAdminSerializer},
    )
    def post(self, request):
        serializer = SubscriptionPlanAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Plan created successfully.",
                "data": SubscriptionPlanAdminSerializer(plan).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminSubscriptionPlanDetailView(APIView):
    """
    Super Admin endpoint to retrieve, update, or deactivate a specific subscription plan.
    """
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Retrieve Plan (Admin)",
        responses={200: SubscriptionPlanAdminSerializer},
    )
    def get(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        return Response({"success": True, "data": SubscriptionPlanAdminSerializer(plan).data})

    @extend_schema(
        summary="Update Plan (Admin)",
        request=SubscriptionPlanAdminSerializer,
        responses={200: SubscriptionPlanAdminSerializer},
    )
    def patch(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        serializer = SubscriptionPlanAdminSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Plan updated successfully.",
                "data": SubscriptionPlanAdminSerializer(updated).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminClinicSubscriptionsListView(APIView):
    """
    Super Admin endpoint to list all clinic subscriptions with filtering.
    """
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="List All Clinic Subscriptions (Admin)",
        description="Returns clinic subscriptions across all facilities with status and plan filters.",
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        tier_filter = request.query_params.get("tier")
        search = request.query_params.get("search")

        qs = ClinicSubscription.objects.select_related("clinic", "plan").order_by("-created_at")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if tier_filter:
            qs = qs.filter(plan__tier=tier_filter)
        if search:
            qs = qs.filter(clinic__name__icontains=search)

        serializer = ClinicSubscriptionSerializer(qs[:100], many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class AdminClinicSubscriptionOverrideView(APIView):
    """
    Super Admin endpoint for manual administrative overrides:
    - Change status (ACTIVE, SUSPENDED, EXPIRED)
    - Comp/assign a specific plan
    - Set custom doctor/staff limit overrides
    - Extend subscription duration
    """
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Override Clinic Subscription (Admin)",
        description="Allows Super Admin to suspend, reinstate, comp, or override quotas for a clinic.",
        request=AdminSubscriptionOverrideSerializer,
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        subscription = (
            ClinicSubscription.objects.filter(clinic=clinic)
            .select_related("plan")
            .first()
        )
        if not subscription:
            subscription = SubscriptionLifecycleService.initialize_clinic_subscription(clinic)

        serializer = AdminSubscriptionOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_status = serializer.validated_data.get("status")
        plan_id = serializer.validated_data.get("plan_id")
        custom_docs = serializer.validated_data.get("custom_doctor_limit")
        custom_staff = serializer.validated_data.get("custom_staff_limit")
        extend_days = serializer.validated_data.get("extend_days")
        reason = serializer.validated_data["reason"]

        old_status = subscription.status
        old_plan_name = subscription.plan.name

        if plan_id:
            new_plan = get_object_or_404(SubscriptionPlan, id=plan_id)
            subscription.plan = new_plan

        if target_status:
            if target_status == SubscriptionStatus.SUSPENDED:
                subscription.status = SubscriptionStatus.SUSPENDED
            elif target_status == SubscriptionStatus.ACTIVE:
                subscription.status = SubscriptionStatus.ACTIVE
            elif target_status == SubscriptionStatus.EXPIRED:
                subscription.status = SubscriptionStatus.EXPIRED

        if custom_docs is not None:
            subscription.custom_doctor_limit = custom_docs
        if custom_staff is not None:
            subscription.custom_staff_limit = custom_staff

        if extend_days:
            now = timezone.now()
            base = subscription.current_period_end if subscription.current_period_end and subscription.current_period_end > now else now
            subscription.current_period_end = base + timedelta(days=extend_days)
            subscription.status = SubscriptionStatus.ACTIVE

        subscription.save()

        SubscriptionEvent.objects.create(
            subscription=subscription,
            clinic=clinic,
            event_type=SubscriptionEventType.LIMIT_OVERRIDE,
            old_status=old_status,
            new_status=subscription.status,
            old_plan_name=old_plan_name,
            new_plan_name=subscription.plan.name,
            reason=f"Admin Override: {reason}",
            triggered_by=request.user,
            metadata={
                "custom_doctor_limit": subscription.custom_doctor_limit,
                "custom_staff_limit": subscription.custom_staff_limit,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Subscription updated successfully by administrator.",
                "data": ClinicSubscriptionSerializer(subscription).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminSubscriptionAuditEventsView(APIView):
    """
    Super Admin endpoint to inspect recent platform-wide subscription audit events.
    """
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="List Subscription Audit Events",
        description="Returns stream of recent subscription lifecycle events across all clinics.",
    )
    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        events = SubscriptionAnalyticsService.get_recent_subscription_events(limit=limit)
        return Response({"success": True, "data": events}, status=status.HTTP_200_OK)
