from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import PasswordResetToken, User


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="resetme@example.com",
            password="OldPassword123!",
            first_name="Reset",
            last_name="Tester",
        )
        self.forgot_url = reverse("api-v1:accounts:forgot-password")
        self.reset_url = reverse("api-v1:accounts:reset-password")

    def test_forgot_password_valid_request(self):
        response = self.client.post(
            self.forgot_url, {"email": "resetme@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Token created
        token = PasswordResetToken.objects.filter(user=self.user, is_used=False).first()
        self.assertIsNotNone(token)
        self.assertTrue(token.is_valid())

    def test_forgot_password_unknown_email_does_not_reveal_existence(self):
        response = self.client.post(
            self.forgot_url, {"email": "nosuchuser@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("If an account exists", response.data["message"])

    def test_reset_password_valid_flow(self):
        # Create token
        token = PasswordResetToken.objects.create(
            user=self.user,
            token="valid-secure-token-1234567890",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        response = self.client.post(
            self.reset_url,
            {
                "token": "valid-secure-token-1234567890",
                "password": "NewStrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Verify password changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword123!"))

        # Verify token marked as used
        token.refresh_from_db()
        self.assertTrue(token.is_used)

    def test_reset_password_expired_token(self):
        token = PasswordResetToken.objects.create(
            user=self.user,
            token="expired-token-1234567890",
            expires_at=timezone.now() - timedelta(minutes=5),  # in past
        )

        response = self.client.post(
            self.reset_url,
            {
                "token": "expired-token-1234567890",
                "password": "NewStrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("expired", str(response.data))

    def test_reset_password_already_used_token(self):
        token = PasswordResetToken.objects.create(
            user=self.user,
            token="used-token-1234567890",
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True,
        )

        response = self.client.post(
            self.reset_url,
            {
                "token": "used-token-1234567890",
                "password": "NewStrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_reset_password_invalid_token(self):
        response = self.client.post(
            self.reset_url,
            {
                "token": "completely-bogus-token",
                "password": "NewStrongPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
