import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus


def create_test_image(filename="test.png", format="PNG", size=(50, 50)):
    """Helper creating an in-memory valid image file."""
    file = io.BytesIO()
    image = Image.new("RGB", size, color="blue")
    image.save(file, format=format)
    file.seek(0)
    return SimpleUploadedFile(filename, file.read(), content_type=f"image/{format.lower()}")


class ClinicRegistrationTests(APITestCase):
    def setUp(self):
        self.clinic_list_create_url = reverse("api-v1:clinics:clinic-list-create")
        self.my_clinics_url = reverse("api-v1:clinics:my-clinics")

        self.owner = User.objects.create_user(
            email="owner@medicare.com",
            password="StrongPassword123!",
            first_name="Rajesh",
            last_name="Kumar",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.valid_payload = {
            "name": "MediCare Speciality Clinic",
            "description": "Leading healthcare center in Indiranagar.",
            "email": "contact@medicare.com",
            "phone": "+919876543210",
            "address_line_1": "100 Feet Road, 12th Main",
            "address_line_2": "Near Metro Station",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560038",
            "country": "India",
        }

    def test_unauthenticated_request_rejected(self):
        response = self.client.post(self.clinic_list_create_url, self.valid_payload, format="json")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_valid_clinic_creation_pending_by_default(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.clinic_list_create_url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        clinic_data = response.data["data"]
        self.assertEqual(clinic_data["name"], "MediCare Speciality Clinic")
        self.assertEqual(clinic_data["status"], ClinicStatus.PENDING)
        self.assertEqual(clinic_data["owner"]["id"], str(self.owner.id))
        self.assertEqual(clinic_data["slug"], "medicare-speciality-clinic")
        self.assertFalse(clinic_data["is_verified"])
        self.assertFalse(clinic_data["is_publicly_bookable"])

        # DB verification
        clinic = Clinic.objects.get(id=clinic_data["id"])
        self.assertEqual(clinic.owner, self.owner)
        self.assertEqual(clinic.status, ClinicStatus.PENDING)

    def test_valid_clinic_creation_as_draft(self):
        self.client.force_authenticate(user=self.owner)
        payload = self.valid_payload.copy()
        payload["status"] = ClinicStatus.DRAFT
        response = self.client.post(self.clinic_list_create_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["status"], ClinicStatus.DRAFT)

    def test_invalid_fields_validation(self):
        self.client.force_authenticate(user=self.owner)

        # Empty name
        payload = self.valid_payload.copy()
        payload["name"] = "  "
        response = self.client.post(self.clinic_list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid phone format
        payload = self.valid_payload.copy()
        payload["phone"] = "1234"
        response = self.client.post(self.clinic_list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid Indian PIN code (must be 6 digits, first not 0)
        payload = self.valid_payload.copy()
        payload["pincode"] = "012345"
        response = self.client.post(self.clinic_list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid email
        payload = self.valid_payload.copy()
        payload["email"] = "not-an-email"
        response = self.client.post(self.clinic_list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_slug_handling(self):
        self.client.force_authenticate(user=self.owner)

        # Create first clinic
        res1 = self.client.post(self.clinic_list_create_url, self.valid_payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["data"]["slug"], "medicare-speciality-clinic")

        # Create second clinic with same name
        res2 = self.client.post(self.clinic_list_create_url, self.valid_payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        # Suffix must be appended to prevent collision
        self.assertEqual(res2.data["data"]["slug"], "medicare-speciality-clinic-1")

        # Create third clinic with same name
        res3 = self.client.post(self.clinic_list_create_url, self.valid_payload, format="json")
        self.assertEqual(res3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res3.data["data"]["slug"], "medicare-speciality-clinic-2")

    def test_multiple_clinics_for_single_owner(self):
        self.client.force_authenticate(user=self.owner)

        p1 = self.valid_payload.copy()
        p1["name"] = "Branch One"
        self.client.post(self.clinic_list_create_url, p1, format="json")

        p2 = self.valid_payload.copy()
        p2["name"] = "Branch Two"
        self.client.post(self.clinic_list_create_url, p2, format="json")

        response = self.client.get(self.my_clinics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        names = [c["name"] for c in response.data["data"]]
        self.assertIn("Branch One", names)
        self.assertIn("Branch Two", names)

    def test_valid_and_invalid_logo_upload(self):
        self.client.force_authenticate(user=self.owner)

        # Valid image file
        valid_img = create_test_image("clinic.png", "PNG")
        payload = self.valid_payload.copy()
        payload["name"] = "Apollo Health"
        payload["logo"] = valid_img

        response = self.client.post(self.clinic_list_create_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["data"]["logo"])

        # Corrupted / non-image spoofed file
        fake_img = SimpleUploadedFile("fake.png", b"NOT_AN_IMAGE_CONTENT", content_type="image/png")
        payload2 = self.valid_payload.copy()
        payload2["name"] = "Fortis Health"
        payload2["logo"] = fake_img

        response2 = self.client.post(self.clinic_list_create_url, payload2, format="multipart")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
