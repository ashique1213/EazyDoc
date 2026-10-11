from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus


class DoctorPermissionsTests(APITestCase):
    def setUp(self):
        self.me_url = reverse("api-v1:doctors:doctor-me")
        self.admin_list_url = reverse("api-v1:admin-doctors:admin-doctor-list")

        self.doctor_user = User.objects.create_user(
            email="dr.one@example.com",
            password="StrongPassword123!",
            first_name="Doctor",
            last_name="One",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.doctor_profile = Doctor.objects.create(
            user=self.doctor_user,
            registration_number="REG-11111",
            registration_council="Council One",
            full_name="Dr. One",
            specialization="General Medicine",
            qualifications="MBBS",
            verification_status=DoctorVerificationStatus.PENDING,
        )

        self.other_doctor_user = User.objects.create_user(
            email="dr.two@example.com",
            password="StrongPassword123!",
            first_name="Doctor",
            last_name="Two",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="StrongPassword123!",
            first_name="Patient",
            last_name="User",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.clinic_owner = User.objects.create_user(
            email="clinicowner@example.com",
            password="StrongPassword123!",
            first_name="Clinic",
            last_name="Owner",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.super_admin = User.objects.create_superuser(
            email="admin@eazydoc.com",
            password="AdminPassword123!",
            first_name="Super",
            last_name="Admin",
        )

    def test_doctor_accesses_own_profile(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["registration_number"], "REG-11111")

    def test_other_doctor_cannot_modify_doctor_one_profile(self):
        # Doctor Two only affects their own profile (which doesn't exist yet, gets 404)
        self.client.force_authenticate(user=self.other_doctor_user)
        response = self.client.patch(self.me_url, {"full_name": "Tampered Name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Doctor One profile unchanged
        self.doctor_profile.refresh_from_db()
        self.assertEqual(self.doctor_profile.full_name, "Dr. One")

    def test_patient_cannot_access_doctor_endpoints(self):
        self.client.force_authenticate(user=self.patient_user)
        # GET /me/
        res_me = self.client.get(self.me_url)
        self.assertEqual(res_me.status_code, status.HTTP_403_FORBIDDEN)

        # Admin doctor list
        res_admin = self.client.get(self.admin_list_url)
        self.assertEqual(res_admin.status_code, status.HTTP_403_FORBIDDEN)

    def test_clinic_owner_cannot_access_admin_endpoints(self):
        self.client.force_authenticate(user=self.clinic_owner)
        res = self.client.get(self.admin_list_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_access_admin_doctor_list(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(self.admin_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_unauthenticated_user_rejected(self):
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res_admin = self.client.get(self.admin_list_url)
        self.assertEqual(res_admin.status_code, status.HTTP_401_UNAUTHORIZED)
