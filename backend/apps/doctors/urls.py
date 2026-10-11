from django.urls import path
from .views import (
    DoctorDocumentDeleteView,
    DoctorDocumentDownloadView,
    DoctorDocumentListCreateView,
    DoctorMeView,
    DoctorProfileCreateView,
    DoctorRegistrationLookupView,
    DoctorSubmitVerificationView,
    SpecializationListView,
)

app_name = "doctors"

urlpatterns = [
    # Doctor Profile
    path("profile/", DoctorProfileCreateView.as_view(), name="doctor-profile-create"),
    path("me/", DoctorMeView.as_view(), name="doctor-me"),
    path("me/submit-verification/", DoctorSubmitVerificationView.as_view(), name="doctor-submit-verification"),
    # Documents
    path("me/documents/", DoctorDocumentListCreateView.as_view(), name="doctor-documents"),
    path("me/documents/<uuid:pk>/", DoctorDocumentDeleteView.as_view(), name="doctor-document-delete"),
    path("me/documents/<uuid:pk>/download/", DoctorDocumentDownloadView.as_view(), name="doctor-document-download"),
    # Registration Lookup (for Clinic Owners)
    path("registration-lookup/", DoctorRegistrationLookupView.as_view(), name="doctor-registration-lookup"),
    # Specializations Catalog
    path("specializations/", SpecializationListView.as_view(), name="specializations-list"),
]
