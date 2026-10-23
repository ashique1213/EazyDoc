from django.urls import path
from .admin_views import (
    AdminAppointmentsTrendView,
    AdminDashboardSummaryView,
    AdminFinancialSummaryView,
)

app_name = "admin-dashboard"

urlpatterns = [
    path("summary/", AdminDashboardSummaryView.as_view(), name="dashboard-summary"),
    path("appointments-trend/", AdminAppointmentsTrendView.as_view(), name="appointments-trend"),
    path("financial-summary/", AdminFinancialSummaryView.as_view(), name="financial-summary"),
]
