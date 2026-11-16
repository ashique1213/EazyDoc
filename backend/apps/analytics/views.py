from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsSuperAdmin
from apps.clinics.models import Clinic
from apps.clinics.permissions import (
    HasClinicStaffOrOwnerPermission,
    IsSuperAdminOnly,
    check_clinic_access,
)
from .serializers import (
    AnalyticsQuerySerializer,
    ClinicPerformanceQuerySerializer,
    DoctorPerformanceQuerySerializer,
    ExportReportQuerySerializer,
)
from .services.admin_analytics import (
    get_appointment_analytics,
    get_clinic_performance_analytics,
    get_doctor_performance_analytics,
    get_financial_reconciliation,
    get_revenue_analytics,
    get_super_admin_kpis,
)
from .services.cache_utils import generate_cache_key, get_cached_or_compute
from .services.clinic_analytics import (
    get_clinic_appointment_analytics,
    get_clinic_doctor_performance,
    get_clinic_overview_analytics,
    get_clinic_revenue_analytics,
)
from .services.date_range import resolve_date_range
from .services.export_service import export_admin_csv, export_clinic_csv


# -------------------------------------------------------------------
# Super Admin Analytics Endpoints
# -------------------------------------------------------------------

class AdminAnalyticsOverviewView(APIView):
    permission_classes = [IsSuperAdminOnly]

    @extend_schema(summary="Super Admin Analytics Overview", responses={200: dict})
    def get(self, request):
        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
        )

        clinic_id = str(data.get("clinic_id")) if data.get("clinic_id") else None
        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        status_filter = data.get("status")
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "overview",
            "admin",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "clinic": clinic_id,
                "doctor": doctor_id,
                "status": status_filter,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_super_admin_kpis(bounds, clinic_id, doctor_id, status_filter),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class AdminAnalyticsRevenueView(APIView):
    permission_classes = [IsSuperAdminOnly]

    @extend_schema(summary="Super Admin Revenue Analytics", responses={200: dict})
    def get(self, request):
        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
        )

        clinic_id = str(data.get("clinic_id")) if data.get("clinic_id") else None
        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "revenue",
            "admin",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "clinic": clinic_id,
                "doctor": doctor_id,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_revenue_analytics(bounds, clinic_id, doctor_id),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class AdminAnalyticsAppointmentsView(APIView):
    permission_classes = [IsSuperAdminOnly]

    @extend_schema(summary="Super Admin Appointment Analytics", responses={200: dict})
    def get(self, request):
        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
        )

        clinic_id = str(data.get("clinic_id")) if data.get("clinic_id") else None
        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "appointments",
            "admin",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "clinic": clinic_id,
                "doctor": doctor_id,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_appointment_analytics(bounds, clinic_id, doctor_id),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class AdminAnalyticsClinicsView(APIView):
    permission_classes = [IsSuperAdminOnly]

    @extend_schema(summary="Super Admin Clinics Performance", responses={200: list})
    def get(self, request):
        ser = ClinicPerformanceQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
        )

        status_filter = data.get("status")
        search = data.get("search")
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "clinics",
            "admin",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "status": status_filter,
                "search": search,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_clinic_performance_analytics(bounds, status_filter, search),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class AdminAnalyticsDoctorsView(APIView):
    permission_classes = [IsSuperAdminOnly]

    @extend_schema(summary="Super Admin Doctors Performance", responses={200: list})
    def get(self, request):
        ser = DoctorPerformanceQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
        )

        clinic_id = str(data.get("clinic_id")) if data.get("clinic_id") else None
        ver_status = data.get("verification_status")
        search = data.get("search")
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "doctors",
            "admin",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "clinic": clinic_id,
                "ver_status": ver_status,
                "search": search,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_doctor_performance_analytics(bounds, clinic_id, ver_status, search),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class AdminAnalyticsReconciliationView(APIView):
    permission_classes = [IsSuperAdminOnly]

    @extend_schema(summary="Super Admin Financial Reconciliation", responses={200: dict})
    def get(self, request):
        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
        )

        clinic_id = str(data.get("clinic_id")) if data.get("clinic_id") else None
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "reconciliation",
            "admin",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "clinic": clinic_id,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_financial_reconciliation(bounds, clinic_id),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class AdminAnalyticsExportView(APIView):
    permission_classes = [IsSuperAdminOnly]

    @extend_schema(summary="Super Admin Reports CSV Export", responses={200: dict})
    def get(self, request):
        ser = ExportReportQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
        )

        clinic_id = str(data.get("clinic_id")) if data.get("clinic_id") else None
        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        report_type = data.get("report_type", "appointments")

        return export_admin_csv(report_type, bounds, clinic_id, doctor_id)


