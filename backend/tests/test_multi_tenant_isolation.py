import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import (
    Clinic,
    ClinicStaff,
    ClinicStaffPermission,
    ClinicStatus,
    DoctorClinic,
    DoctorClinicStatus,
)
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.schedules.models import DoctorSchedule
from apps.appointments.models import Appointment, AppointmentStatus
from apps.payments.models import CommissionRecord, CommissionStatus, Payment, PaymentStatus
from apps.notifications.models import Notification, NotificationType


class MultiTenantIsolationSecurityTests(APITestCase):
    """
    Comprehensive multi-tenant isolation security test suite.
    Validates tenant boundaries across Clinic A, Clinic B, shared doctors,
    cross-clinic patients, scoped clinic staff, and Super Admin.
    """

    def setUp(self):
        super().setUp()

        # 1. Super Admin
        self.super_admin = User.objects.create_superuser(
            email="admin@eazydoc.com",
            password="AdminPassword123!",
            first_name="Super",
            last_name="Admin",
        )

        # 2. Clinic A & Owner A
        self.owner_a = User.objects.create_user(
            email="owner_a@clinic-a.com",
            password="OwnerPassword123!",
            first_name="Owner",
            last_name="Alpha",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.clinic_a = Clinic.objects.create(
            name="Clinic Alpha",
            owner=self.owner_a,
            email="contact@clinic-a.com",
            phone="9876543210",
            address_line_1="123 Alpha Way",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            status=ClinicStatus.APPROVED,
            is_verified=True,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("6.00"),
        )

        # 3. Clinic B & Owner B
        self.owner_b = User.objects.create_user(
            email="owner_b@clinic-b.com",
            password="OwnerPassword123!",
            first_name="Owner",
            last_name="Beta",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.clinic_b = Clinic.objects.create(
            name="Clinic Beta",
            owner=self.owner_b,
            email="contact@clinic-b.com",
            phone="9876543211",
            address_line_1="456 Beta Street",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            status=ClinicStatus.APPROVED,
            is_verified=True,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("4.50"),
        )

        # 4. Doctor practicing at BOTH clinics
        self.doctor_user = User.objects.create_user(
            email="doctor@healthcare.org",
            password="DoctorPassword123!",
            first_name="Ramesh",
            last_name="Patel",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            registration_number="MMC-998877",
            normalized_registration_number="MMC-998877",
            registration_council="Maharashtra Medical Council",
            normalized_registration_council="MAHARASHTRA MEDICAL COUNCIL",
            full_name="Dr. Ramesh Patel",
            specialization="Cardiology",
            qualifications="MBBS, MD",
            years_of_experience=12,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # Doctor affiliation with Clinic A
        self.doc_clinic_a = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("800.00"),
            appointment_duration_minutes=30,
        )

        # Doctor affiliation with Clinic B
        self.doc_clinic_b = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_b,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("1200.00"),
            appointment_duration_minutes=45,
        )

        # 5. Clinic Staff assigned strictly to Clinic A
        self.staff_a_user = User.objects.create_user(
            email="reception@clinic-a.com",
            password="StaffPassword123!",
            first_name="Staff",
            last_name="Alpha",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.staff_a = ClinicStaff.objects.create(
            clinic=self.clinic_a,
            user=self.staff_a_user,
            role_title="Frontdesk Staff",
            permissions=[
                ClinicStaffPermission.VIEW_APPOINTMENTS,
                ClinicStaffPermission.MANAGE_APPOINTMENTS,
                ClinicStaffPermission.MANAGE_SCHEDULES,
            ],
            is_active=True,
        )

        # 6. Patients
        self.patient_1 = User.objects.create_user(
            email="patient1@gmail.com",
            password="PatientPassword123!",
            first_name="Aarav",
            last_name="Sharma",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.patient_2 = User.objects.create_user(
            email="patient2@gmail.com",
            password="PatientPassword123!",
            first_name="Diya",
            last_name="Verma",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        # Create Appointments at Clinic A and Clinic B
        now = timezone.now()
        tomorrow_10am = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)

        self.appt_clinic_a = Appointment.objects.create(
            booking_reference="EZD-202610-CLINA1",
            patient=self.patient_1,
            doctor_clinic=self.doc_clinic_a,
            doctor=self.doctor,
            clinic=self.clinic_a,
            start_at=tomorrow_10am,
            end_at=tomorrow_10am + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
            consultation_fee=Decimal("800.00"),
        )

        self.appt_clinic_b = Appointment.objects.create(
            booking_reference="EZD-202610-CLINB1",
            patient=self.patient_1,  # Same patient has appt at Clinic B on day 3
            doctor_clinic=self.doc_clinic_b,
            doctor=self.doctor,
            clinic=self.clinic_b,
            start_at=tomorrow_10am + timedelta(days=1),
            end_at=tomorrow_10am + timedelta(days=1, minutes=45),
            status=AppointmentStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
            consultation_fee=Decimal("1200.00"),
        )

        # Financial records
        self.payment_b = Payment.objects.create(
            appointment=self.appt_clinic_b,
            patient=self.patient_1,
            clinic=self.clinic_b,
            gateway_order_id="order_beta_12345",
            gateway_payment_id="pay_beta_12345",
            amount=Decimal("1200.00"),
            status=PaymentStatus.PAID,
            paid_at=timezone.now(),
        )
        self.comm_b = CommissionRecord.objects.create(
            payment=self.payment_b,
            appointment=self.appt_clinic_b,
            clinic=self.clinic_b,
            gross_amount=Decimal("1200.00"),
            commission_rate=Decimal("4.50"),
            commission_amount=Decimal("54.00"),
            clinic_share=Decimal("1146.00"),
            status=CommissionStatus.PENDING_SETTLEMENT,
        )

        # Schedules
        self.schedule_b = DoctorSchedule.objects.create(
            doctor_clinic=self.doc_clinic_b,
            day_of_week=0,
            start_time=time(14, 0),
            end_time=time(18, 0),
            is_active=True,
        )

    # -------------------------------------------------------------------------
    # Test 1: Clinic A cannot view Clinic B's private appointments
    # -------------------------------------------------------------------------
    def test_clinic_a_owner_cannot_view_clinic_b_appointments(self):
        self.client.force_authenticate(user=self.owner_a)

        # Attempt to list Clinic B appointments
        res = self.client.get(f"/api/v1/clinics/{self.clinic_b.id}/appointments/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to retrieve Clinic B appointment directly via ID
        res_detail = self.client.get(f"/api/v1/appointments/{self.appt_clinic_b.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # Test 2: Clinic A cannot access Clinic B's financial records
    # -------------------------------------------------------------------------
    def test_clinic_a_owner_cannot_access_clinic_b_financial_records(self):
        self.client.force_authenticate(user=self.owner_a)

        # Financial summary of Clinic B
        res_summary = self.client.get(f"/api/v1/clinics/{self.clinic_b.id}/finance/summary/")
        self.assertEqual(res_summary.status_code, status.HTTP_403_FORBIDDEN)

        # Financial transaction list of Clinic B
        res_payments = self.client.get(f"/api/v1/clinics/{self.clinic_b.id}/finance/payments/")
        self.assertEqual(res_payments.status_code, status.HTTP_403_FORBIDDEN)

        # Direct payment records endpoint
        res_records = self.client.get(f"/api/v1/payments/clinics/{self.clinic_b.id}/financial-records/")
        self.assertEqual(res_records.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # Test 3: Clinic A cannot edit Clinic B's schedules
    # -------------------------------------------------------------------------
    def test_clinic_a_owner_cannot_edit_or_delete_clinic_b_schedules(self):
        self.client.force_authenticate(user=self.owner_a)

        # Attempt to modify Clinic B's schedule
        res_patch = self.client.patch(
            f"/api/v1/schedules/{self.schedule_b.id}/",
            data={"start_time": "15:00"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to create a schedule for Clinic B using Clinic A authentication
        res_create = self.client.post(
            "/api/v1/schedules/",
            data={
                "doctor_clinic": str(self.doc_clinic_b.id),
                "day_of_week": 1,
                "start_time": "09:00",
                "end_time": "12:00",
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # Test 4: Staff cannot access unassigned clinics
    # -------------------------------------------------------------------------
    def test_staff_cannot_access_unassigned_clinic_b(self):
        self.client.force_authenticate(user=self.staff_a_user)

        # Staff of Clinic A tries to access Clinic B appointments
        res_appts = self.client.get(f"/api/v1/clinics/{self.clinic_b.id}/appointments/")
        self.assertEqual(res_appts.status_code, status.HTTP_403_FORBIDDEN)

        # Staff of Clinic A tries to access Clinic B financial overview
        res_finance = self.client.get(f"/api/v1/clinics/{self.clinic_b.id}/finance/summary/")
        self.assertEqual(res_finance.status_code, status.HTTP_403_FORBIDDEN)

        # Staff of Clinic A tries to manage Clinic B profile
        res_mgmt = self.client.patch(
            f"/api/v1/clinics/{self.clinic_b.id}/management/",
            data={"description": "Hacked"},
            format="json",
        )
        self.assertEqual(res_mgmt.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # Test 5: Staff with VIEW_APPOINTMENTS can view their assigned clinic's appt
    # -------------------------------------------------------------------------
    def test_staff_can_view_assigned_clinic_appointments(self):
        self.client.force_authenticate(user=self.staff_a_user)

        # Authorized appointment in Clinic A
        res_detail = self.client.get(f"/api/v1/appointments/{self.appt_clinic_a.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["booking_reference"], self.appt_clinic_a.booking_reference)

    # -------------------------------------------------------------------------
    # Test 6: Doctors cannot access unrelated patients or appointments
    # -------------------------------------------------------------------------
    def test_doctor_cannot_access_unrelated_appointments(self):
        # Create unrelated doctor and appointment
        other_doctor_user = User.objects.create_user(
            email="other_doc@health.org",
            password="DocPassword123!",
            role=UserRole.DOCTOR,
            is_verified=True,
        )
        other_doctor = Doctor.objects.create(
            user=other_doctor_user,
            registration_number="MMC-112233",
            normalized_registration_number="MMC-112233",
            registration_council="Maharashtra Medical Council",
            normalized_registration_council="MAHARASHTRA MEDICAL COUNCIL",
            full_name="Dr. Priya Nair",
            specialization="Pediatrics",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )
        other_dc = DoctorClinic.objects.create(
            doctor=other_doctor,
            clinic=self.clinic_a,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
        )
        unrelated_appt = Appointment.objects.create(
            booking_reference="EZD-202610-UNREL1",
            patient=self.patient_2,
            doctor_clinic=other_dc,
            doctor=other_doctor,
            clinic=self.clinic_a,
            start_at=timezone.now() + timedelta(days=5),
            end_at=timezone.now() + timedelta(days=5, minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )

        # Authenticate Dr. Patel
        self.client.force_authenticate(user=self.doctor_user)

        # Dr. Patel tries to view unrelated appointment
        res = self.client.get(f"/api/v1/appointments/{unrelated_appt.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Dr. Patel tries to cancel unrelated appointment
        res_cancel = self.client.post(
            f"/api/v1/appointments/{unrelated_appt.id}/cancel/",
            data={"reason": "Unauthorized attempt"},
            format="json",
        )
        self.assertEqual(res_cancel.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # Test 7: Patient isolation - cannot access another patient's appointment
    # -------------------------------------------------------------------------
    def test_patient_cannot_view_or_cancel_another_patients_appointment(self):
        # Patient 2 tries to view Patient 1's appointment
        self.client.force_authenticate(user=self.patient_2)

        res_get = self.client.get(f"/api/v1/appointments/{self.appt_clinic_a.id}/")
        self.assertEqual(res_get.status_code, status.HTTP_403_FORBIDDEN)

        res_cancel = self.client.post(
            f"/api/v1/appointments/{self.appt_clinic_a.id}/cancel/",
            data={"reason": "Sneaky cancel"},
            format="json",
        )
        self.assertEqual(res_cancel.status_code, status.HTTP_403_FORBIDDEN)

        # Patient 2's appointment list does not include Patient 1's appointments
        res_my = self.client.get("/api/v1/appointments/my/")
        self.assertEqual(res_my.status_code, status.HTTP_200_OK)
        booking_refs = [a["booking_reference"] for a in res_my.data.get("results", [])]
        self.assertNotIn(self.appt_clinic_a.booking_reference, booking_refs)

    # -------------------------------------------------------------------------
    # Test 8: Public endpoints do not leak private tenant data
    # -------------------------------------------------------------------------
    def test_public_discovery_does_not_leak_private_tenant_fields(self):
        self.client.logout()

        # Public clinic detail
        res = self.client.get(f"/api/v1/public/clinics/{self.clinic_a.slug}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data

        # Private fields must never appear
        self.assertNotIn("commission_rate", data)
        self.assertNotIn("approved_by", data)
        self.assertNotIn("verification_notes", data)
        self.assertNotIn("owner", data)

        # Draft/Pending clinics must not appear publicly
        draft_clinic = Clinic.objects.create(
            name="Secret Unverified Clinic",
            owner=self.owner_a,
            email="secret@draft.com",
            phone="9000000000",
            address_line_1="Secret Alley",
            city="Goa",
            state="Goa",
            pincode="403001",
            status=ClinicStatus.PENDING,
            is_verified=False,
        )
        res_draft = self.client.get(f"/api/v1/public/clinics/{draft_clinic.slug}/")
        self.assertEqual(res_draft.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # Test 9: Notification links enforce authorization when opened
    # -------------------------------------------------------------------------
    def test_notification_links_enforce_authorization_when_opened(self):
        # Create private notification for Patient 1
        notif = Notification.objects.create(
            recipient=self.patient_1,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Confirmed",
            message="Your appointment is confirmed.",
            related_object_type="appointment",
            related_object_id=str(self.appt_clinic_a.id),
            action_url=f"/appointments/{self.appt_clinic_a.id}",
        )

        # Patient 2 tries to mark or read Patient 1's notification
        self.client.force_authenticate(user=self.patient_2)
        res_read = self.client.post(f"/api/v1/notifications/{notif.id}/read/")
        self.assertEqual(res_read.status_code, status.HTTP_404_NOT_FOUND)

        # Patient 2 follows action_url to appointment
        res_appt = self.client.get(f"/api/v1/appointments/{self.appt_clinic_a.id}/")
        self.assertEqual(res_appt.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # Test 10: Super Admin has platform-wide oversight but audits actions
    # -------------------------------------------------------------------------
    def test_super_admin_can_inspect_across_tenants(self):
        self.client.force_authenticate(user=self.super_admin)

        # Admin can view Clinic A and Clinic B details
        res_a = self.client.get(f"/api/v1/admin/clinics/{self.clinic_a.id}/")
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)

        res_b = self.client.get(f"/api/v1/admin/clinics/{self.clinic_b.id}/")
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)

        # Admin can view platform-wide payments list and financial summary
        res_admin_fin = self.client.get("/api/v1/admin/payments/")
        self.assertEqual(res_admin_fin.status_code, status.HTTP_200_OK)

        res_admin_summary = self.client.get("/api/v1/admin/dashboard/financial-summary/")
        self.assertEqual(res_admin_summary.status_code, status.HTTP_200_OK)
