from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import EmailVerificationToken, User


class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="unverified@example.com",
            password="Password123!",
            first_name="Unverified",
            last_name="User",
            is_verified=False,
        )
        self.verify_url = reverse("api-v1:accounts:verify-email")
        self.resend_url = reverse("api-v1:accounts:resend-verification")

    def test_verify_email_valid_token(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token="valid-verification-token-12345678",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        response = self.client.post(
            self.verify_url,
            {"token": "valid-verification-token-12345678"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

        token.refresh_from_db()
        self.assertTrue(token.is_used)

    def test_verify_email_expired_token(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token="expired-verification-token-123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            self.verify_url,
            {"token": "expired-verification-token-123456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("expired", str(response.data))

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_verify_email_already_used_token(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token="already-used-verification-token",
            expires_at=timezone.now() + timedelta(hours=24),
            is_used=True,
        )

        response = self.client.post(
            self.verify_url,
            {"token": "already-used-verification-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_verify_email_invalid_token(self):
        response = self.client.post(
            self.verify_url,
            {"token": "nonexistent-token-123456789"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_resend_verification_email(self):
        response = self.client.post(
            self.resend_url,
            {"email": "unverified@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Check new token created
        tokens = EmailVerificationToken.objects.filter(user=self.user, is_used=False)
        self.assertTrue(tokens.exists())
