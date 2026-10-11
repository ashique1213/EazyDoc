import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus


def create_test_image(filename="doc.png", format="PNG", size=(50, 50)):
    file = io.BytesIO()
    image = Image.new("RGB", size, color="teal")
    image.save(file, format=format)
    file.seek(0)
    return SimpleUploadedFile(filename, file.read(), content_type=f"image/{format.lower()}")


class DoctorProfileCreationTests(APITestCase):
    def setUp(self):
        self.profile_create_url = reverse("api-v1:doctors:doctor-profile-create")
        self.me_url = reverse("api-v1:doctors:doctor-me")

        self.doctor_user = User.objects.create_user(
            email="dr.anita@example.com",
            password="StrongPassword123!",
            first_name="Anita",
            last_name="Desai",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.other_doctor_user = User.objects.create_user(
            email="dr.rahul@example.com",
            password="StrongPassword123!",
            first_name="Rahul",
            last_name="Sharma",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="StrongPassword123!",
            first_name="John",
            last_name="Doe",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.valid_payload = {
            "registration_number": "MMC-98765",
            "registration_council": "Maharashtra Medical Council",
            "registration_state": "Maharashtra",
            "full_name": "Dr. Anita Desai",
            "specialization": "Cardiology",
            "qualifications": "MBBS, MD (General Medicine), DM (Cardiology)",
            "years_of_experience": 12,
            "bio": "Experienced Interventional Cardiologist.",
            "languages": "English, Hindi, Marathi",
        }

    def test_unauthenticated_request_rejected(self):
        response = self.client.post(self.profile_create_url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_doctor_role_rejected(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.post(self.profile_create_url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_doctor_profile_creation(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(self.profile_create_url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        doc_data = response.data["data"]
        self.assertEqual(doc_data["registration_number"], "MMC-98765")
        self.assertEqual(doc_data["verification_status"], DoctorVerificationStatus.DRAFT)
        self.assertFalse(doc_data["is_verified"])
        self.assertEqual(doc_data["full_name"], "Dr. Anita Desai")

        # Verify database record
        doc = Doctor.objects.get(user=self.doctor_user)
        self.assertEqual(doc.normalized_registration_number, "MMC-98765")
        self.assertEqual(doc.normalized_registration_council, "MAHARASHTRA MEDICAL COUNCIL")

    def test_duplicate_doctor_profile_for_same_user_rejected(self):
        self.client.force_authenticate(user=self.doctor_user)
        res1 = self.client.post(self.profile_create_url, self.valid_payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Attempt to create another profile for the same user
        payload2 = dict(self.valid_payload)
        payload2["registration_number"] = "MMC-11111"
        res2 = self.client.post(self.profile_create_url, payload2, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(res2.data).lower())

    def test_duplicate_registration_identity_rejected(self):
        # Doctor 1 creates profile
        self.client.force_authenticate(user=self.doctor_user)
        res1 = self.client.post(self.profile_create_url, self.valid_payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Doctor 2 attempts same registration number in same council
        self.client.force_authenticate(user=self.other_doctor_user)
        res2 = self.client.post(self.profile_create_url, self.valid_payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        errors = res2.data.get("errors", res2.data)
        self.assertIn("registration_number", errors)

    def test_registration_normalization_prevents_case_and_whitespace_bypass(self):
        # Doctor 1 creates profile with "MMC-98765" and "Maharashtra Medical Council"
        self.client.force_authenticate(user=self.doctor_user)
        self.client.post(self.profile_create_url, self.valid_payload, format="json")

        # Doctor 2 attempts " mmc-98765 " and "  maharashtra  medical  council  "
        self.client.force_authenticate(user=self.other_doctor_user)
        bypass_payload = dict(self.valid_payload)
        bypass_payload["registration_number"] = "  mmc-98765  "
        bypass_payload["registration_council"] = "  maharashtra   medical   council  "

        response = self.client.post(self.profile_create_url, bypass_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.data.get("errors", response.data)
        self.assertIn("registration_number", errors)

    def test_same_registration_number_in_different_councils_allowed(self):
        # Doctor 1 in Maharashtra
        self.client.force_authenticate(user=self.doctor_user)
        res1 = self.client.post(self.profile_create_url, self.valid_payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Doctor 2 in Karnataka with same registration number
        self.client.force_authenticate(user=self.other_doctor_user)
        karnataka_payload = dict(self.valid_payload)
        karnataka_payload["registration_council"] = "Karnataka Medical Council"
        karnataka_payload["registration_state"] = "Karnataka"

        res2 = self.client.post(self.profile_create_url, karnataka_payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

    def test_invalid_or_missing_registration_details_rejected(self):
        self.client.force_authenticate(user=self.doctor_user)

        # Missing registration number
        payload = dict(self.valid_payload)
        del payload["registration_number"]
        res = self.client.post(self.profile_create_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid short registration number
        payload = dict(self.valid_payload)
        payload["registration_number"] = "x"
        res = self.client.post(self.profile_create_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing specialization
        payload = dict(self.valid_payload)
        del payload["specialization"]
        res = self.client.post(self.profile_create_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing qualifications
        payload = dict(self.valid_payload)
        del payload["qualifications"]
        res = self.client.post(self.profile_create_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_doctor_can_update_permitted_fields(self):
        self.client.force_authenticate(user=self.doctor_user)
        self.client.post(self.profile_create_url, self.valid_payload, format="json")

        update_payload = {
            "bio": "Updated bio with 15 years experience.",
            "years_of_experience": 15,
            "languages": "English, Hindi, Marathi, Gujarati",
        }
        res = self.client.patch(self.me_url, update_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["years_of_experience"], 15)
        self.assertEqual(res.data["data"]["bio"], "Updated bio with 15 years experience.")
