from django.urls import path
from .views import (
    DoctorAcceptInvitationView,
    DoctorDocumentDeleteView,
    DoctorDocumentDownloadView,
    DoctorDocumentListCreateView,
    DoctorMeView,
    DoctorMyClinicInvitationsListView,
    DoctorMyClinicsListView,
    DoctorProfileCreateView,
    DoctorRegistrationLookupView,
    DoctorRejectInvitationView,
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
    # Doctor Clinic Association Endpoints
    path("me/clinics/", DoctorMyClinicsListView.as_view(), name="doctor-my-clinics"),
    path("me/clinic-invitations/", DoctorMyClinicInvitationsListView.as_view(), name="doctor-my-clinic-invitations"),
    path("me/clinic-invitations/<uuid:association_id>/accept/", DoctorAcceptInvitationView.as_view(), name="doctor-accept-invitation"),
    path("me/clinic-invitations/<uuid:association_id>/reject/", DoctorRejectInvitationView.as_view(), name="doctor-reject-invitation"),
    # Registration Lookup (for Clinic Owners)
    path("registration-lookup/", DoctorRegistrationLookupView.as_view(), name="doctor-registration-lookup"),
    # Specializations Catalog
    path("specializations/", SpecializationListView.as_view(), name="specializations-list"),
]
