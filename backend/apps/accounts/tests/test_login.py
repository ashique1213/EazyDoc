from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User, UserRole, UserStatus


class LoginTests(APITestCase):
    def setUp(self):
        self.login_url = reverse("api-v1:accounts:login")
        self.password = "ValidPassword123!"
        self.active_user = User.objects.create_user(
            email="activeuser@example.com",
            password=self.password,
            first_name="Active",
            last_name="User",
            role=UserRole.PATIENT,
            is_active=True,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

    def test_valid_login(self):
        payload = {"email": "activeuser@example.com", "password": self.password}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("user", response.data["data"])
        self.assertIn("tokens", response.data["data"])
        self.assertIn("access", response.data["data"]["tokens"])

        # Check HttpOnly cookies are set
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_invalid_password(self):
        payload = {"email": "activeuser@example.com", "password": "WrongPassword!"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Validation failed.")

    def test_unknown_email(self):
        payload = {"email": "nonexistent@example.com", "password": self.password}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_suspended_account_cannot_login(self):
        suspended_user = User.objects.create_user(
            email="suspended@example.com",
            password=self.password,
            status=UserStatus.SUSPENDED,
            is_active=True,
        )
        payload = {"email": "suspended@example.com", "password": self.password}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("suspended", str(response.data))

    def test_inactive_account_cannot_login(self):
        inactive_user = User.objects.create_user(
            email="inactive@example.com",
            password=self.password,
            status=UserStatus.INACTIVE,
            is_active=False,
        )
        payload = {"email": "inactive@example.com", "password": self.password}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("inactive", str(response.data))
