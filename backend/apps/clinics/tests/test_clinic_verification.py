from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus


class ClinicVerificationTests(APITestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            email="superadmin@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_verified=True,
            is_staff=True,
            is_superuser=True,
        )

        self.owner = User.objects.create_user(
            email="owner@medicare.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        self.clinic = Clinic.objects.create(
            name="Care Diagnostic Center",
            owner=self.owner,
            email="contact@carediag.com",
            phone="+919876543210",
            address_line_1="MG Road",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.PENDING,
        )

    def test_super_admin_approve_pending_clinic(self):
        self.client.force_authenticate(user=self.super_admin)
        url = reverse("api-v1:admin-clinics:clinic-approve", kwargs={"pk": self.clinic.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.status, ClinicStatus.APPROVED)
        self.assertTrue(self.clinic.is_verified)
        self.assertTrue(self.clinic.is_publicly_bookable)
        self.assertIsNotNone(self.clinic.approved_at)
        self.assertEqual(self.clinic.approved_by, self.super_admin)

    def test_super_admin_reject_pending_clinic_with_reason(self):
        self.client.force_authenticate(user=self.super_admin)
        url = reverse("api-v1:admin-clinics:clinic-reject", kwargs={"pk": self.clinic.id})
        reason = "Clinical Establishment Act certificate is blurred. Please upload a clear scan."
        response = self.client.post(url, {"reason": reason}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.status, ClinicStatus.REJECTED)
        self.assertFalse(self.clinic.is_verified)
        self.assertFalse(self.clinic.is_publicly_bookable)
        self.assertEqual(self.clinic.verification_notes, reason)

    def test_reject_without_reason_fails(self):
        self.client.force_authenticate(user=self.super_admin)
        url = reverse("api-v1:admin-clinics:clinic-reject", kwargs={"pk": self.clinic.id})

        # Missing reason
        res1 = self.client.post(url, {}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)

        # Empty reason
        res2 = self.client.post(url, {"reason": "   "}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_clinic_owner_cannot_call_admin_verification_endpoints(self):
        self.client.force_authenticate(user=self.owner)
        approve_url = reverse("api-v1:admin-clinics:clinic-approve", kwargs={"pk": self.clinic.id})
        reject_url = reverse("api-v1:admin-clinics:clinic-reject", kwargs={"pk": self.clinic.id})

        res1 = self.client.post(approve_url)
        self.assertEqual(res1.status_code, status.HTTP_403_FORBIDDEN)

        res2 = self.client.post(reject_url, {"reason": "Self reject"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)

    def test_clinic_owner_cannot_approve_own_clinic_even_if_superadmin(self):
        # Create a clinic owned by a user who is also Super Admin
        admin_owned_clinic = Clinic.objects.create(
            name="Admin Owned Clinic",
            owner=self.super_admin,
            email="admin@medicare.com",
            phone="+919876543210",
            address_line_1="Admin Street",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.PENDING,
        )

        self.client.force_authenticate(user=self.super_admin)
        url = reverse("api-v1:admin-clinics:clinic-approve", kwargs={"pk": admin_owned_clinic.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])
        self.assertIn("cannot approve their own clinic", response.data["message"])

    def test_super_admin_suspend_and_reactivate_clinic(self):
        self.client.force_authenticate(user=self.super_admin)

        # First approve the clinic
        approve_url = reverse("api-v1:admin-clinics:clinic-approve", kwargs={"pk": self.clinic.id})
        self.client.post(approve_url)
        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.status, ClinicStatus.APPROVED)

        # Suspend approved clinic
        suspend_url = reverse("api-v1:admin-clinics:clinic-suspend", kwargs={"pk": self.clinic.id})
        suspension_reason = "License expired pending renewal."
        res_suspend = self.client.post(suspend_url, {"reason": suspension_reason}, format="json")
        self.assertEqual(res_suspend.status_code, status.HTTP_200_OK)

        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.status, ClinicStatus.SUSPENDED)
        self.assertFalse(self.clinic.is_verified)
        self.assertFalse(self.clinic.is_publicly_bookable)
        self.assertEqual(self.clinic.verification_notes, suspension_reason)

        # Reactivate suspended clinic
        reactivate_url = reverse("api-v1:admin-clinics:clinic-reactivate", kwargs={"pk": self.clinic.id})
        res_reactivate = self.client.post(reactivate_url)
        self.assertEqual(res_reactivate.status_code, status.HTTP_200_OK)

        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.status, ClinicStatus.APPROVED)
        self.assertTrue(self.clinic.is_verified)
        self.assertTrue(self.clinic.is_publicly_bookable)

    def test_invalid_status_transitions_rejected(self):
        self.client.force_authenticate(user=self.super_admin)

        # Draft clinic
        draft_clinic = Clinic.objects.create(
            name="Draft Clinic",
            owner=self.owner,
            email="draft@medicare.com",
            phone="+919876543210",
            address_line_1="Draft Street",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.DRAFT,
        )

        # Cannot approve DRAFT clinic directly (must be PENDING)
        approve_draft_url = reverse("api-v1:admin-clinics:clinic-approve", kwargs={"pk": draft_clinic.id})
        res1 = self.client.post(approve_draft_url)
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)

        # Cannot reject DRAFT clinic directly
        reject_draft_url = reverse("api-v1:admin-clinics:clinic-reject", kwargs={"pk": draft_clinic.id})
        res2 = self.client.post(reject_draft_url, {"reason": "Not ready"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

        # Cannot suspend PENDING clinic (must be APPROVED first)
        suspend_pending_url = reverse("api-v1:admin-clinics:clinic-suspend", kwargs={"pk": self.clinic.id})
        res3 = self.client.post(suspend_pending_url, {"reason": "Violations"}, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)

        # Cannot reactivate non-suspended clinic
        reactivate_url = reverse("api-v1:admin-clinics:clinic-reactivate", kwargs={"pk": self.clinic.id})
        res4 = self.client.post(reactivate_url)
        self.assertEqual(res4.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejected_clinic_corrected_and_resubmitted(self):
        # Super admin rejects the clinic
        self.client.force_authenticate(user=self.super_admin)
        reject_url = reverse("api-v1:admin-clinics:clinic-reject", kwargs={"pk": self.clinic.id})
        self.client.post(reject_url, {"reason": "Invalid address line"}, format="json")
        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.status, ClinicStatus.REJECTED)

        # Owner corrects profile information
        self.client.force_authenticate(user=self.owner)
        detail_url = reverse("api-v1:clinics:clinic-detail", kwargs={"pk": self.clinic.id})
        patch_res = self.client.patch(
            detail_url,
            {"address_line_1": "123 Updated Valid Street Address"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)

        # Owner submits clinic for re-verification
        submit_url = reverse("api-v1:clinics:clinic-submit", kwargs={"pk": self.clinic.id})
        submit_res = self.client.post(submit_url)
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)

        self.clinic.refresh_from_db()
        self.assertEqual(self.clinic.status, ClinicStatus.PENDING)
        self.assertEqual(self.clinic.address_line_1, "123 Updated Valid Street Address")

    def test_draft_clinic_submitted_for_verification(self):
        draft_clinic = Clinic.objects.create(
            name="New Draft Clinic",
            owner=self.owner,
            email="draft@medicare.com",
            phone="+919876543210",
            address_line_1="Draft Street",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.DRAFT,
        )

        self.client.force_authenticate(user=self.owner)
        submit_url = reverse("api-v1:clinics:clinic-submit", kwargs={"pk": draft_clinic.id})
        res = self.client.post(submit_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        draft_clinic.refresh_from_db()
        self.assertEqual(draft_clinic.status, ClinicStatus.PENDING)
