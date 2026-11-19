from django.urls import path
from apps.subscriptions.admin_views import (
    AdminClinicSubscriptionOverrideView,
    AdminClinicSubscriptionsListView,
    AdminSubscriptionAuditEventsView,
    AdminSubscriptionDashboardView,
    AdminSubscriptionPlanDetailView,
    AdminSubscriptionPlansListCreateView,
)

app_name = "admin-subscriptions"

urlpatterns = [
    path("metrics/", AdminSubscriptionDashboardView.as_view(), name="admin-subscription-metrics"),
    path("plans/", AdminSubscriptionPlansListCreateView.as_view(), name="admin-subscription-plans"),
    path("plans/<uuid:pk>/", AdminSubscriptionPlanDetailView.as_view(), name="admin-subscription-plan-detail"),
    path("clinics/", AdminClinicSubscriptionsListView.as_view(), name="admin-subscription-clinics"),
    path("clinics/<uuid:clinic_id>/override/", AdminClinicSubscriptionOverrideView.as_view(), name="admin-subscription-override"),
    path("events/", AdminSubscriptionAuditEventsView.as_view(), name="admin-subscription-events"),
]
