from django.urls import path
from .admin_views import AdminAuditLogListView

app_name = "admin-audit-logs"

urlpatterns = [
    path("", AdminAuditLogListView.as_view(), name="audit-log-list"),
]
