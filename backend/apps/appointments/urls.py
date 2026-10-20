from django.urls import path
from .views import (
    AppointmentCancelView,
    AppointmentCreateView,
    AppointmentDetailView,
    AppointmentHistoryListView,
    AppointmentRescheduleView,
    PatientAppointmentsListView,
)

app_name = "appointments"

urlpatterns = [
    path("", AppointmentCreateView.as_view(), name="appointment-create"),
    path("my/", PatientAppointmentsListView.as_view(), name="my-appointments"),
    path("<uuid:appointment_id>/", AppointmentDetailView.as_view(), name="appointment-detail"),
    path("<uuid:appointment_id>/cancel/", AppointmentCancelView.as_view(), name="appointment-cancel"),
    path("<uuid:appointment_id>/reschedule/", AppointmentRescheduleView.as_view(), name="appointment-reschedule"),
    path("<uuid:appointment_id>/history/", AppointmentHistoryListView.as_view(), name="appointment-history"),
]

