from django.urls import path
from .admin_views import (
    AdminAppointmentsTrendView,
    AdminDashboardSummaryView,
    AdminFinancialSummaryView,
    AdminSystemOperationsMonitoringView,
)

app_name = "admin-dashboard"

urlpatterns = [
    path("summary/", AdminDashboardSummaryView.as_view(), name="dashboard-summary"),
    path("appointments-trend/", AdminAppointmentsTrendView.as_view(), name="appointments-trend"),
    path("financial-summary/", AdminFinancialSummaryView.as_view(), name="financial-summary"),
    path("operations/", AdminSystemOperationsMonitoringView.as_view(), name="operations-monitoring"),
]
