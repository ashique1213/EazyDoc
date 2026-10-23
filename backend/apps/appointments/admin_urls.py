from django.urls import path
from .admin_views import (
    AdminAppointmentCancelView,
    AdminAppointmentDetailView,
    AdminAppointmentHistoryView,
    AdminAppointmentListView,
)

app_name = "admin-appointments"

urlpatterns = [
    path("", AdminAppointmentListView.as_view(), name="appointment-list"),
    path("<uuid:pk>/", AdminAppointmentDetailView.as_view(), name="appointment-detail"),
    path("<uuid:pk>/history/", AdminAppointmentHistoryView.as_view(), name="appointment-history"),
    path("<uuid:pk>/cancel/", AdminAppointmentCancelView.as_view(), name="appointment-cancel"),
]
