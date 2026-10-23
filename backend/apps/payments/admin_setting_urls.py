from django.urls import path
from .admin_views import AdminCommissionSettingsView

app_name = "admin-commission-settings"

urlpatterns = [
    path("", AdminCommissionSettingsView.as_view(), name="commission-settings"),
]
