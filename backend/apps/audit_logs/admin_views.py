from django.db.models import Q
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin
from .admin_serializers import AdminAuditLogSerializer
from .models import AuditLog


class AdminAuditLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminAuditLogListView(APIView):
    """
    Super Admin endpoint to inspect the immutable platform audit trail.
    Supports filtering by action, resource type, actor, clinic, date range, and keyword search.
    """

    permission_classes = [IsSuperAdmin]
    pagination_class = AdminAuditLogPagination

    @extend_schema(
        summary="Admin List Audit Logs",
        description="Lists all security, tenant, and administrative audit logs across the platform.",
        responses={200: AdminAuditLogSerializer(many=True)},
    )
    def get(self, request):
        queryset = (
            AuditLog.objects.all()
            .select_related("actor")
            .order_by("-created_at")
        )

        action_param = request.query_params.get("action")
        if action_param and action_param.upper() != "ALL":
            queryset = queryset.filter(action=action_param.upper())

        resource_type = request.query_params.get("resource_type")
        if resource_type and resource_type.upper() != "ALL":
            queryset = queryset.filter(resource_type__iexact=resource_type)

        clinic_id = request.query_params.get("clinic_id")
        if clinic_id:
            queryset = queryset.filter(clinic_id=clinic_id)

        actor_id = request.query_params.get("actor_id")
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)

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

        search = request.query_params.get("search")
        if search:
            q = search.strip()
            queryset = queryset.filter(
                Q(action__icontains=q)
                | Q(resource_type__icontains=q)
                | Q(resource_id__icontains=q)
                | Q(actor__email__icontains=q)
                | Q(actor__first_name__icontains=q)
                | Q(actor__last_name__icontains=q)
            )

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminAuditLogSerializer(paginated_qs, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)
