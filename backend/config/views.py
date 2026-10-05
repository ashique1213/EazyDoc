import logging
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.conf import settings

logger = logging.getLogger("apps")


class HealthCheckView(APIView):
    """Health check endpoint validating core application and backing infrastructure."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Service Health Check",
        description="Returns operational status of the API, Database, and Redis infrastructure.",
        responses={
            200: OpenApiResponse(
                description="All services operational",
            ),
            503: OpenApiResponse(
                description="One or more critical dependencies unavailable",
            ),
        },
        tags=["System"],
    )
    def get(self, request, *args, **kwargs):
        health_data = {
            "status": "ok",
            "database": "ok",
            "redis": "ok",
        }
        overall_healthy = True

        # Check Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_data["database"] = "error"
            health_data["status"] = "degraded"
            overall_healthy = False

        # Check Redis
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
            redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            health_data["redis"] = "unavailable"
            # Redis failure can be non-fatal or marked degraded depending on requirement

        http_status = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_data, status=http_status)