# -------------------------------------------------------------------
# Tenant-Scoped Clinic Analytics Endpoints
# -------------------------------------------------------------------

class BaseClinicAnalyticsView(APIView):
    permission_classes = [HasClinicStaffOrOwnerPermission]

    def get_clinic_and_check_access(self, request, clinic_id) -> Clinic:
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic):
            raise PermissionDenied("You do not have authorization to view this clinic's analytics.")
        return clinic


class ClinicAnalyticsOverviewView(BaseClinicAnalyticsView):
    @extend_schema(summary="Clinic Analytics Overview", responses={200: dict})
    def get(self, request, clinic_id):
        clinic = self.get_clinic_and_check_access(request, clinic_id)

        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
            tz_name=clinic.timezone,
        )

        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "overview",
            f"clinic:{clinic.id}",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "doctor": doctor_id,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_clinic_overview_analytics(clinic, bounds, doctor_id),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class ClinicAnalyticsRevenueView(BaseClinicAnalyticsView):
    @extend_schema(summary="Clinic Revenue Analytics", responses={200: dict})
    def get(self, request, clinic_id):
        clinic = self.get_clinic_and_check_access(request, clinic_id)

        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
            tz_name=clinic.timezone,
        )

        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "revenue",
            f"clinic:{clinic.id}",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "doctor": doctor_id,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_clinic_revenue_analytics(clinic, bounds, doctor_id),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class ClinicAnalyticsAppointmentsView(BaseClinicAnalyticsView):
    @extend_schema(summary="Clinic Appointment Analytics", responses={200: dict})
    def get(self, request, clinic_id):
        clinic = self.get_clinic_and_check_access(request, clinic_id)

        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
            tz_name=clinic.timezone,
        )

        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "appointments",
            f"clinic:{clinic.id}",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
                "doctor": doctor_id,
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_clinic_appointment_analytics(clinic, bounds, doctor_id),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class ClinicAnalyticsDoctorsView(BaseClinicAnalyticsView):
    @extend_schema(summary="Clinic Doctor Performance", responses={200: list})
    def get(self, request, clinic_id):
        clinic = self.get_clinic_and_check_access(request, clinic_id)

        ser = AnalyticsQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
            tz_name=clinic.timezone,
        )

        bypass = data.get("refresh", False)

        cache_key = generate_cache_key(
            "doctors",
            f"clinic:{clinic.id}",
            {
                "period": bounds.period,
                "start": bounds.start_date.isoformat(),
                "end": bounds.end_date.isoformat(),
            },
        )

        result = get_cached_or_compute(
            cache_key,
            lambda: get_clinic_doctor_performance(clinic, bounds),
            bypass_cache=bypass,
        )
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)


class ClinicAnalyticsExportView(BaseClinicAnalyticsView):
    @extend_schema(summary="Clinic Reports CSV Export", responses={200: dict})
    def get(self, request, clinic_id):
        clinic = self.get_clinic_and_check_access(request, clinic_id)

        ser = ExportReportQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        bounds = resolve_date_range(
            period=data.get("period"),
            date_from=str(data.get("date_from")) if data.get("date_from") else None,
            date_to=str(data.get("date_to")) if data.get("date_to") else None,
            tz_name=clinic.timezone,
        )

        doctor_id = str(data.get("doctor_id")) if data.get("doctor_id") else None
        report_type = data.get("report_type", "appointments")

        return export_clinic_csv(clinic, report_type, bounds, doctor_id)

