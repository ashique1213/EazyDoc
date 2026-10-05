from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole


class HealthCheckTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint(self):
        """Ensure GET /api/v1/health/ returns 200 OK with expected JSON structure."""
        url = reverse("api-v1:health-check")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "ok")
        self.assertIn("database", response.data)
        self.assertEqual(response.data["database"], "ok")


class UserModelTests(TestCase):
    def test_create_user(self):
        """Ensure custom User model can be created with email and role."""
        user = User.objects.create_user(
            email="doctor@eazydoc.com",
            password="StrongPassword123!",
            first_name="Rahul",
            last_name="Sharma",
            role=UserRole.DOCTOR,
        )
        self.assertEqual(user.email, "doctor@eazydoc.com")
        self.assertEqual(user.role, UserRole.DOCTOR)
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_superuser(self):
        """Ensure superuser gets role SUPER_ADMIN and is_staff/is_superuser flags."""
        admin_user = User.objects.create_superuser(
            email="admin@eazydoc.com",
            password="AdminPassword123!",
            first_name="Platform",
            last_name="Admin",
        )
        self.assertEqual(admin_user.role, UserRole.SUPER_ADMIN)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
