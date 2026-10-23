from django.urls import path
from .admin_views import AdminCommissionListView

app_name = "admin-commissions"

urlpatterns = [
    path("", AdminCommissionListView.as_view(), name="commission-list"),
]
