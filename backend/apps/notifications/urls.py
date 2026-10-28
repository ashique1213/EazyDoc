from django.urls import path
from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationListView,
    NotificationPreferenceView,
    UnreadCountView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("unread-count/", UnreadCountView.as_view(), name="unread-count"),
    path("<uuid:notification_id>/read/", MarkNotificationReadView.as_view(), name="mark-read"),
    path("read-all/", MarkAllNotificationsReadView.as_view(), name="read-all"),
    path("preferences/", NotificationPreferenceView.as_view(), name="preferences"),
]
