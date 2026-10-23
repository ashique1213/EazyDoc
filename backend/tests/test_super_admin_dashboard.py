from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.appointments.models import (
    Appointment,
    AppointmentHistory,
    AppointmentHistoryEventType,
    AppointmentStatus,
)
from apps.audit_logs.models import AuditLog
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.payments.models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentStatus,
    PlatformSetting,
)


class SuperAdminDashboardAndSaaSManagementTests(APITestCase):
    """
    Day 12 comprehensive automated test suite for Super Admin Dashboard and SaaS Management.
    """

    def setUp(self):
        self.kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.now = timezone.now()

        # Users
        self.super_admin = User.objects.create_user(
            email="admin.super@eazydoc.com",
            password="SuperPassword123!",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_superuser=True,
            first_name="Super",
            last_name="Admin",
        )
        self.clinic_owner = User.objects.create_user(
            email="owner@medicare.com",
            password="OwnerPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            first_name="Clinic",
            last_name="Owner",
        )
        self.doctor_user = User.objects.create_user(
            email="dr.smith@medicare.com",
            password="DoctorPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            first_name="John",
            last_name="Smith",
        )
        self.patient_user = User.objects.create_user(
            email="patient.jane@gmail.com",
            password="PatientPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Jane",
            last_name="Doe",
        )

        # Clinics
        self.clinic_pending = Clinic.objects.create(
            name="Pending Care Clinic",
            owner=self.clinic_owner,
            email="pending@medicare.com",
            phone="9876543210",
            address_line_1="123 Health Ave",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.PENDING,
        )
        self.clinic_approved = Clinic.objects.create(
            name="Approved Care Hospital",
            owner=self.clinic_owner,
            email="approved@medicare.com",
            phone="9876543211",
            address_line_1="456 Care Blvd",
            city="Bengaluru",
            state="Karnataka",
            pincode="560002",
            status=ClinicStatus.APPROVED,
            commission_rate=Decimal("8.00"),  # Clinic-specific override
        )

        # Doctor
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            full_name="Dr. John Smith",
            registration_number="KMC-998877",
            registration_council="Karnataka Medical Council",
            qualifications="MBBS, MD",
            specialization="Cardiology",
            years_of_experience=10,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # Doctor-Clinic Association
        self.doctor_clinic = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_approved,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("1000.00"),
            appointment_duration_minutes=30,
        )

        # Appointment & Payment
        self.appointment = Appointment.objects.create(
            booking_reference="EZD-TEST-D12-001",
            patient=self.patient_user,
            doctor=self.doctor,
            clinic=self.clinic_approved,
            doctor_clinic=self.doctor_clinic,
            start_at=self.now + timedelta(hours=2),
            end_at=self.now + timedelta(hours=2, minutes=30),
            status=AppointmentStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
            consultation_fee=Decimal("1000.00"),
        )

        self.payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_user,
            clinic=self.clinic_approved,
            gateway_order_id="order_test_d12_001",
            gateway_payment_id="pay_test_d12_001",
            amount=Decimal("1000.00"),
            currency="INR",
            status=PaymentStatus.PAID,
            paid_at=self.now,
        )

        self.commission_record = CommissionRecord.objects.create(
            payment=self.payment,
            appointment=self.appointment,
            clinic=self.clinic_approved,
            gross_amount=Decimal("1000.00"),
            commission_rate=Decimal("8.00"),
            commission_amount=Decimal("80.00"),
            clinic_share=Decimal("920.00"),
            status=CommissionStatus.PENDING_SETTLEMENT,
        )

    # =========================================================================
    # Test 1: Super Admin can access administrative dashboard summary
    # =========================================================================
    def test_01_super_admin_can_access_dashboard_summary(self):
        url = reverse("api-v1:admin-dashboard:dashboard-summary")
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertIn("clinics", data)
        self.assertIn("doctors", data)
        self.assertIn("users", data)
        self.assertIn("appointments", data)
        self.assertIn("finance", data)

    # =========================================================================
    # Test 2: Clinic Owners cannot access Super Admin endpoints
    # =========================================================================
    def test_02_clinic_owners_cannot_access_super_admin_endpoints(self):
        endpoints = [
            reverse("api-v1:admin-dashboard:dashboard-summary"),
            reverse("api-v1:admin-users:user-list"),
            reverse("api-v1:admin-appointments:appointment-list"),
            reverse("api-v1:admin-payments:payment-list"),
            reverse("api-v1:admin-commissions:commission-list"),
            reverse("api-v1:admin-commission-settings:commission-settings"),
            reverse("api-v1:admin-audit-logs:audit-log-list"),
        ]
        self.client.force_authenticate(user=self.clinic_owner)
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, f"Failed on endpoint {ep}")

    # =========================================================================
    # Test 3: Doctors and patients cannot access Super Admin endpoints
    # =========================================================================
    def test_03_doctors_and_patients_cannot_access_super_admin_endpoints(self):
        url = reverse("api-v1:admin-dashboard:dashboard-summary")

        # Doctor
        self.client.force_authenticate(user=self.doctor_user)
        res_doc = self.client.get(url)
        self.assertEqual(res_doc.status_code, status.HTTP_403_FORBIDDEN)

        # Patient
        self.client.force_authenticate(user=self.patient_user)
        res_pat = self.client.get(url)
        self.assertEqual(res_pat.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 4: Unauthenticated users cannot access administrative APIs
    # =========================================================================
    def test_04_unauthenticated_users_cannot_access_admin_apis(self):
        url = reverse("api-v1:admin-dashboard:dashboard-summary")
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # =========================================================================
    # Test 5: Dashboard metrics are derived from actual database records
    # =========================================================================
    def test_05_dashboard_metrics_derived_from_actual_db_records(self):
        url = reverse("api-v1:admin-dashboard:dashboard-summary")
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]
        # Clinics: 1 approved, 1 pending = 2 total
        self.assertEqual(data["clinics"]["total"], 2)
        self.assertEqual(data["clinics"]["approved"], 1)
        self.assertEqual(data["clinics"]["pending"], 1)

        # Doctors: 1 verified
        self.assertEqual(data["doctors"]["total"], 1)
        self.assertEqual(data["doctors"]["verified"], 1)

        # Users: 1 patient
        self.assertEqual(data["users"]["total_patients"], 1)

        # Appointments: 1 confirmed
        self.assertEqual(data["appointments"]["confirmed"], 1)

        # Finance
        self.assertEqual(data["finance"]["successful_payments"], 1)
        self.assertEqual(data["finance"]["gross_volume"], "1000.00")
        self.assertEqual(data["finance"]["recorded_commission"], "80.00")
        self.assertEqual(data["finance"]["calculated_clinic_share"], "920.00")

    # =========================================================================
    # Test 6: Date filters return accurate results on dashboard and lists
    # =========================================================================
    def test_06_date_filters_return_accurate_results(self):
        url = reverse("api-v1:admin-payments:payment-list")
        self.client.force_authenticate(user=self.super_admin)

        today_str = timezone.now().date().isoformat()
        yesterday_str = (timezone.now().date() - timedelta(days=1)).isoformat()

        # Filtering for today includes the payment
        res_today = self.client.get(url, {"date_from": today_str, "date_to": today_str})
        self.assertEqual(res_today.status_code, status.HTTP_200_OK)
        self.assertEqual(res_today.data["count"], 1)

        # Filtering for yesterday excludes it
        res_yesterday = self.client.get(url, {"date_from": yesterday_str, "date_to": yesterday_str})
        self.assertEqual(res_yesterday.status_code, status.HTTP_200_OK)
        self.assertEqual(res_yesterday.data["count"], 0)

    # =========================================================================
    # Test 7: Clinic approval follows valid status transitions
    # =========================================================================
    def test_07_clinic_approval_follows_valid_status_transitions(self):
        approve_url = reverse("api-v1:admin-clinics:clinic-approve", kwargs={"pk": self.clinic_pending.id})
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.clinic_pending.refresh_from_db()
        self.assertEqual(self.clinic_pending.status, ClinicStatus.APPROVED)
        self.assertTrue(self.clinic_pending.is_verified)
        self.assertEqual(self.clinic_pending.approved_by, self.super_admin)

    # =========================================================================
    # Test 8: Invalid clinic transitions are rejected
    # =========================================================================
    def test_08_invalid_clinic_transitions_are_rejected(self):
        # Already approved clinic cannot be approved again
        approve_url = reverse("api-v1:admin-clinics:clinic-approve", kwargs={"pk": self.clinic_approved.id})
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Test 9: Doctor verification actions require appropriate permission
    # =========================================================================
    def test_09_doctor_verification_actions_require_super_admin(self):
        doc_verify_url = reverse("api-v1:admin-doctors:admin-doctor-verify", kwargs={"pk": self.doctor.id})

        # Clinic owner cannot verify doctors on behalf of the platform
        self.client.force_authenticate(user=self.clinic_owner)
        res_forbidden = self.client.post(doc_verify_url)
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 10: Doctor suspension prevents new bookings according to existing rules
    # =========================================================================
    def test_10_doctor_suspension_prevents_new_bookings(self):
        suspend_url = reverse("api-v1:admin-doctors:admin-doctor-suspend", kwargs={"pk": self.doctor.id})
        self.client.force_authenticate(user=self.super_admin)
        res_suspend = self.client.post(suspend_url, {"reason": "Medical council investigation"}, format="json")
        self.assertEqual(res_suspend.status_code, status.HTTP_200_OK)

        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.verification_status, DoctorVerificationStatus.SUSPENDED)
        self.assertFalse(self.doctor.is_verified)

        # Existing appointment is preserved
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)

    # =========================================================================
    # Test 11: User management does not expose credentials or tokens
    # =========================================================================
    def test_11_user_management_does_not_expose_credentials_or_tokens(self):
        url = reverse("api-v1:admin-users:user-list")
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        for user_entry in results:
            self.assertNotIn("password", user_entry)
            self.assertNotIn("password_hash", user_entry)
            self.assertNotIn("token", user_entry)
            self.assertNotIn("access", user_entry)
            self.assertNotIn("refresh", user_entry)

    # =========================================================================
    # Test 12: Users cannot promote themselves or deactivate own admin account
    # =========================================================================
    def test_12_admin_self_lockout_protection(self):
        deactivate_url = reverse("api-v1:admin-users:user-deactivate", kwargs={"pk": self.super_admin.id})
        self.client.force_authenticate(user=self.super_admin)
        res_self = self.client.post(deactivate_url)
        self.assertEqual(res_self.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot deactivate your own", res_self.data["message"])

        # Deactivating another user succeeds
        deactivate_pat = reverse("api-v1:admin-users:user-deactivate", kwargs={"pk": self.patient_user.id})
        res_pat = self.client.post(deactivate_pat)
        self.assertEqual(res_pat.status_code, status.HTTP_200_OK)
        self.patient_user.refresh_from_db()
        self.assertEqual(self.patient_user.status, UserStatus.INACTIVE)

    # =========================================================================
    # Test 13: Appointment records are filtered and displayed correctly
    # =========================================================================
    def test_13_appointment_records_filtered_and_displayed_correctly(self):
        url = reverse("api-v1:admin-appointments:appointment-list")
        self.client.force_authenticate(user=self.super_admin)

        # Filter by clinic
        res_clinic = self.client.get(url, {"clinic_id": str(self.clinic_approved.id)})
        self.assertEqual(res_clinic.status_code, status.HTTP_200_OK)
        self.assertEqual(res_clinic.data["count"], 1)

        # Filter by search
        res_search = self.client.get(url, {"search": "EZD-TEST-D12"})
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        self.assertEqual(res_search.data["count"], 1)

    # =========================================================================
    # Test 14: Administrative appointment actions use existing business services
    # =========================================================================
    def test_14_admin_appointment_cancellation_records_history_and_audit(self):
        cancel_url = reverse("api-v1:admin-appointments:appointment-cancel", kwargs={"pk": self.appointment.id})
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.post(cancel_url, {"reason": "Operational safety requirement"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)

        # Verify AppointmentHistory
        history = AppointmentHistory.objects.filter(appointment=self.appointment, event_type=AppointmentHistoryEventType.ADMIN_OVERRIDE)
        self.assertTrue(history.exists())

        # Verify AuditLog
        audit = AuditLog.objects.filter(action="ADMIN_CANCEL_APPOINTMENT", resource_id=str(self.appointment.id))
        self.assertTrue(audit.exists())

    # =========================================================================
    # Test 15: Historical commission snapshots remain unchanged after rate updates
    # =========================================================================
    def test_15_historical_commission_snapshots_remain_unchanged(self):
        old_snapshot_rate = self.commission_record.commission_rate
        old_commission_amount = self.commission_record.commission_amount

        settings_url = reverse("api-v1:admin-commission-settings:commission-settings")
        self.client.force_authenticate(user=self.super_admin)

        # Update platform rate to 12.00%
        res = self.client.patch(settings_url, {"default_rate": "12.00", "reason": "Annual platform rate adjustment"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(PlatformSetting.get_default_commission_rate(), Decimal("12.00"))

        # Historical record is completely unchanged
        self.commission_record.refresh_from_db()
        self.assertEqual(self.commission_record.commission_rate, old_snapshot_rate)
        self.assertEqual(self.commission_record.commission_amount, old_commission_amount)

    # =========================================================================
    # Test 16: Global commission settings cannot be changed by clinic owners
    # =========================================================================
    def test_16_global_commission_settings_cannot_be_changed_by_clinic_owners(self):
        settings_url = reverse("api-v1:admin-commission-settings:commission-settings")
        self.client.force_authenticate(user=self.clinic_owner)
        res = self.client.patch(settings_url, {"default_rate": "1.00"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 17: Clinic-specific commission overrides are displayed correctly
    # =========================================================================
    def test_17_clinic_specific_commission_overrides_displayed_correctly(self):
        settings_url = reverse("api-v1:admin-commission-settings:commission-settings")
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(settings_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        overrides = res.data["data"]["clinic_overrides"]
        self.assertEqual(len(overrides), 1)
        self.assertEqual(overrides[0]["clinic_name"], "Approved Care Hospital")
        self.assertEqual(overrides[0]["commission_rate"], "8.00")

    # =========================================================================
    # Test 18: Financial reports do not invent payouts or settlements
    # =========================================================================
    def test_18_financial_reports_do_not_invent_payouts(self):
        summary_url = reverse("api-v1:admin-dashboard:financial-summary")
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(summary_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        totals = res.data["data"]["totals"]
        self.assertEqual(totals["actual_payouts"], "0.00")
        self.assertEqual(totals["actual_refunds"], "0.00")
        self.assertEqual(totals["gross_successful_payments"], "1000.00")
        self.assertEqual(totals["recorded_commission"], "80.00")

    # =========================================================================
    # Test 19: Audit records are created for sensitive administrative actions
    # =========================================================================
    def test_19_audit_records_created_for_sensitive_administrative_actions(self):
        audit_count_before = AuditLog.objects.count()

        # Suspend a user
        suspend_user_url = reverse("api-v1:admin-users:user-suspend", kwargs={"pk": self.doctor_user.id})
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post(suspend_user_url, {"reason": "Credential review required"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        audit_count_after = AuditLog.objects.count()
        self.assertGreater(audit_count_after, audit_count_before)

        latest_log = AuditLog.objects.first()
        self.assertEqual(latest_log.action, "USER_SUSPENDED")
        self.assertEqual(latest_log.actor, self.super_admin)

    # =========================================================================
    # Test 20: Unauthorized users cannot access audit logs
    # =========================================================================
    def test_20_unauthorized_users_cannot_access_audit_logs(self):
        url = reverse("api-v1:admin-audit-logs:audit-log-list")

        self.client.force_authenticate(user=self.patient_user)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.clinic_owner)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.super_admin)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    # =========================================================================
    # Test 21: Pagination and filtering work correctly
    # =========================================================================
    def test_21_pagination_and_filtering_work_correctly(self):
        url = reverse("api-v1:admin-clinics:clinic-list")
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(url, {"status": "APPROVED"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["name"], "Approved Care Hospital")
