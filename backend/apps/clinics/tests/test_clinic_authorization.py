from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus


class ClinicAuthorizationTests(APITestCase):
    def setUp(self):
        self.clinic_list_create_url = reverse("api-v1:clinics:clinic-list-create")
        self.my_clinics_url = reverse("api-v1:clinics:my-clinics")

        self.owner_a = User.objects.create_user(
            email="owner_a@medicare.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.owner_b = User.objects.create_user(
            email="owner_b@healthplus.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.patient = User.objects.create_user(
            email="patient@example.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.doctor = User.objects.create_user(
            email="doctor@example.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="StrongPassword123!",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.super_admin = User.objects.create_user(
            email="admin@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_verified=True,
            is_staff=True,
            is_superuser=True,
        )

        # Clinic belonging to Owner A
        self.clinic_a = Clinic.objects.create(
            name="Clinic Alpha",
            owner=self.owner_a,
            email="info@alpha.com",
            phone="+919876543210",
            address_line_1="Alpha Street",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.PENDING,
        )

        # Clinic belonging to Owner B
        self.clinic_b = Clinic.objects.create(
            name="Clinic Beta",
            owner=self.owner_b,
            email="info@beta.com",
            phone="+919876543211",
            address_line_1="Beta Street",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            status=ClinicStatus.PENDING,
        )

    def test_owner_accesses_own_clinic(self):
        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-detail", kwargs={"pk": self.clinic_a.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["id"], str(self.clinic_a.id))
        self.assertEqual(response.data["data"]["name"], "Clinic Alpha")

    def test_owner_cannot_access_another_owners_clinic(self):
        self.client.force_authenticate(user=self.owner_a)
        # Attempting to access Clinic B owned by Owner B
        url = reverse("api-v1:clinics:clinic-detail", kwargs={"pk": self.clinic_b.id})
        response = self.client.get(url)

        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_owner_cannot_patch_another_owners_clinic(self):
        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-detail", kwargs={"pk": self.clinic_b.id})
        response = self.client.patch(url, {"name": "Hacked Name"}, format="json")

        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        self.clinic_b.refresh_from_db()
        self.assertEqual(self.clinic_b.name, "Clinic Beta")

    def test_patient_cannot_create_or_list_clinics(self):
        self.client.force_authenticate(user=self.patient)
        payload = {
            "name": "Patient Clinic",
            "email": "p@test.com",
            "phone": "+919876543210",
            "address_line_1": "Road 1",
            "city": "Delhi",
            "state": "Delhi",
            "pincode": "110001",
        }
        response = self.client.post(self.clinic_list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        list_response = self.client.get(self.my_clinics_url)
        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_cannot_create_clinics(self):
        self.client.force_authenticate(user=self.doctor)
        payload = {
            "name": "Doctor Clinic",
            "email": "doc@test.com",
            "phone": "+919876543210",
            "address_line_1": "Road 1",
            "city": "Delhi",
            "state": "Delhi",
            "pincode": "110001",
        }
        response = self.client.post(self.clinic_list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_cannot_create_clinics(self):
        self.client.force_authenticate(user=self.staff)
        payload = {
            "name": "Staff Clinic",
            "email": "staff@test.com",
            "phone": "+919876543210",
            "address_line_1": "Road 1",
            "city": "Delhi",
            "state": "Delhi",
            "pincode": "110001",
        }
        response = self.client.post(self.clinic_list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_cannot_modify_approval_status_or_owner(self):
        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-detail", kwargs={"pk": self.clinic_a.id})

        # Malicious payload trying to escalate privileges
        payload = {
            "status": ClinicStatus.APPROVED,
            "owner": str(self.owner_b.id),
            "verification_notes": "Self-approved",
            "is_verified": True,
            "description": "Legitimate updated description",
        }
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.clinic_a.refresh_from_db()
        # Permitted field updated
        self.assertEqual(self.clinic_a.description, "Legitimate updated description")
        # Protected fields remain untouched
        self.assertEqual(self.clinic_a.status, ClinicStatus.PENDING)
        self.assertEqual(self.clinic_a.owner, self.owner_a)
        self.assertFalse(self.clinic_a.is_verified)
        self.assertNotEqual(self.clinic_a.verification_notes, "Self-approved")

    def test_super_admin_can_access_and_list_all_clinics(self):
        self.client.force_authenticate(user=self.super_admin)

        # Admin can view clinic_a
        url_a = reverse("api-v1:clinics:clinic-detail", kwargs={"pk": self.clinic_a.id})
        res_a = self.client.get(url_a)
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)

        # Admin can view clinic_b
        url_b = reverse("api-v1:clinics:clinic-detail", kwargs={"pk": self.clinic_b.id})
        res_b = self.client.get(url_b)
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)

        # Admin list shows both clinics
        res_all = self.client.get(self.clinic_list_create_url)
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_all.data["data"]), 2)
