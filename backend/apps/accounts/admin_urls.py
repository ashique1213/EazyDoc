from django.urls import path
from .admin_views import (
    AdminUserActivateView,
    AdminUserDeactivateView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserSuspendView,
)

app_name = "admin-users"

urlpatterns = [
    path("", AdminUserListView.as_view(), name="user-list"),
    path("<uuid:pk>/", AdminUserDetailView.as_view(), name="user-detail"),
    path("<uuid:pk>/activate/", AdminUserActivateView.as_view(), name="user-activate"),
    path("<uuid:pk>/deactivate/", AdminUserDeactivateView.as_view(), name="user-deactivate"),
    path("<uuid:pk>/suspend/", AdminUserSuspendView.as_view(), name="user-suspend"),
]
