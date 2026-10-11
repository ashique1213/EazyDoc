from django.urls import path
from .admin_views import (
    AdminClinicApproveView,
    AdminClinicDetailView,
    AdminClinicListView,
    AdminClinicReactivateView,
    AdminClinicRejectView,
    AdminClinicSuspendView,
)

app_name = "admin-clinics"

urlpatterns = [
    path("", AdminClinicListView.as_view(), name="clinic-list"),
    path("<uuid:pk>/", AdminClinicDetailView.as_view(), name="clinic-detail"),
    path("<uuid:pk>/approve/", AdminClinicApproveView.as_view(), name="clinic-approve"),
    path("<uuid:pk>/reject/", AdminClinicRejectView.as_view(), name="clinic-reject"),
    path("<uuid:pk>/suspend/", AdminClinicSuspendView.as_view(), name="clinic-suspend"),
    path("<uuid:pk>/reactivate/", AdminClinicReactivateView.as_view(), name="clinic-reactivate"),
]
