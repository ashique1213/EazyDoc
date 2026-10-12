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
]
