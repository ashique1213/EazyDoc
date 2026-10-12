from decimal import Decimal
import uuid
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus


class DoctorClinicAssociationTests(APITestCase):
    """
    Comprehensive test suite for Doctor-Clinic associations (Day 6).
    Validates invitation lifecycle, multi-tenant isolation, role permissions,
    fee configurations, and integrity constraints.
    """

    def setUp(self):
        # 1. Clinic Owners
        self.owner_a = User.objects.create_user(
            email="owner_a@apolloclinic.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.owner_b = User.objects.create_user(
            email="owner_b@fortiscare.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        # 2. Doctors
        self.doctor_user_1 = User.objects.create_user(
            email="dr.arun@hospital.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor_1 = Doctor.objects.create(
            user=self.doctor_user_1,
            full_name="Dr. Arun Sharma",
            registration_number="MMC-112233",
            registration_council="Maharashtra Medical Council",
            specialization="Cardiology",
            qualifications="MBBS, MD (Cardiology)",
            years_of_experience=10,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        self.doctor_user_2 = User.objects.create_user(
            email="dr.priya@hospital.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor_2 = Doctor.objects.create(
            user=self.doctor_user_2,
            full_name="Dr. Priya Patel",
            registration_number="GMC-445566",
            registration_council="Gujarat Medical Council",
            specialization="Dermatology",
            qualifications="MBBS, DVD",
            years_of_experience=6,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # Unverified & Suspended doctors
        self.unverified_doctor_user = User.objects.create_user(
            email="dr.unverified@hospital.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.unverified_doctor = Doctor.objects.create(
            user=self.unverified_doctor_user,
            full_name="Dr. Unverified Roy",
            registration_number="DMC-998877",
            registration_council="Delhi Medical Council",
            specialization="General Medicine",
            qualifications="MBBS",
            years_of_experience=2,
            verification_status=DoctorVerificationStatus.PENDING,
            is_verified=False,
        )

        self.suspended_doctor_user = User.objects.create_user(
            email="dr.suspended@hospital.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.suspended_doctor = Doctor.objects.create(
            user=self.suspended_doctor_user,
            full_name="Dr. Suspended Sen",
            registration_number="WBMC-776655",
            registration_council="West Bengal Medical Council",
            specialization="Orthopedics",
            qualifications="MBBS, MS",
            years_of_experience=12,
            verification_status=DoctorVerificationStatus.SUSPENDED,
            is_verified=False,
        )

        # 3. Patient and Super Admin
        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
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
        )

        # 4. Approved and Non-Approved Clinics
        self.clinic_a = Clinic.objects.create(
            name="Apollo Care Clinic",
            slug="apollo-care-clinic",
            owner=self.owner_a,
            email="contact@apollocare.com",
            phone="+919876543210",
            address_line_1="12 Health Avenue",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            status=ClinicStatus.APPROVED,
            is_verified=True,
        )

        self.clinic_b = Clinic.objects.create(
            name="Fortis Wellness Centre",
            slug="fortis-wellness-centre",
            owner=self.owner_b,
            email="contact@fortiswellness.com",
            phone="+919876543211",
            address_line_1="45 Wellness Road",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            status=ClinicStatus.APPROVED,
            is_verified=True,
        )

        self.unapproved_clinic = Clinic.objects.create(
            name="Pending City Clinic",
            slug="pending-city-clinic",
            owner=self.owner_a,
            email="pending@cityclinic.com",
            phone="+919876543212",
            address_line_1="88 Pending Lane",
            city="Mumbai",
            state="Maharashtra",
            pincode="400002",
            status=ClinicStatus.PENDING,
            is_verified=False,
        )

        self.suspended_clinic = Clinic.objects.create(
            name="Suspended Metro Clinic",
            slug="suspended-metro-clinic",
            owner=self.owner_a,
            email="suspended@metroclinic.com",
            phone="+919876543213",
            address_line_1="99 Hold Street",
            city="Mumbai",
            state="Maharashtra",
            pincode="400003",
            status=ClinicStatus.SUSPENDED,
            is_verified=False,
        )

    # --------------------------------------------------------------------------
    # 1. INVITATION CREATION & ELIGIBILITY TESTS
    # --------------------------------------------------------------------------

    def test_01_clinic_owner_can_invite_verified_doctor_to_approved_clinic(self):
        """Rule 1 & 2: Clinic owner invites verified doctor to approved clinic they own."""
        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic_a.id})
        payload = {
            "doctor_id": str(self.doctor_1.id),
            "invitation_message": "Welcome to Apollo Care!",
            "consultation_fee": "500.00",
            "follow_up_fee": "250.00",
            "appointment_duration_minutes": 20,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["status"], DoctorClinicStatus.INVITED)
        self.assertEqual(response.data["data"]["consultation_fee"], "500.00")
        self.assertEqual(response.data["data"]["appointment_duration_minutes"], 20)

        # Check in DB
        assoc = DoctorClinic.objects.get(clinic=self.clinic_a, doctor=self.doctor_1)
        self.assertEqual(assoc.status, DoctorClinicStatus.INVITED)
        self.assertEqual(assoc.invited_by, self.owner_a)
        self.assertIsNone(assoc.accepted_at)

    def test_02_clinic_owner_cannot_invite_unverified_doctor(self):
        """Rule 3: Only verified doctors can be invited."""
        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic_a.id})
        payload = {"doctor_id": str(self.unverified_doctor.id)}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("verified", response.data["message"].lower())
        self.assertFalse(DoctorClinic.objects.filter(doctor=self.unverified_doctor).exists())

    def test_03_clinic_owner_cannot_invite_suspended_doctor(self):
        """Rule 12: Suspended doctors cannot receive invitations."""
        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic_a.id})
        payload = {"doctor_id": str(self.suspended_doctor.id)}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(DoctorClinic.objects.filter(doctor=self.suspended_doctor).exists())

    def test_04_clinic_owner_cannot_invite_from_unapproved_or_suspended_clinic(self):
        """Rule 2 & 12: Only approved clinics can invite doctors."""
        self.client.force_authenticate(user=self.owner_a)

        # Pending clinic
        url_pending = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.unapproved_clinic.id})
        res_pending = self.client.post(url_pending, {"doctor_id": str(self.doctor_1.id)}, format="json")
        self.assertEqual(res_pending.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("approved", res_pending.data["message"].lower())

        # Suspended clinic
        url_suspended = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.suspended_clinic.id})
        res_suspended = self.client.post(url_suspended, {"doctor_id": str(self.doctor_1.id)}, format="json")
        self.assertEqual(res_suspended.status_code, status.HTTP_400_BAD_REQUEST)

    def test_05_duplicate_doctor_clinic_invitation_prevented(self):
        """Rule 7: Duplicate doctor-clinic associations prevented."""
        # Create initial invitation
        DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.INVITED,
            invited_by=self.owner_a,
        )

        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic_a.id})
        response = self.client.post(url, {"doctor_id": str(self.doctor_1.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already pending", response.data["message"].lower())
        self.assertEqual(DoctorClinic.objects.filter(clinic=self.clinic_a, doctor=self.doctor_1).count(), 1)

    def test_06_cannot_reinvite_if_already_active(self):
        """Rule 7: Cannot invite if already an active member."""
        DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            invited_by=self.owner_a,
            accepted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic_a.id})
        response = self.client.post(url, {"doctor_id": str(self.doctor_1.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already an active", response.data["message"].lower())

    def test_07_safe_reinvitation_workflow_for_rejected_association(self):
        """Rule 7 & 4: Safe re-invitation workflow for rejected or removed associations without duplicate rows."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.REJECTED,
            invited_by=self.owner_a,
            rejected_at=timezone.now(),
            consultation_fee=Decimal("400.00"),
        )

        self.client.force_authenticate(user=self.owner_a)
        url = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic_a.id})
        payload = {
            "doctor_id": str(self.doctor_1.id),
            "invitation_message": "Reconsidering with better terms!",
            "consultation_fee": "600.00",
            "appointment_duration_minutes": 25,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Still only 1 record, updated safely
        self.assertEqual(DoctorClinic.objects.filter(clinic=self.clinic_a, doctor=self.doctor_1).count(), 1)
        assoc.refresh_from_db()
        self.assertEqual(assoc.status, DoctorClinicStatus.INVITED)
        self.assertEqual(assoc.consultation_fee, Decimal("600.00"))
        self.assertEqual(assoc.appointment_duration_minutes, 25)
        self.assertIsNone(assoc.rejected_at)

    # --------------------------------------------------------------------------
    # 2. DOCTOR INVITATION ACCEPTANCE & REJECTION TESTS
    # --------------------------------------------------------------------------

    def test_08_doctor_can_accept_their_own_invitation(self):
        """Rule 4 & 5: Doctor explicitly accepts invitation to become ACTIVE."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.INVITED,
            invited_by=self.owner_a,
            consultation_fee=Decimal("500.00"),
        )

        self.client.force_authenticate(user=self.doctor_user_1)
        url = reverse("api-v1:doctors:doctor-accept-invitation", kwargs={"association_id": assoc.id})
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["status"], DoctorClinicStatus.ACTIVE)

        assoc.refresh_from_db()
        self.assertEqual(assoc.status, DoctorClinicStatus.ACTIVE)
        self.assertIsNotNone(assoc.accepted_at)

    def test_09_doctor_can_reject_their_own_invitation(self):
        """Rule 4: Doctor can reject an invitation."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.INVITED,
            invited_by=self.owner_a,
        )

        self.client.force_authenticate(user=self.doctor_user_1)
        url = reverse("api-v1:doctors:doctor-reject-invitation", kwargs={"association_id": assoc.id})
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assoc.refresh_from_db()
        self.assertEqual(assoc.status, DoctorClinicStatus.REJECTED)
        self.assertIsNotNone(assoc.rejected_at)

    def test_10_doctor_cannot_accept_another_doctors_invitation(self):
        """Security: IDOR prevention - Doctor B cannot accept Doctor A's invitation."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.INVITED,
            invited_by=self.owner_a,
        )

        # Authenticate as Doctor 2
        self.client.force_authenticate(user=self.doctor_user_2)
        url = reverse("api-v1:doctors:doctor-accept-invitation", kwargs={"association_id": assoc.id})
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        assoc.refresh_from_db()
        self.assertEqual(assoc.status, DoctorClinicStatus.INVITED)

    def test_11_invalid_status_transitions_are_rejected(self):
        """Rule 4: Invalid status transitions rejected (cannot accept active/rejected)."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            accepted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.doctor_user_1)
        url = reverse("api-v1:doctors:doctor-accept-invitation", kwargs={"association_id": assoc.id})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Rejection of already active association
        url_reject = reverse("api-v1:doctors:doctor-reject-invitation", kwargs={"association_id": assoc.id})
        res_reject = self.client.post(url_reject, format="json")
        self.assertEqual(res_reject.status_code, status.HTTP_400_BAD_REQUEST)

    # --------------------------------------------------------------------------
    # 3. MULTI-TENANCY & INDEPENDENT CLINIC FEES
    # --------------------------------------------------------------------------

    def test_12_doctor_can_work_at_multiple_clinics_with_independent_fees(self):
        """Rule 6, 10 & 11: One doctor at multiple clinics with independent fees."""
        # Clinic A association (₹500)
        assoc_a = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            follow_up_fee=Decimal("250.00"),
            appointment_duration_minutes=15,
            accepted_at=timezone.now(),
        )

        # Clinic B association (₹700)
        assoc_b = DoctorClinic.objects.create(
            clinic=self.clinic_b,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("700.00"),
            follow_up_fee=Decimal("350.00"),
            appointment_duration_minutes=30,
            accepted_at=timezone.now(),
        )

        # Clinic A updates fee to ₹550
        self.client.force_authenticate(user=self.owner_a)
        url_a = reverse(
            "api-v1:clinics:clinic-doctor-settings",
            kwargs={"clinic_id": self.clinic_a.id, "association_id": assoc_a.id},
        )
        response = self.client.patch(url_a, {"consultation_fee": "550.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify Clinic A changed, Clinic B unchanged
        assoc_a.refresh_from_db()
        assoc_b.refresh_from_db()
        self.assertEqual(assoc_a.consultation_fee, Decimal("550.00"))
        self.assertEqual(assoc_b.consultation_fee, Decimal("700.00"))

    def test_13_clinic_a_cannot_view_or_modify_clinic_b_associations(self):
        """Security: Tenant isolation - Clinic A owner cannot access Clinic B associations."""
        assoc_b = DoctorClinic.objects.create(
            clinic=self.clinic_b,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("700.00"),
            accepted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.owner_a)

        # Try to view Clinic B's doctors
        url_list_b = reverse("api-v1:clinics:clinic-doctor-list", kwargs={"clinic_id": self.clinic_b.id})
        res_list = self.client.get(url_list_b)
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        # Try to modify Clinic B's settings through Clinic B endpoint
        url_settings_b = reverse(
            "api-v1:clinics:clinic-doctor-settings",
            kwargs={"clinic_id": self.clinic_b.id, "association_id": assoc_b.id},
        )
        res_settings = self.client.patch(url_settings_b, {"consultation_fee": "999.00"}, format="json")
        self.assertEqual(res_settings.status_code, status.HTTP_403_FORBIDDEN)

        # Try IDOR: pass Clinic B association id to Clinic A URL
        url_idor = reverse(
            "api-v1:clinics:clinic-doctor-settings",
            kwargs={"clinic_id": self.clinic_a.id, "association_id": assoc_b.id},
        )
        res_idor = self.client.patch(url_idor, {"consultation_fee": "999.00"}, format="json")
        self.assertEqual(res_idor.status_code, status.HTTP_404_NOT_FOUND)

        # Verify fee did not change
        assoc_b.refresh_from_db()
        self.assertEqual(assoc_b.consultation_fee, Decimal("700.00"))

    # --------------------------------------------------------------------------
    # 4. REMOVAL AND INTEGRITY TESTS
    # --------------------------------------------------------------------------

    def test_14_clinic_owner_can_remove_active_association(self):
        """Rule 10 & 11: Removing association sets REMOVED and does not delete doctor profile."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            accepted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.owner_a)
        url = reverse(
            "api-v1:clinics:clinic-doctor-remove",
            kwargs={"clinic_id": self.clinic_a.id, "association_id": assoc.id},
        )
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        assoc.refresh_from_db()
        self.assertEqual(assoc.status, DoctorClinicStatus.REMOVED)
        self.assertIsNotNone(assoc.removed_at)

        # Global Doctor profile is completely intact
        self.assertTrue(Doctor.objects.filter(id=self.doctor_1.id).exists())
        self.doctor_1.refresh_from_db()
        self.assertEqual(self.doctor_1.verification_status, DoctorVerificationStatus.VERIFIED)

    def test_15_removed_associations_cannot_configure_settings(self):
        """Removed association cannot have settings altered."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.REMOVED,
            removed_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.owner_a)
        url = reverse(
            "api-v1:clinics:clinic-doctor-settings",
            kwargs={"clinic_id": self.clinic_a.id, "association_id": assoc.id},
        )
        response = self.client.patch(url, {"consultation_fee": "800.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active", response.data["message"].lower())

    def test_16_invalid_fees_and_durations_are_rejected(self):
        """Data Validation: Non-negative fees and valid durations enforced."""
        assoc = DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            accepted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.owner_a)
        url = reverse(
            "api-v1:clinics:clinic-doctor-settings",
            kwargs={"clinic_id": self.clinic_a.id, "association_id": assoc.id},
        )

        # Negative fee
        res_neg = self.client.patch(url, {"consultation_fee": "-50.00"}, format="json")
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)

        # Too short duration (< 5 min)
        res_short = self.client.patch(url, {"appointment_duration_minutes": 2}, format="json")
        self.assertEqual(res_short.status_code, status.HTTP_400_BAD_REQUEST)

        # Too long duration (> 240 min)
        res_long = self.client.patch(url, {"appointment_duration_minutes": 300}, format="json")
        self.assertEqual(res_long.status_code, status.HTTP_400_BAD_REQUEST)

    def test_17_unauthorized_users_cannot_access_association_endpoints(self):
        """Security: Patients and unauthenticated users receive 401/403."""
        url_invite = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic_a.id})

        # Unauthenticated
        res_unauth = self.client.post(url_invite, {"doctor_id": str(self.doctor_1.id)}, format="json")
        self.assertEqual(res_unauth.status_code, status.HTTP_401_UNAUTHORIZED)

        # Patient
        self.client.force_authenticate(user=self.patient_user)
        res_patient = self.client.post(url_invite, {"doctor_id": str(self.doctor_1.id)}, format="json")
        self.assertEqual(res_patient.status_code, status.HTTP_403_FORBIDDEN)

        # Patient cannot view doctor associations endpoint
        url_me_clinics = reverse("api-v1:doctors:doctor-my-clinics")
        res_doc_list = self.client.get(url_me_clinics)
        self.assertEqual(res_doc_list.status_code, status.HTTP_403_FORBIDDEN)

    def test_18_doctor_can_view_my_clinics_and_invitations(self):
        """Doctor queries /api/v1/doctors/me/clinics/ and /api/v1/doctors/me/clinic-invitations/."""
        # 1 active, 1 pending invitation
        DoctorClinic.objects.create(
            clinic=self.clinic_a,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            accepted_at=timezone.now(),
        )
        DoctorClinic.objects.create(
            clinic=self.clinic_b,
            doctor=self.doctor_1,
            status=DoctorClinicStatus.INVITED,
            consultation_fee=Decimal("700.00"),
            invited_by=self.owner_b,
        )

        self.client.force_authenticate(user=self.doctor_user_1)

        # All clinics
        res_clinics = self.client.get(reverse("api-v1:doctors:doctor-my-clinics"))
        self.assertEqual(res_clinics.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_clinics.data["data"]), 2)

        # Filtered ACTIVE clinics
        res_active = self.client.get(reverse("api-v1:doctors:doctor-my-clinics") + "?status=ACTIVE")
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_active.data["data"]), 1)
        self.assertEqual(res_active.data["data"][0]["clinic"]["name"], "Apollo Care Clinic")

        # Pending invitations
        res_invites = self.client.get(reverse("api-v1:doctors:doctor-my-clinic-invitations"))
        self.assertEqual(res_invites.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_invites.data["data"]), 1)
        self.assertEqual(res_invites.data["data"][0]["clinic"]["name"], "Fortis Wellness Centre")
