from django.urls import path
from .views import (
    AppointmentCreateView,
    AppointmentDetailView,
    PatientAppointmentsListView,
)

app_name = "appointments"

urlpatterns = [
    path("", AppointmentCreateView.as_view(), name="appointment-create"),
    path("my/", PatientAppointmentsListView.as_view(), name="my-appointments"),
    path("<uuid:appointment_id>/", AppointmentDetailView.as_view(), name="appointment-detail"),
]
