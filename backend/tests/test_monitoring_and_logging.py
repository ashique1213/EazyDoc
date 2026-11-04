import json
import logging
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from config.logging import (
    redact_sensitive_data,
    StructuredJSONFormatter,
    get_current_request_id,
    set_current_request_id,
    clear_current_request_id,
)
from config.middleware import RequestIDMiddleware


class RequestIDMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RequestIDMiddleware(lambda req: req)

    def tearDown(self):
        clear_current_request_id()

    def test_request_id_auto_generated_when_missing(self):
        """Middleware should generate a unique req_<uuid> if no header is supplied."""
        request = self.factory.get("/api/v1/health/live/")
        response = MagicMock()

        def get_response(req):
            # Verify request ID was attached to request and contextvar
            self.assertTrue(hasattr(req, "request_id"))
            self.assertTrue(req.request_id.startswith("req_"))
            self.assertEqual(get_current_request_id(), req.request_id)
            return response

        middleware = RequestIDMiddleware(get_response)
        res = middleware(request)

        # Verify header is injected into response
        response.__setitem__.assert_called_with("X-Request-ID", request.request_id)
        # Context should be cleared after response
        self.assertIsNone(get_current_request_id())

    def test_request_id_honors_valid_client_header(self):
        """Middleware should preserve a valid incoming X-Request-ID header."""
        valid_id = "req_custom_upstream_trace_12345"
        request = self.factory.get(
            "/api/v1/health/live/",
            HTTP_X_REQUEST_ID=valid_id,
        )
        response = MagicMock()

        def get_response(req):
            self.assertEqual(req.request_id, valid_id)
            self.assertEqual(get_current_request_id(), valid_id)
            return response

        middleware = RequestIDMiddleware(get_response)
        res = middleware(request)
        response.__setitem__.assert_called_with("X-Request-ID", valid_id)

    def test_request_id_rejects_and_replaces_malformed_header(self):
        """Middleware should sanitize/replace dangerous or malformed client IDs."""
        malformed_id = "bad id with spaces <script>alert(1)</script>"
        request = self.factory.get(
            "/api/v1/health/live/",
            HTTP_X_REQUEST_ID=malformed_id,
        )
        response = MagicMock()

        def get_response(req):
            self.assertNotEqual(req.request_id, malformed_id)
            self.assertTrue(req.request_id.startswith("req_"))
            return response

        middleware = RequestIDMiddleware(get_response)
        middleware(request)


