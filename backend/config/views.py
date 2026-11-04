import logging
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.conf import settings

logger = logging.getLogger("apps")


class LivenessHealthCheckView(APIView):
    """
    Lightweight liveness probe confirming Django web process is alive.
    Performs zero database or cache queries to prevent restart loops.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Liveness Probe",
        description="Confirms that the web application process is running and responsive. Does not perform backing store queries.",
        responses={
            200: OpenApiResponse(description="Process is alive"),
        },
        tags=["System"],
    )
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": "ok",
                "service": "eazydoc-api",
            },
            status=status.HTTP_200_OK,
        )


class ReadinessHealthCheckView(APIView):
    """
    Readiness probe verifying that backing PostgreSQL and Redis dependencies are reachable
    before orchestrators route live user traffic to this container instance.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Readiness Probe",
        description="Validates connectivity to PostgreSQL database and Redis broker. Returns 503 if database is unreachable.",
        responses={
            200: OpenApiResponse(description="All dependencies ready to serve traffic"),
            503: OpenApiResponse(description="Critical dependencies not ready"),
        },
        tags=["System"],
    )
    def get(self, request, *args, **kwargs):
        health_data = {
            "status": "ok",
            "database": "ok",
            "redis": "ok",
        }
        is_ready = True

        # Database Check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        except Exception as e:
            logger.error(f"Readiness check failed on database: {e}")
            health_data["database"] = "unavailable"
            health_data["status"] = "unavailable"
            is_ready = False

        # Redis Check
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
            redis_client.ping()
        except Exception as e:
            logger.warning(f"Readiness check failed on redis: {e}")
            health_data["redis"] = "unavailable"
            health_data["status"] = "degraded" if is_ready else "unavailable"

        http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_data, status=http_status)


class HealthCheckView(APIView):
    """Comprehensive health check endpoint validating core application and backing infrastructure."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Service Health Check",
        description="Returns operational status of the API, Database, and Redis infrastructure.",
        responses={
            200: OpenApiResponse(description="All services operational"),
            503: OpenApiResponse(description="One or more critical dependencies unavailable"),
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

        http_status = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_data, status=http_status)
