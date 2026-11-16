from datetime import date, datetime, time, timedelta
from decimal import Decimal
import pytz
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole, UserStatus
from apps.appointments.models import Appointment, AppointmentStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.payments.models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentStatus,
    PlatformSetting,
)

User = get_user_model()


class SaaSAnalyticsAndBITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Super Admin User
        self.super_admin = User.objects.create_user(
            email="admin@eazydoc.com",
            password="AdminPassword123!",
            first_name="Super",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
        )

        # 2. Clinic Owners
        self.owner_a = User.objects.create_user(
            email="owner_a@clinic.com",
            password="OwnerPassword123!",
            first_name="Alice",
            last_name="Owner",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )
        self.owner_b = User.objects.create_user(
            email="owner_b@clinic.com",
            password="OwnerPassword123!",
            first_name="Bob",
            last_name="Owner",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )

        # 3. Patient User
        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="PatientPassword123!",
            first_name="John",
            last_name="Doe",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
        )

        # 4. Doctor User
        self.doctor_user = User.objects.create_user(
            email="doctor@example.com",
            password="DoctorPassword123!",
            first_name="Gregory",
            last_name="House",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            full_name="Dr. Gregory House",
            specialization="Diagnostic Medicine",
            registration_number="MMC-12345",
            registration_council="Maharashtra Medical Council",
            verification_status=DoctorVerificationStatus.VERIFIED,
            years_of_experience=15,
        )

        # 5. Clinics
        self.clinic_a = Clinic.objects.create(
            name="Apollo Health Center",
            slug="apollo-health-center",
            owner=self.owner_a,
            status=ClinicStatus.APPROVED,
            is_verified=True,
            city="Bengaluru",
            state="Karnataka",
            timezone="Asia/Kolkata",
            commission_rate=Decimal("10.00"),  # 10% override
        )
        self.clinic_b = Clinic.objects.create(
            name="City Care Clinic",
            slug="city-care-clinic",
            owner=self.owner_b,
            status=ClinicStatus.APPROVED,
            is_verified=True,
            city="Mumbai",
            state="Maharashtra",
            timezone="Asia/Kolkata",
            commission_rate=None,  # default 5%
        )

        # 6. Doctor affiliations across both clinics (Multi-clinic doctor practice)
        self.doc_assoc_a = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            consultation_fee=Decimal("1000.00"),
            status=DoctorClinicStatus.ACTIVE,
        )
        self.doc_assoc_b = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_b,
            consultation_fee=Decimal("500.00"),
            status=DoctorClinicStatus.ACTIVE,
        )

        # 7. Create Appointments, Payments, and Commissions
        now = timezone.now()
        # Appointment 1 at Clinic A: Completed, Paid 1000.00 (10% commission = 100.00, clinic_share = 900.00)
        self.appt_1 = Appointment.objects.create(
            booking_reference="EZD-TEST-001",
            clinic=self.clinic_a,
            doctor=self.doctor,
            doctor_clinic=self.doc_assoc_a,
            patient=self.patient_user,
            start_at=now - timedelta(days=2),
            end_at=now - timedelta(days=2, hours=-1),
            status=AppointmentStatus.COMPLETED,
            consultation_fee=Decimal("1000.00"),
        )
        self.pay_1 = Payment.objects.create(
            appointment=self.appt_1,
            clinic=self.clinic_a,
            patient=self.patient_user,
            amount=Decimal("1000.00"),
            currency="INR",
            status=PaymentStatus.PAID,
            gateway_order_id="order_001",
            gateway_payment_id="pay_001",
        )
        self.comm_1 = CommissionRecord.objects.create(
            payment=self.pay_1,
            appointment=self.appt_1,
            clinic=self.clinic_a,
            gross_amount=Decimal("1000.00"),
            commission_rate=Decimal("10.00"),
            commission_amount=Decimal("100.00"),
            clinic_share=Decimal("900.00"),
            status=CommissionStatus.SETTLED,
        )

        # Appointment 2 at Clinic B: Confirmed, Paid 500.00 (5% commission = 25.00, clinic_share = 475.00)
        self.appt_2 = Appointment.objects.create(
            booking_reference="EZD-TEST-002",
            clinic=self.clinic_b,
            doctor=self.doctor,
            doctor_clinic=self.doc_assoc_b,
            patient=self.patient_user,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=1, hours=1),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )
        self.pay_2 = Payment.objects.create(
            appointment=self.appt_2,
            clinic=self.clinic_b,
            patient=self.patient_user,
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PAID,
            gateway_order_id="order_002",
            gateway_payment_id="pay_002",
        )
        self.comm_2 = CommissionRecord.objects.create(
            payment=self.pay_2,
            appointment=self.appt_2,
            clinic=self.clinic_b,
            gross_amount=Decimal("500.00"),
            commission_rate=Decimal("5.00"),
            commission_amount=Decimal("25.00"),
            clinic_share=Decimal("475.00"),
            status=CommissionStatus.SETTLED,
        )

        # Appointment 3 at Clinic A: Cancelled
        self.appt_3 = Appointment.objects.create(
            booking_reference="EZD-TEST-003",
            clinic=self.clinic_a,
            doctor=self.doctor,
            doctor_clinic=self.doc_assoc_a,
            patient=self.patient_user,
            start_at=now - timedelta(days=1),
            end_at=now - timedelta(days=1, hours=-1),
            status=AppointmentStatus.CANCELLED,
            cancellation_reason="Patient scheduling conflict",
            consultation_fee=Decimal("1000.00"),
        )

    # ------------------------------------------------------------------
    # Super Admin Endpoint Tests
    # ------------------------------------------------------------------

    def test_super_admin_analytics_overview_access(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/overview/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        self.assertEqual(data["appointments"]["total"], 3)
        self.assertEqual(data["appointments"]["completed"], 1)
        self.assertEqual(data["appointments"]["confirmed"], 1)
        self.assertEqual(data["appointments"]["cancelled"], 1)

        # Verify Financial Figures
        self.assertEqual(data["finance"]["gross_collected"], "1500.00")
        self.assertEqual(data["finance"]["platform_commission"], "125.00")
        self.assertEqual(data["finance"]["clinic_payable"], "1375.00")
        self.assertTrue(data["finance"]["accounting_invariant_valid"])

    def test_super_admin_revenue_accounting_invariant(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/revenue/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        totals = res.json()["data"]["totals"]

        gross = Decimal(totals["gross_revenue"])
        commission = Decimal(totals["platform_commission"])
        clinic_share = Decimal(totals["clinic_share"])

        # Accounting invariant: gross == commission + clinic_share
        self.assertEqual(gross, commission + clinic_share)
        self.assertEqual(gross, Decimal("1500.00"))
        self.assertEqual(commission, Decimal("125.00"))
        self.assertEqual(clinic_share, Decimal("1375.00"))

    def test_historical_commission_snapshot_immutability(self):
        """
        Verify that changing platform default or clinic commission override
        does NOT retroactively modify historical recorded commission values.
        """
        # Change Clinic A override to 20%
        self.clinic_a.commission_rate = Decimal("20.00")
        self.clinic_a.save()

        # Change platform default setting to 15%
        PlatformSetting.objects.update_or_create(
            key="default_commission_rate",
            defaults={"value": "15.00", "description": "New rate"},
        )

        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/revenue/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        totals = res.json()["data"]["totals"]

        # Historical transactions must still report 125.00 commission, NOT updated 20%/15%
        self.assertEqual(totals["platform_commission"], "125.00")
        self.assertEqual(totals["clinic_share"], "1375.00")

    def test_super_admin_appointment_analytics(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/appointments/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        self.assertEqual(data["totals"]["total_bookings"], 3)
        self.assertEqual(data["totals"]["completed"], 1)
        self.assertEqual(data["totals"]["cancelled"], 1)
        self.assertAlmostEqual(data["totals"]["completion_rate"], 33.33, places=1)
        self.assertAlmostEqual(data["totals"]["cancellation_rate"], 33.33, places=1)

        self.assertEqual(len(data["peak_days"]), 7)
        self.assertEqual(len(data["peak_hours"]), 24)

    def test_super_admin_clinic_performance(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/clinics/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        clinics = res.json()["data"]

        # Clinic A has 1000.00 gross, Clinic B has 500.00 gross
        self.assertEqual(len(clinics), 2)
        top_clinic = clinics[0]
        self.assertEqual(top_clinic["clinic_id"], str(self.clinic_a.id))
        self.assertEqual(top_clinic["gross_volume"], "1000.00")
        self.assertEqual(top_clinic["platform_commission"], "100.00")
        self.assertEqual(top_clinic["clinic_share"], "900.00")

    def test_super_admin_doctor_performance_multi_clinic(self):
        """
        Verify doctor performance preserves separate clinic affiliations and consultation fees.
        """
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/doctors/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        doctors = res.json()["data"]

        self.assertEqual(len(doctors), 1)
        doc = doctors[0]
        self.assertEqual(doc["doctor_id"], str(self.doctor.id))
        self.assertEqual(len(doc["affiliations"]), 2)
        self.assertEqual(doc["total_appointments"], 3)
        self.assertEqual(doc["gross_revenue"], "1500.00")
        self.assertEqual(doc["clinic_share"], "1375.00")

    def test_super_admin_financial_reconciliation(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/reconciliation/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        rec = res.json()["data"]

        # Both paid appointments have exact matching commissions
        self.assertEqual(rec["health_status"], "HEALTHY")
        self.assertEqual(rec["discrepancy_count"], 0)

        # Introduce intentional discrepancy: paid payment without commission record
        orphan_payment = Payment.objects.create(
            appointment=self.appt_1,
            clinic=self.clinic_a,
            patient=self.patient_user,
            amount=Decimal("200.00"),
            currency="INR",
            status=PaymentStatus.PAID,
            gateway_order_id="order_disc",
            gateway_payment_id="pay_disc",
        )

        res_disc = self.client.get("/api/v1/admin/analytics/reconciliation/?period=last_30_days&refresh=true")
        rec_disc = res_disc.json()["data"]
        self.assertEqual(rec_disc["health_status"], "DISCREPANCIES_DETECTED")
        self.assertGreaterEqual(rec_disc["discrepancy_count"], 1)

    def test_super_admin_export_reports(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get("/api/v1/admin/analytics/reports/export/?report_type=revenue&period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv; charset=utf-8")
        content = res.content.decode("utf-8")
        self.assertIn("Payment ID", content)
        self.assertIn("Gross Amount (INR)", content)
        self.assertIn("1000.00", content)

    def test_super_admin_endpoints_permission_denied_for_regular_users(self):
        # Patient denied
        self.client.force_authenticate(user=self.patient_user)
        res = self.client.get("/api/v1/admin/analytics/overview/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Clinic owner denied on admin endpoints
        self.client.force_authenticate(user=self.owner_a)
        res = self.client.get("/api/v1/admin/analytics/overview/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Unauthenticated denied
        self.client.logout()
        res = self.client.get("/api/v1/admin/analytics/overview/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Tenant-Scoped Clinic Owner Analytics Tests
    # ------------------------------------------------------------------

    def test_clinic_owner_overview_scoped(self):
        self.client.force_authenticate(user=self.owner_a)
        res = self.client.get(f"/api/v1/clinics/{self.clinic_a.id}/analytics/overview/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        # Clinic A has 2 appointments (1 completed, 1 cancelled)
        self.assertEqual(data["appointments"]["total"], 2)
        self.assertEqual(data["appointments"]["completed"], 1)
        self.assertEqual(data["appointments"]["cancelled"], 1)
        self.assertEqual(data["finance"]["gross_revenue"], "1000.00")
        self.assertEqual(data["finance"]["platform_commission_deducted"], "100.00")
        self.assertEqual(data["finance"]["clinic_payable_share"], "900.00")

    def test_clinic_owner_multi_tenant_isolation(self):
        """
        Owner A must NOT be able to view Clinic B's analytics.
        """
        self.client.force_authenticate(user=self.owner_a)
        res = self.client.get(f"/api/v1/clinics/{self.clinic_b.id}/analytics/overview/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_clinic_owner_revenue_analytics(self):
        self.client.force_authenticate(user=self.owner_a)
        res = self.client.get(f"/api/v1/clinics/{self.clinic_a.id}/analytics/revenue/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        self.assertEqual(data["totals"]["gross_revenue"], "1000.00")
        self.assertEqual(data["totals"]["clinic_share"], "900.00")
        self.assertEqual(len(data["doctor_breakdown"]), 1)
        self.assertEqual(data["doctor_breakdown"][0]["doctor_id"], str(self.doctor.id))

    def test_clinic_owner_doctor_performance(self):
        self.client.force_authenticate(user=self.owner_a)
        res = self.client.get(f"/api/v1/clinics/{self.clinic_a.id}/analytics/doctors/?period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        docs = res.json()["data"]

        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["consultation_fee"], "1000.00")
        self.assertEqual(docs[0]["clinic_share"], "900.00")

    def test_clinic_owner_export_csv(self):
        self.client.force_authenticate(user=self.owner_a)
        res = self.client.get(f"/api/v1/clinics/{self.clinic_a.id}/analytics/reports/export/?report_type=appointments&period=last_30_days")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv; charset=utf-8")
        content = res.content.decode("utf-8")
        self.assertIn("Appointment ID", content)
        self.assertIn("Patient Name (Masked)", content)
        # Verify patient Doe is masked as "John D."
        self.assertIn("John D.", content)
        self.assertNotIn("John Doe", content)
