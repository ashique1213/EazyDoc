from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User, UserRole, UserStatus


class JwtAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jwttest@example.com",
            password="StrongPassword123!",
            first_name="JWT",
            last_name="Tester",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)
        self.me_url = reverse("api-v1:accounts:current-user")
        self.refresh_url = reverse("api-v1:accounts:token-refresh")
        self.logout_url = reverse("api-v1:accounts:logout")

    def test_authenticated_request_via_header(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "jwttest@example.com")

    def test_authenticated_request_via_cookie(self):
        self.client.credentials()  # Clear authorization header
        self.client.cookies["access_token"] = self.access_token
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "jwttest@example.com")

    def test_token_refresh_via_body(self):
        response = self.client.post(
            self.refresh_url, {"refresh": str(self.refresh)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("tokens", response.data["data"])
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_token_refresh_via_cookie(self):
        self.client.cookies["refresh_token"] = str(self.refresh)
        response = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("tokens", response.data["data"])

    def test_invalid_refresh_token_rejected(self):
        response = self.client.post(
            self.refresh_url, {"refresh": "invalid.refresh.token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_logout_revokes_token_and_clears_cookies(self):
        self.client.cookies["refresh_token"] = str(self.refresh)
        self.client.cookies["access_token"] = self.access_token
        response = self.client.post(self.logout_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Subsequent refresh with the blacklisted refresh token must fail
        refresh_attempt = self.client.post(
            self.refresh_url, {"refresh": str(self.refresh)}, format="json"
        )
        self.assertEqual(refresh_attempt.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suspended_user_token_rejected_in_realtime(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        # Verify initial access is good
        res1 = self.client.get(self.me_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Suspend the user
        self.user.status = UserStatus.SUSPENDED
        self.user.save()

        # Immediate rejection even with unexpired token
        res2 = self.client.get(self.me_url)
        self.assertEqual(res2.status_code, status.HTTP_401_UNAUTHORIZED)
