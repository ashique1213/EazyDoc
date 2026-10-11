from django.urls import path
from .views import (
    ClinicDetailView,
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
]
