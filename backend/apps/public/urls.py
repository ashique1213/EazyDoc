from django.urls import path

from .views import (
    PublicCityListView,
    PublicClinicDetailView,
    PublicClinicSearchView,
    PublicDoctorAvailabilityView,
    PublicDoctorDetailView,
    PublicDoctorSearchView,
    PublicSpecializationListView,
)

app_name = "public"

urlpatterns = [
    # Public Doctor Search & Profile
    path("doctors/", PublicDoctorSearchView.as_view(), name="doctor-search"),
    path("doctors/<uuid:doctor_id>/", PublicDoctorDetailView.as_view(), name="doctor-detail"),
    # Public Clinic Search & Profile
    path("clinics/", PublicClinicSearchView.as_view(), name="clinic-search"),
    path("clinics/<str:clinic_id>/", PublicClinicDetailView.as_view(), name="clinic-detail"),
    # Public Availability Slots
    path(
        "clinics/<uuid:clinic_id>/doctors/<uuid:doctor_id>/availability/",
        PublicDoctorAvailabilityView.as_view(),
        name="doctor-availability",
    ),
    # Public Catalogs for Filter Selectors
    path("specializations/", PublicSpecializationListView.as_view(), name="specialization-list"),
    path("cities/", PublicCityListView.as_view(), name="city-list"),
]
