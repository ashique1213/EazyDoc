from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus


class DoctorRegistrationLookupTests(APITestCase):
    def setUp(self):
        self.lookup_url = reverse("api-v1:doctors:doctor-registration-lookup")

        self.clinic_owner = User.objects.create_user(
            email="owner@cityclinic.com",
            password="StrongPassword123!",
            first_name="Ramesh",
            last_name="Patel",
            role=UserRole.CLINIC_OWNER,
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

        self.doctor_user = User.objects.create_user(
            email="dr.kavita@example.com",
            password="StrongPassword123!",
            first_name="Kavita",
            last_name="Rao",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.verified_doctor = Doctor.objects.create(
            user=self.doctor_user,
            registration_number="KMC-12345",
            registration_council="Karnataka Medical Council",
            full_name="Dr. Kavita Rao",
            specialization="Pediatrics",
            qualifications="MBBS, MD (Pediatrics)",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

    def test_unauthenticated_lookup_rejected(self):
        response = self.client.get(self.lookup_url, {"registration_number": "KMC-12345"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_cannot_perform_lookup(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get(self.lookup_url, {"registration_number": "KMC-12345"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_registration_number_returns_400(self):
        self.client.force_authenticate(user=self.clinic_owner)
        response = self.client.get(self.lookup_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_clinic_owner_looks_up_verified_doctor_successfully(self):
        self.client.force_authenticate(user=self.clinic_owner)
        response = self.client.get(
            self.lookup_url,
            {"registration_number": "kmc-12345"},  # Case-insensitive check
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertTrue(data["found"])
        self.assertEqual(data["full_name"], "Dr. Kavita Rao")
        self.assertEqual(data["specialization"], "Pediatrics")
        self.assertEqual(data["registration_council"], "Karnataka Medical Council")
        self.assertTrue(data["is_verified"])
        self.assertTrue(data["is_eligible_for_invitation"])

        # Strictly verify sensitive information is NOT leaked
        self.assertNotIn("email", data)
        self.assertNotIn("phone", data)
        self.assertNotIn("documents", data)
        self.assertNotIn("verification_notes", data)
        self.assertNotIn("user", data)

    def test_lookup_non_existent_doctor(self):
        self.client.force_authenticate(user=self.clinic_owner)
        response = self.client.get(
            self.lookup_url,
            {"registration_number": "NON-EXISTENT-999"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertFalse(data["found"])
        self.assertFalse(data["is_eligible_for_invitation"])
        self.assertIsNone(data["doctor_id"])

    def test_pending_or_suspended_doctor_not_eligible_for_invitation(self):
        # Create a suspended doctor
        suspended_user = User.objects.create_user(
            email="suspended@example.com",
            password="StrongPassword123!",
            first_name="Bad",
            last_name="Doctor",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        Doctor.objects.create(
            user=suspended_user,
            registration_number="SUSP-001",
            registration_council="Council X",
            full_name="Dr. Suspended",
            specialization="Surgery",
            qualifications="MBBS",
            verification_status=DoctorVerificationStatus.SUSPENDED,
            is_verified=False,
        )

        self.client.force_authenticate(user=self.clinic_owner)
        response = self.client.get(self.lookup_url, {"registration_number": "SUSP-001"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertTrue(data["found"])
        self.assertFalse(data["is_verified"])
        self.assertFalse(data["is_eligible_for_invitation"])

    def test_ambiguous_registration_number_prompts_for_council(self):
        # Create another doctor with the same registration number in Delhi council
        delhi_user = User.objects.create_user(
            email="dr.delhi@example.com",
            password="StrongPassword123!",
            first_name="Delhi",
            last_name="Doc",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        Doctor.objects.create(
            user=delhi_user,
            registration_number="KMC-12345",  # identical number
            registration_council="Delhi Medical Council",  # different council
            full_name="Dr. Delhi Doc",
            specialization="ENT",
            qualifications="MBBS, MS",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        self.client.force_authenticate(user=self.clinic_owner)
        # Without specifying council -> ambiguous -> returns 400
        ambiguous_res = self.client.get(self.lookup_url, {"registration_number": "KMC-12345"})
        self.assertEqual(ambiguous_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("registration_council", ambiguous_res.data["message"])

        # With council specified -> disambiguated -> returns 200
        resolved_res = self.client.get(
            self.lookup_url,
            {"registration_number": "KMC-12345", "registration_council": "Karnataka Medical Council"},
        )
        self.assertEqual(resolved_res.status_code, status.HTTP_200_OK)
        self.assertEqual(resolved_res.data["data"]["full_name"], "Dr. Kavita Rao")
