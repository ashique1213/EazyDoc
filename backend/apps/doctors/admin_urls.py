from django.urls import path
from .admin_views import (
    AdminDoctorDetailView,
    AdminDoctorDocumentDownloadView,
    AdminDoctorListView,
    AdminDoctorReactivateView,
    AdminDoctorRejectView,
    AdminDoctorSuspendView,
    AdminDoctorVerifyView,
)

app_name = "admin-doctors"

urlpatterns = [
    path("", AdminDoctorListView.as_view(), name="admin-doctor-list"),
    path("<uuid:pk>/", AdminDoctorDetailView.as_view(), name="admin-doctor-detail"),
    path("<uuid:pk>/verify/", AdminDoctorVerifyView.as_view(), name="admin-doctor-verify"),
    path("<uuid:pk>/reject/", AdminDoctorRejectView.as_view(), name="admin-doctor-reject"),
    path("<uuid:pk>/suspend/", AdminDoctorSuspendView.as_view(), name="admin-doctor-suspend"),
    path("<uuid:pk>/reactivate/", AdminDoctorReactivateView.as_view(), name="admin-doctor-reactivate"),
    path(
        "<uuid:pk>/documents/<uuid:doc_id>/download/",
        AdminDoctorDocumentDownloadView.as_view(),
        name="admin-doctor-document-download",
    ),
]
