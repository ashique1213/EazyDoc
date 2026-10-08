from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import EmailVerificationToken, User, UserRole, UserStatus


class RegistrationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("api-v1:accounts:register")
        self.valid_payload = {
            "email": "newpatient@example.com",
            "password": "StrongPassword123!",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "9876543210",
            "role": "PATIENT",
        }

    def test_valid_registration(self):
        response = self.client.post(self.register_url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("user", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["email"], "newpatient@example.com")
        self.assertEqual(response.data["data"]["user"]["role"], UserRole.PATIENT)
        self.assertFalse(response.data["data"]["user"]["is_verified"])
        self.assertNotIn("password", response.data["data"]["user"])

        # Verify user in database
        user = User.objects.get(email="newpatient@example.com")
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertEqual(user.status, UserStatus.ACTIVE)

        # Verify email verification token was issued
        token = EmailVerificationToken.objects.filter(user=user, is_used=False).first()
        self.assertIsNotNone(token)
        self.assertTrue(token.is_valid())

    def test_duplicate_email_registration(self):
        User.objects.create_user(
            email="existing@example.com",
            password="Password123!",
            first_name="Existing",
            last_name="User",
        )
        payload = self.valid_payload.copy()
        payload["email"] = "existing@example.com"
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["errors"])

    def test_invalid_email_format(self):
        payload = self.valid_payload.copy()
        payload["email"] = "not-an-email"
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["errors"])

    def test_weak_password_rejected(self):
        payload = self.valid_payload.copy()
        payload["password"] = "123"  # Shorter than 8 chars
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("password", response.data["errors"])

    def test_attempt_to_register_super_admin(self):
        payload = self.valid_payload.copy()
        payload["role"] = "SUPER_ADMIN"
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("role", response.data["errors"])
        self.assertFalse(User.objects.filter(email=payload["email"]).exists())

    def test_attempt_to_register_staff(self):
        payload = self.valid_payload.copy()
        payload["role"] = "STAFF"
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("role", response.data["errors"])

    def test_allowed_roles_can_register(self):
        # DOCTOR registration
        doc_payload = self.valid_payload.copy()
        doc_payload["email"] = "doctor1@example.com"
        doc_payload["phone"] = "9876543211"
        doc_payload["role"] = "DOCTOR"
        res_doc = self.client.post(self.register_url, doc_payload, format="json")
        self.assertEqual(res_doc.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_doc.data["data"]["user"]["role"], "DOCTOR")

        # CLINIC_OWNER registration
        owner_payload = self.valid_payload.copy()
        owner_payload["email"] = "owner1@example.com"
        owner_payload["phone"] = "9876543212"
        owner_payload["role"] = "CLINIC_OWNER"
        res_owner = self.client.post(self.register_url, owner_payload, format="json")
        self.assertEqual(res_owner.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_owner.data["data"]["user"]["role"], "CLINIC_OWNER")

    def test_create_superadmin_management_command(self):
        from django.core.management import call_command
        call_command(
            "create_superadmin",
            email="cmdadmin@eazydoc.com",
            password="AdminPassword123!",
            first_name="Cli",
            last_name="Admin",
        )
        admin = User.objects.get(email="cmdadmin@eazydoc.com")
        self.assertEqual(admin.role, UserRole.SUPER_ADMIN)
        self.assertEqual(admin.status, UserStatus.ACTIVE)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_verified)
        self.assertTrue(admin.check_password("AdminPassword123!"))
