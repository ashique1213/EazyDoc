from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Notification, NotificationPreference
from .serializers import (
    MarkAllReadResponseSerializer,
    MarkReadResponseSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
    UnreadCountResponseSerializer,
)


class NotificationListView(generics.ListAPIView):
    """
    List the authenticated user's notifications with pagination and optional unread filtering.
    Strictly tenant-scoped to the authenticated recipient.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List User Notifications",
        description="Returns a paginated list of notifications belonging exclusively to the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="unread",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter for unread notifications only (true/false).",
            ),
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        unread_filter = self.request.query_params.get("unread")
        if unread_filter is not None and unread_filter.lower() in ("true", "1"):
            qs = qs.filter(is_read=False)
        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Include current total unread count in response headers/data for convenience
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        if isinstance(response.data, dict) and "results" in response.data:
            response.data["unread_count"] = unread_count
        return response


class UnreadCountView(APIView):
    """Returns the total number of unread notifications for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Unread Notification Count",
        description="Returns the current unread notifications count for the authenticated recipient.",
        responses={200: UnreadCountResponseSerializer},
    )
    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count}, status=status.HTTP_200_OK)


class MarkNotificationReadView(APIView):
    """Marks a single notification as read, ensuring strict ownership validation."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark Notification as Read",
        description="Marks a specific notification as read. Enforces recipient-level authorization.",
        responses={
            200: MarkReadResponseSerializer,
            404: OpenApiResponse(description="Notification not found or access denied."),
        },
    )
    def post(self, request, notification_id):
        # Enforce recipient scoping: return 404 if notification belongs to another user
        notification = Notification.objects.filter(
            id=notification_id,
            recipient=request.user,
        ).first()

        if not notification:
            return Response(
                {"success": False, "message": "Notification not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.mark_as_read()
        return Response(
            {
                "success": True,
                "message": "Notification marked as read.",
                "notification": NotificationSerializer(notification).data,
            },
            status=status.HTTP_200_OK,
        )


class MarkAllNotificationsReadView(APIView):
    """Marks all unread notifications belonging to the authenticated user as read."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark All Notifications as Read",
        description="Marks all unread notifications of the authenticated user as read in a single batch.",
        responses={200: MarkAllReadResponseSerializer},
    )
    def post(self, request):
        now = timezone.now()
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=now)

        return Response(
            {
                "success": True,
                "message": f"Marked {updated_count} notification(s) as read.",
                "marked_read_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )


class NotificationPreferenceView(APIView):
    """View and update authenticated user's notification preferences."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Notification Preferences",
        description="Retrieves the current channel and category preferences for the authenticated user.",
        responses={200: NotificationPreferenceSerializer},
    )
    def get(self, request):
        prefs = NotificationPreference.get_for_user(request.user)
        return Response(NotificationPreferenceSerializer(prefs).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update Notification Preferences",
        description="Updates channel and category notification preferences for the authenticated user.",
        request=NotificationPreferenceSerializer,
        responses={
            200: NotificationPreferenceSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
    )
    def patch(self, request):
        prefs = NotificationPreference.get_for_user(request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