class LoggingAndRedactionTests(TestCase):
    def test_redact_sensitive_keys(self):
        """Sensitive dictionary keys must be redacted recursively."""
        payload = {
            "username": "doctor@eazydoc.com",
            "password": "SuperSecretPassword123!",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "nested": {
                "client_secret": "rzp_secret_998877",
                "normal_field": "public_data",
                "cvv": "123",
                "authorization": "Bearer secret_jwt",
            },
            "list_data": [
                {"token": "xyz123", "name": "Item 1"},
                "plain_string",
            ],
        }

        redacted = redact_sensitive_data(payload)
        self.assertEqual(redacted["username"], "doctor@eazydoc.com")
        self.assertEqual(redacted["password"], "[REDACTED]")
        self.assertEqual(redacted["access_token"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["client_secret"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["cvv"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["authorization"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["normal_field"], "public_data")
        self.assertEqual(redacted["list_data"][0]["token"], "[REDACTED]")
        self.assertEqual(redacted["list_data"][0]["name"], "Item 1")

    def test_structured_json_formatter_output(self):
        """StructuredJSONFormatter produces valid JSON with required observability fields."""
        formatter = StructuredJSONFormatter(app_name="eazydoc-test")
        set_current_request_id("req_formatter_test_8888")

        try:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.WARNING,
                pathname="/app/backend/test.py",
                lineno=42,
                msg="Test message with extra",
                args=(),
                exc_info=None,
            )
            record.extra = {"sensitive_token": "secret123", "tenant_id": "clinic-42"}

            formatted_str = formatter.format(record)
            log_data = json.loads(formatted_str)

            self.assertEqual(log_data["level"], "WARNING")
            self.assertEqual(log_data["app"], "eazydoc-test")
            self.assertEqual(log_data["request_id"], "req_formatter_test_8888")
            self.assertEqual(log_data["logger"], "test_logger")
            self.assertEqual(log_data["message"], "Test message with extra")
            self.assertEqual(log_data["line"], 42)
            self.assertEqual(log_data["extra"]["sensitive_token"], "[REDACTED]")
            self.assertEqual(log_data["extra"]["tenant_id"], "clinic-42")
            self.assertIn("timestamp", log_data)
        finally:
            clear_current_request_id()


class HealthCheckEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_liveness_probe_returns_200(self):
        """GET /api/v1/health/live/ should return 200 OK immediately without DB overhead."""
        res_api = self.client.get("/api/v1/health/live/")
        self.assertEqual(res_api.status_code, status.HTTP_200_OK)
        self.assertEqual(res_api.data["status"], "ok")
        self.assertEqual(res_api.data["service"], "eazydoc-api")

        res_root = self.client.get("/health/live/")
        self.assertEqual(res_root.status_code, status.HTTP_200_OK)
        self.assertEqual(res_root.data["status"], "ok")

    def test_readiness_probe_success(self):
        """GET /api/v1/health/ready/ should return 200 OK when services are responsive."""
        with patch("django.db.connection.cursor") as mock_cursor, \
             patch("redis.from_url") as mock_redis:
            mock_cursor.return_value.__enter__.return_value.execute.return_value = None
            mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            mock_redis.return_value.ping.return_value = True

            res = self.client.get("/api/v1/health/ready/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["status"], "ok")
            self.assertEqual(res.data["database"], "ok")
            self.assertEqual(res.data["redis"], "ok")

    def test_readiness_probe_returns_503_on_database_failure(self):
        """GET /api/v1/health/ready/ should return 503 SERVICE UNAVAILABLE on DB failure."""
        with patch("django.db.connection.cursor", side_effect=Exception("DB connection refused")):
            res = self.client.get("/api/v1/health/ready/")
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(res.data["status"], "unavailable")
            self.assertEqual(res.data["database"], "unavailable")


class OperationalMetricsEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superadmin = User.objects.create_superuser(
            email="opsadmin@eazydoc.com",
            password="OpsPassword123!",
            first_name="Ops",
            last_name="SuperAdmin",
        )
        self.clinic_owner = User.objects.create_user(
            email="owner@eazydoc.com",
            password="OwnerPassword123!",
            first_name="Clinic",
            last_name="Owner",
            role=UserRole.CLINIC_OWNER,
        )
        self.patient = User.objects.create_user(
            email="patient@eazydoc.com",
            password="PatientPassword123!",
            first_name="John",
            last_name="Patient",
            role=UserRole.PATIENT,
        )
        self.url = reverse("api-v1:admin-dashboard:operations-monitoring")

    def test_unauthenticated_access_denied(self):
        """Anonymous requests must receive 401 Unauthorized."""
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_superadmin_access_forbidden(self):
        """Clinic owners and patients must receive 403 Forbidden."""
        self.client.force_authenticate(user=self.clinic_owner)
        res_owner = self.client.get(self.url)
        self.assertEqual(res_owner.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.patient)
        res_patient = self.client.get(self.url)
        self.assertEqual(res_patient.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_can_access_operational_metrics(self):
        """Super Admin receives comprehensive operational metrics."""
        self.client.force_authenticate(user=self.superadmin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data["data"]
        self.assertIn("system_health", data)
        self.assertIn("database", data["system_health"])
        self.assertIn("redis", data["system_health"])
        self.assertIn("celery", data["system_health"])
        self.assertIn("business_operations_24h", data)
        self.assertIn("backup_status", data)
        self.assertIn("active_warnings", data)
        self.assertIsInstance(data["active_warnings"], list)
