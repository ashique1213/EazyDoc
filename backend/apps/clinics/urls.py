from django.urls import path
from .views import (
    ClinicDetailView,
    ClinicDoctorInvitationView,
    ClinicDoctorListView,
    ClinicDoctorRemoveView,
    ClinicDoctorSettingsUpdateView,
    ClinicListCreateView,
    ClinicSubmitView,
    MyClinicsListView,
)
from apps.appointments.views import (
    ClinicAppointmentCancelView,
    ClinicAppointmentReportUnavailabilityView,
    ClinicAppointmentRescheduleView,
    ClinicAppointmentsListView,
)

app_name = "clinics"

urlpatterns = [
    path("", ClinicListCreateView.as_view(), name="clinic-list-create"),
    path("my-clinics/", MyClinicsListView.as_view(), name="my-clinics"),
    path("<uuid:pk>/", ClinicDetailView.as_view(), name="clinic-detail"),
    path("<uuid:pk>/submit/", ClinicSubmitView.as_view(), name="clinic-submit"),
    # Doctor Association Endpoints
    path("<uuid:clinic_id>/doctors/", ClinicDoctorListView.as_view(), name="clinic-doctor-list"),
    path("<uuid:clinic_id>/doctor-invitations/", ClinicDoctorInvitationView.as_view(), name="clinic-doctor-invitations"),
    path("<uuid:clinic_id>/doctors/<uuid:association_id>/settings/", ClinicDoctorSettingsUpdateView.as_view(), name="clinic-doctor-settings"),
    path("<uuid:clinic_id>/doctors/<uuid:association_id>/remove/", ClinicDoctorRemoveView.as_view(), name="clinic-doctor-remove"),
    path("<uuid:clinic_id>/appointments/", ClinicAppointmentsListView.as_view(), name="clinic-appointments"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/cancel/", ClinicAppointmentCancelView.as_view(), name="clinic-appointment-cancel"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/reschedule/", ClinicAppointmentRescheduleView.as_view(), name="clinic-appointment-reschedule"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/report-unavailability/", ClinicAppointmentReportUnavailabilityView.as_view(), name="clinic-appointment-report-unavailability"),
]

