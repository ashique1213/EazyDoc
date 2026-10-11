from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus


class DoctorVerificationWorkflowTests(APITestCase):
    def setUp(self):
        self.submit_url = reverse("api-v1:doctors:doctor-submit-verification")
        self.profile_create_url = reverse("api-v1:doctors:doctor-profile-create")
        self.me_url = reverse("api-v1:doctors:doctor-me")

        self.doctor_user = User.objects.create_user(
            email="dr.priya@example.com",
            password="StrongPassword123!",
            first_name="Priya",
            last_name="Nair",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.super_admin = User.objects.create_superuser(
            email="admin@eazydoc.com",
            password="AdminPassword123!",
            first_name="Super",
            last_name="Admin",
        )

        # Doctor profile in DRAFT
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            registration_number="KMC-45678",
            registration_council="Karnataka Medical Council",
            registration_state="Karnataka",
            full_name="Dr. Priya Nair",
            specialization="Dermatology",
            qualifications="MBBS, MD (Dermatology)",
            years_of_experience=8,
            verification_status=DoctorVerificationStatus.DRAFT,
        )

        self.verify_url = reverse("api-v1:admin-doctors:admin-doctor-verify", kwargs={"pk": self.doctor.pk})
        self.reject_url = reverse("api-v1:admin-doctors:admin-doctor-reject", kwargs={"pk": self.doctor.pk})
        self.suspend_url = reverse("api-v1:admin-doctors:admin-doctor-suspend", kwargs={"pk": self.doctor.pk})
        self.reactivate_url = reverse("api-v1:admin-doctors:admin-doctor-reactivate", kwargs={"pk": self.doctor.pk})

    def test_doctor_submits_profile_transitions_to_pending(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(self.submit_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.PENDING)
        self.assertIsNotNone(self.doctor.submitted_at)
        self.assertFalse(self.doctor.is_verified)

    def test_doctor_cannot_set_own_status_to_verified(self):
        self.client.force_authenticate(user=self.doctor_user)
        # Attempt direct PATCH tampering
        response = self.client.patch(
            self.me_url,
            {"verification_status": "VERIFIED", "is_verified": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        # Remains in DRAFT
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.DRAFT)
        self.assertFalse(self.doctor.is_verified)

    def test_admin_cannot_verify_own_doctor_profile(self):
        # Create a doctor profile linked to the super admin
        admin_doc = Doctor.objects.create(
            user=self.super_admin,
            registration_number="DMC-99999",
            registration_council="Delhi Medical Council",
            full_name="Dr. Admin",
            specialization="General Medicine",
            qualifications="MBBS",
            verification_status=DoctorVerificationStatus.PENDING,
        )
        self.client.force_authenticate(user=self.super_admin)
        self_verify_url = reverse("api-v1:admin-doctors:admin-doctor-verify", kwargs={"pk": admin_doc.pk})

        response = self.client.post(self_verify_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("cannot verify their own", response.data["message"])

    def test_super_admin_verifies_pending_profile(self):
        # Move to PENDING first
        self.doctor.verification_status = DoctorVerificationStatus.PENDING
        self.doctor.save()

        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(self.verify_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.VERIFIED)
        self.assertTrue(self.doctor.is_verified)
        self.assertEqual(self.doctor.verified_by, self.super_admin)
        self.assertIsNotNone(self.doctor.verified_at)

    def test_super_admin_rejects_pending_profile_with_reason(self):
        self.doctor.verification_status = DoctorVerificationStatus.PENDING
        self.doctor.save()

        self.client.force_authenticate(user=self.super_admin)
        reason = "Uploaded registration certificate is blurred; please re-upload clear copy."
        response = self.client.post(self.reject_url, {"reason": reason}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.REJECTED)
        self.assertFalse(self.doctor.is_verified)
        self.assertEqual(self.doctor.verification_notes, reason)

    def test_rejection_requires_valid_reason(self):
        self.doctor.verification_status = DoctorVerificationStatus.PENDING
        self.doctor.save()

        self.client.force_authenticate(user=self.super_admin)
        # Empty reason
        res = self.client.post(self.reject_url, {"reason": ""}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejected_profile_can_be_corrected_and_resubmitted(self):
        # Set to REJECTED with notes
        self.doctor.verification_status = DoctorVerificationStatus.REJECTED
        self.doctor.verification_notes = "Wrong registration council specified."
        self.doctor.save()

        self.client.force_authenticate(user=self.doctor_user)
        # Doctor corrects council
        update_res = self.client.patch(
            self.me_url,
            {"registration_council": "Karnataka Medical Council (Bangalore)"},
            format="json",
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)

        # Doctor resubmits
        submit_res = self.client.post(self.submit_url)
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)

        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.PENDING)
        self.assertFalse(self.doctor.is_verified)

    def test_super_admin_suspends_and_reactivates_doctor(self):
        # Doctor is VERIFIED
        self.doctor.verification_status = DoctorVerificationStatus.VERIFIED
        self.doctor.is_verified = True
        self.doctor.save()

        self.client.force_authenticate(user=self.super_admin)
        suspend_res = self.client.post(
            self.suspend_url,
            {"reason": "Medical license suspended pending inquiry."},
            format="json",
        )
        self.assertEqual(suspend_res.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.SUSPENDED)
        self.assertFalse(self.doctor.is_verified)

        # Suspended doctor cannot resubmit
        self.client.force_authenticate(user=self.doctor_user)
        resubmit_res = self.client.post(self.submit_url)
        self.assertEqual(resubmit_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Admin reactivates
        self.client.force_authenticate(user=self.super_admin)
        reactivate_res = self.client.post(self.reactivate_url)
        self.assertEqual(reactivate_res.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.VERIFIED)
        self.assertTrue(self.doctor.is_verified)
