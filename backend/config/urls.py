from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from .views import HealthCheckView

api_v1_patterns = [
    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),
    # Domain module routing foundations
    path("auth/", include("apps.accounts.urls", namespace="accounts")),
    path("clinics/", include("apps.clinics.urls", namespace="clinics")),
    path("admin/clinics/", include("apps.clinics.admin_urls", namespace="admin-clinics")),
    path("admin/doctors/", include("apps.doctors.admin_urls", namespace="admin-doctors")),
    path("admin/dashboard/", include("apps.analytics.admin_urls", namespace="admin-dashboard")),
    path("admin/users/", include("apps.accounts.admin_urls", namespace="admin-users")),
    path("admin/appointments/", include("apps.appointments.admin_urls", namespace="admin-appointments")),
    path("admin/payments/", include("apps.payments.admin_payment_urls", namespace="admin-payments")),
    path("admin/commissions/", include("apps.payments.admin_commission_urls", namespace="admin-commissions")),
    path("admin/settings/commission/", include("apps.payments.admin_setting_urls", namespace="admin-commission-settings")),
    path("admin/audit-logs/", include("apps.audit_logs.admin_urls", namespace="admin-audit-logs")),
    path("doctors/", include("apps.doctors.urls", namespace="doctors")),
    path("patients/", include("apps.patients.urls", namespace="patients")),
    path("schedules/", include("apps.schedules.urls", namespace="schedules")),
    path("appointments/", include("apps.appointments.urls", namespace="appointments")),
    path("consultations/", include("apps.consultations.urls", namespace="consultations")),
    path("prescriptions/", include("apps.prescriptions.urls", namespace="prescriptions")),
    path("payments/", include("apps.payments.urls", namespace="payments")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("documents/", include("apps.documents.urls", namespace="documents")),
    path("reviews/", include("apps.reviews.urls", namespace="reviews")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("audit/", include("apps.audit_logs.urls", namespace="audit_logs")),
    path("public/", include("apps.public.urls", namespace="public")),
]

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # OpenAPI Schema & Interactive Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Versioned API
    path("api/v1/", include((api_v1_patterns, "api-v1"))),
]
