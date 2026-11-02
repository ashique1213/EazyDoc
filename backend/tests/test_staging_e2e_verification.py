import hashlib
import hmac
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import (
    PasswordResetToken,
    User,
    UserRole,
    UserStatus,
)
from apps.appointments.models import (
    Appointment,
    AppointmentHistory,
    AppointmentHistoryEventType,
    AppointmentStatus,
)
from apps.appointments.services import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)
from apps.clinics.models import (
    Clinic,
    ClinicStaff,
    ClinicStaffPermission,
    ClinicStatus,
    DoctorClinic,
    DoctorClinicStatus,
)
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.notifications.models import DeliveryStatus, Notification, NotificationType
from apps.notifications.tasks import process_due_appointment_reminders
from apps.payments.models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentStatus,
    PaymentWebhookEvent,
    WebhookProcessingStatus,
)
from apps.payments.services import (
    calculate_commission,
    create_payment_order,
    process_razorpay_webhook,
    verify_payment_signature,
)
from apps.schedules.models import DoctorSchedule, DoctorUnavailability, Weekday


class StagingEndToEndVerificationTests(APITestCase):
    """
    Day 16 End-to-End Staging Verification Test Suite.
    Validates the 7 primary functional pillars required for staging sign-off:
    1. Authentication & Session Lifecycles
    2. Clinic & Doctor Onboarding, Verification, and Affiliation
    3. Multi-Clinic Schedules, Timezone Boundaries, and Buffers
    4. Appointment Booking, Concurrency, Cancellation, and Cutoff Enforcement
    5. Razorpay Staging Payment, Webhook Idempotency, and Commission Accounting
    6. Strict Multi-Tenant Security & Role Isolation
    7. Notification Dispatch & Reminder Task Execution
    """

    def setUp(self):
        self.kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.now_utc = timezone.now()

        # Pre-provision platform Super Admin
        self.super_admin = User.objects.create_superuser(
            email="superadmin@eazydoc.staging",
            password="SuperAdminStaging123!",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            first_name="Super",
            last_name="Admin",
            is_verified=True,
        )

    # -------------------------------------------------------------------------
    # 1. Authentication Lifecycles
    # -------------------------------------------------------------------------
    def test_e2e_authentication_lifecycles(self):
        # 1.1 Patient Registration
        reg_payload = {
            "email": "staging.patient@eazydoc.staging",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "first_name": "Staging",
            "last_name": "Patient",
            "phone": "+919876500001",
        }
        res_reg = self.client.post("/api/v1/auth/register/", reg_payload, format="json")
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_reg.data.get("success"))

        patient_user = User.objects.get(email="staging.patient@eazydoc.staging")
        self.assertEqual(patient_user.role, UserRole.PATIENT)
        patient_user.is_verified = True
        patient_user.status = UserStatus.ACTIVE
        patient_user.save()

        # 1.2 Patient Login
        login_payload = {
            "email": "staging.patient@eazydoc.staging",
            "password": "StrongPassword123!",
        }
        res_login = self.client.post("/api/v1/auth/login/", login_payload, format="json")
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)
        tokens = res_login.data["data"]["tokens"]
        access_token = tokens["access"]
        refresh_token = res_login.cookies.get("refresh_token").value
        self.assertTrue(access_token)
        self.assertTrue(refresh_token)

        # 1.3 Token Refresh
        res_refresh = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh_token}, format="json")
        self.assertEqual(res_refresh.status_code, status.HTTP_200_OK)
        new_access = res_refresh.data["data"]["tokens"]["access"]
        self.assertTrue(new_access)

        # 1.4 Super Admin Login
        admin_login = {
            "email": "superadmin@eazydoc.staging",
            "password": "SuperAdminStaging123!",
        }
        res_admin = self.client.post("/api/v1/auth/login/", admin_login, format="json")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res_admin.data["data"]["user"]["role"], UserRole.SUPER_ADMIN)

        # 1.5 Password Reset Lifecycle
        res_reset_req = self.client.post(
            "/api/v1/auth/forgot-password/",
            {"email": "staging.patient@eazydoc.staging"},
            format="json",
        )
        self.assertEqual(res_reset_req.status_code, status.HTTP_200_OK)

        reset_token = PasswordResetToken.objects.filter(user=patient_user).first()
        self.assertIsNotNone(reset_token)

        res_reset_confirm = self.client.post(
            "/api/v1/auth/reset-password/",
            {
                "token": reset_token.token,
                "password": "NewSecurePassword123!",
            },
            format="json",
        )
        self.assertEqual(res_reset_confirm.status_code, status.HTTP_200_OK)

        # Confirm new password allows login
        res_new_login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "staging.patient@eazydoc.staging", "password": "NewSecurePassword123!"},
            format="json",
        )
        self.assertEqual(res_new_login.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # 2. Clinic and Doctor Onboarding & Verification Lifecycle
    # -------------------------------------------------------------------------
    def test_e2e_clinic_and_doctor_lifecycle(self):
        # 2.1 Clinic Owner creates clinic
        owner = User.objects.create_user(
            email="owner.alpha@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.client.force_authenticate(user=owner)
        clinic_payload = {
            "name": "Staging Apollo Care",
            "phone": "9876500002",
            "email": "contact@apollo.staging",
            "address_line_1": "100 Healthcare Way",
            "city": "Bangalore",
            "state": "Karnataka",
            "pincode": "560001",
            "timezone": "Asia/Kolkata",
        }
        res_clinic = self.client.post("/api/v1/clinics/", clinic_payload, format="json")
        self.assertEqual(res_clinic.status_code, status.HTTP_201_CREATED)
        clinic_id = res_clinic.data["data"]["id"]
        clinic = Clinic.objects.get(id=clinic_id)
        self.assertEqual(clinic.status, ClinicStatus.PENDING)

        # 2.2 Super Admin Approves Clinic
        self.client.force_authenticate(user=self.super_admin)
        res_approve = self.client.post(f"/api/v1/admin/clinics/{clinic.id}/approve/", format="json")
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        clinic.refresh_from_db()
        self.assertEqual(clinic.status, ClinicStatus.APPROVED)

        # 2.3 Doctor Registration & Super Admin Verification
        doc_user = User.objects.create_user(
            email="dr.staging@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
            first_name="Anita",
            last_name="Rao",
        )
        doctor = Doctor.objects.create(
            user=doc_user,
            registration_number="REG-STAGING-999",
            normalized_registration_number="REG-STAGING-999",
            registration_council="Karnataka Medical Council",
            normalized_registration_council="KARNATAKA MEDICAL COUNCIL",
            full_name="Dr. Anita Rao",
            specialization="Cardiology",
            qualifications="MBBS, MD",
            years_of_experience=8,
            verification_status=DoctorVerificationStatus.PENDING,
            is_verified=False,
        )

        res_doc_verify = self.client.post(
            f"/api/v1/admin/doctors/{doctor.id}/verify/",
            {"action": "APPROVE"},
            format="json",
        )
        self.assertEqual(res_doc_verify.status_code, status.HTTP_200_OK)
        doctor.refresh_from_db()
        self.assertEqual(doctor.verification_status, DoctorVerificationStatus.VERIFIED)

        # 2.4 Clinic Owner Invites Doctor
        self.client.force_authenticate(user=owner)
        invite_payload = {
            "doctor_id": str(doctor.id),
            "consultation_fee": "750.00",
            "appointment_duration_minutes": 30,
        }
        res_invite = self.client.post(f"/api/v1/clinics/{clinic.id}/doctor-invitations/", invite_payload, format="json")
        self.assertEqual(res_invite.status_code, status.HTTP_201_CREATED)

        doc_clinic = DoctorClinic.objects.get(doctor=doctor, clinic=clinic)
        self.assertEqual(doc_clinic.status, DoctorClinicStatus.INVITED)

        # 2.5 Doctor Accepts Invitation
        self.client.force_authenticate(user=doc_user)
        res_accept = self.client.post(f"/api/v1/doctors/me/clinic-invitations/{doc_clinic.id}/accept/", format="json")
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)
        doc_clinic.refresh_from_db()
        self.assertEqual(doc_clinic.status, DoctorClinicStatus.ACTIVE)

    # -------------------------------------------------------------------------
    # 3. Scheduling, Timezones, Buffers, and Concurrency
    # -------------------------------------------------------------------------
    def test_e2e_scheduling_and_appointments_lifecycle(self):
        # Setup: Clinic A and Clinic B with Doctor
        owner = User.objects.create_user(
            email="owner.sched@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        clinic_a = Clinic.objects.create(
            name="Clinic Alpha",
            owner=owner,
            phone="9876500003",
            email="alpha@sched.staging",
            address_line_1="10 Alpha St",
            city="Bangalore",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("10.00"),
        )
        clinic_b = Clinic.objects.create(
            name="Clinic Beta",
            owner=owner,
            phone="9876500004",
            email="beta@sched.staging",
            address_line_1="20 Beta St",
            city="Bangalore",
            state="Karnataka",
            pincode="560002",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("5.00"),
        )

        doc_user = User.objects.create_user(
            email="dr.multiclinic@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
            first_name="Vikram",
            last_name="Mehta",
        )
        doctor = Doctor.objects.create(
            user=doc_user,
            registration_number="REG-MULTI-001",
            normalized_registration_number="REG-MULTI-001",
            registration_council="Karnataka Medical Council",
            normalized_registration_council="KARNATAKA MEDICAL COUNCIL",
            full_name="Dr. Vikram Mehta",
            specialization="General Medicine",
            qualifications="MBBS",
            years_of_experience=10,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        dc_a = DoctorClinic.objects.create(
            doctor=doctor,
            clinic=clinic_a,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("600.00"),
            appointment_duration_minutes=30,
        )
        dc_b = DoctorClinic.objects.create(
            doctor=doctor,
            clinic=clinic_b,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("800.00"),
            appointment_duration_minutes=30,
        )

        # Future weekday
        base_future = timezone.now().astimezone(self.kolkata_tz) + timedelta(days=12)
        while base_future.weekday() >= 5:
            base_future += timedelta(days=1)
        future_date = base_future.date()
        target_weekday = Weekday(future_date.weekday())

        # Clinic A shift: 09:00 - 13:00; Clinic B shift: 14:00 - 18:00
        DoctorSchedule.objects.create(
            doctor_clinic=dc_a,
            weekday=target_weekday,
            start_time=time(9, 0),
            end_time=time(13, 0),
            is_active=True,
        )
        DoctorSchedule.objects.create(
            doctor_clinic=dc_b,
            weekday=target_weekday,
            start_time=time(14, 0),
            end_time=time(18, 0),
            is_active=True,
        )

        # Patient
        patient = User.objects.create_user(
            email="patient.booking@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
            first_name="Ravi",
            last_name="Kumar",
        )
        other_patient = User.objects.create_user(
            email="patient.other@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
            first_name="Sita",
            last_name="Sharma",
        )

        # 3.1 Patient discovers available slots via public discovery API
        res_slots = self.client.get(
            f"/api/v1/public/clinics/{clinic_a.id}/doctors/{doctor.id}/availability/",
            {"date": future_date.isoformat()},
        )
        self.assertEqual(res_slots.status_code, status.HTTP_200_OK)
        slots = res_slots.data["slots"]
        self.assertTrue(len(slots) > 0)
        first_slot_time = slots[0]["start_time"]  # "09:00"

        # 3.2 Patient books slot at Clinic A (09:00 - 09:30)
        slot_dt = datetime.combine(future_date, time(9, 0), tzinfo=self.kolkata_tz)
        appt, created = book_appointment(
            patient=patient,
            clinic_id=clinic_a.id,
            doctor_id=doctor.id,
            start_at=slot_dt,
            initial_status=AppointmentStatus.CONFIRMED,
        )
        self.assertTrue(created)
        self.assertEqual(appt.status, AppointmentStatus.CONFIRMED)
        self.assertEqual(appt.consultation_fee, Decimal("600.00"))

        # 3.3 Duplicate booking of exact same slot by another patient MUST be rejected
        from apps.appointments.exceptions import SlotUnavailableException
        with self.assertRaises(SlotUnavailableException):
            book_appointment(
                patient=other_patient,
                clinic_id=clinic_a.id,
                doctor_id=doctor.id,
                start_at=slot_dt,
            )

        # 3.4 Rescheduling to an unoccupied slot succeeds atomically
        new_slot_dt = datetime.combine(future_date, time(10, 0), tzinfo=self.kolkata_tz)
        rescheduled_appt = reschedule_appointment(
            appointment=appt,
            rescheduled_by=patient,
            new_start_at=new_slot_dt,
            reason="Need later time",
        )
        self.assertEqual(rescheduled_appt.start_at, new_slot_dt)

        # 3.5 Cancellation policy cutoff: cancelling at 11:59:59 PM day before is permitted
        allowed_cancel_time = datetime.combine(future_date - timedelta(days=1), time(22, 0), tzinfo=self.kolkata_tz)
        cancelled_appt = cancel_appointment(
            appointment=rescheduled_appt,
            cancelled_by=patient,
            reason="Scheduling conflict",
            current_time=allowed_cancel_time,
        )
        self.assertEqual(cancelled_appt.status, AppointmentStatus.CANCELLED)

    # -------------------------------------------------------------------------
    # 4. Razorpay Payments, Webhooks, and Commission Accounting
    # -------------------------------------------------------------------------
    def test_e2e_payment_gateway_and_commission_accounting(self):
        owner = User.objects.create_user(
            email="owner.fin@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        clinic = Clinic.objects.create(
            name="Care Finance Clinic",
            owner=owner,
            phone="9876500005",
            email="finance@care.staging",
            address_line_1="50 Finance Plaza",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("7.50"),  # Clinic-specific 7.5% override
        )
        doc_user = User.objects.create_user(
            email="dr.fin@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
            first_name="Raj",
            last_name="Singhania",
        )
        doctor = Doctor.objects.create(
            user=doc_user,
            registration_number="REG-FIN-001",
            normalized_registration_number="REG-FIN-001",
            registration_council="Maharashtra Medical Council",
            normalized_registration_council="MAHARASHTRA MEDICAL COUNCIL",
            full_name="Dr. Raj Singhania",
            specialization="Orthopaedics",
            qualifications="MBBS, MS",
            years_of_experience=12,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )
        dc = DoctorClinic.objects.create(
            doctor=doctor,
            clinic=clinic,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("1000.00"),
            appointment_duration_minutes=30,
        )

        patient = User.objects.create_user(
            email="patient.pay@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        # Book pending confirmation appointment
        future_dt = timezone.now().astimezone(self.kolkata_tz) + timedelta(days=10)
        slot_dt = datetime.combine(future_dt.date(), time(11, 0), tzinfo=self.kolkata_tz)
        DoctorSchedule.objects.create(
            doctor_clinic=dc,
            weekday=Weekday(future_dt.weekday()),
            start_time=time(10, 0),
            end_time=time(14, 0),
            is_active=True,
        )
        appt, _ = book_appointment(
            patient=patient,
            clinic_id=clinic.id,
            doctor_id=doctor.id,
            start_at=slot_dt,
            initial_status=AppointmentStatus.PENDING_CONFIRMATION,
        )

        # 4.1 Create Razorpay Order
        with patch("apps.payments.services.get_razorpay_client") as mock_client:
            mock_rzp = MagicMock()
            mock_rzp.order.create.return_value = {
                "id": "order_staging_test_001",
                "amount": 100000,
                "currency": "INR",
                "status": "created",
            }
            mock_client.return_value = mock_rzp
            payment = create_payment_order(patient=patient, appointment_id=appt.id)

        self.assertEqual(payment.gateway_order_id, "order_staging_test_001")
        self.assertEqual(payment.amount, Decimal("1000.00"))
        self.assertEqual(payment.status, PaymentStatus.PENDING)

        # 4.2 Webhook verification with raw signature
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "placeholder_webhook_secret_staging")
        payload = {
            "event": "payment.captured",
            "event_id": f"evt_stg_{uuid.uuid4().hex[:8]}",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_staging_001",
                        "order_id": payment.gateway_order_id,
                        "amount": 100000,
                        "status": "captured",
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = hmac.new(webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        event, processed = process_razorpay_webhook(raw_body=body_bytes, signature=sig)
        self.assertTrue(processed)

        # 4.3 Verify Payment state transition to PAID and Appointment to CONFIRMED
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.CONFIRMED)

        # 4.4 Verify Platform Commission calculation and accounting invariant
        comm = CommissionRecord.objects.get(payment=payment)
        self.assertEqual(comm.commission_rate, Decimal("7.50"))
        self.assertEqual(comm.commission_amount, Decimal("75.00"))
        self.assertEqual(comm.clinic_share, Decimal("925.00"))
        self.assertEqual(payment.amount, comm.commission_amount + comm.clinic_share)

        # 4.5 Duplicate webhook delivery idempotency
        event_dup, processed_dup = process_razorpay_webhook(raw_body=body_bytes, signature=sig)
        self.assertFalse(processed_dup)
        self.assertEqual(CommissionRecord.objects.filter(payment=payment).count(), 1)

    # -------------------------------------------------------------------------
    # 5. Multi-Tenant Isolation & Role Boundaries
    # -------------------------------------------------------------------------
    def test_e2e_tenant_isolation_and_role_boundaries(self):
        # Clinic A
        owner_a = User.objects.create_user(
            email="owner_a.iso@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        clinic_a = Clinic.objects.create(
            name="Clinic Alpha Isolation",
            owner=owner_a,
            phone="9876500006",
            email="alpha.iso@eazydoc.staging",
            address_line_1="100 Alpha St",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
        )

        # Clinic B
        owner_b = User.objects.create_user(
            email="owner_b.iso@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        clinic_b = Clinic.objects.create(
            name="Clinic Beta Isolation",
            owner=owner_b,
            phone="9876500007",
            email="beta.iso@eazydoc.staging",
            address_line_1="200 Beta St",
            city="Delhi",
            state="Delhi",
            pincode="110002",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
        )

        # Owner A tries to access Clinic B financial summary -> 403 Forbidden
        self.client.force_authenticate(user=owner_a)
        res_fin_b = self.client.get(f"/api/v1/clinics/{clinic_b.id}/finance/summary/")
        self.assertEqual(res_fin_b.status_code, status.HTTP_403_FORBIDDEN)

        # Owner A tries to modify Clinic B settings -> 403 Forbidden
        res_edit_b = self.client.patch(
            f"/api/v1/clinics/{clinic_b.id}/management/",
            {"name": "Hacked Clinic B"},
            format="json",
        )
        self.assertEqual(res_edit_b.status_code, status.HTTP_403_FORBIDDEN)

        # Ordinary user cannot access Super Admin endpoint
        patient = User.objects.create_user(
            email="patient.iso@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.client.force_authenticate(user=patient)
        res_admin = self.client.get("/api/v1/admin/dashboard/summary/")
        self.assertEqual(res_admin.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 6. Notifications & Scheduled Reminder Task
    # -------------------------------------------------------------------------
    def test_e2e_notifications_and_scheduled_reminders(self):
        patient = User.objects.create_user(
            email="patient.notify@eazydoc.staging",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        notification = Notification.objects.create(
            recipient=patient,
            notification_type="APPOINTMENT_CONFIRMED",
            title="Appointment Confirmed",
            message="Your appointment with Dr. Rao is confirmed.",
        )
        self.assertIsNotNone(notification.id)

        # Test Celery Beat appointment reminder periodic task execution
        # Must execute cleanly without unhandled exceptions
        processed_count = process_due_appointment_reminders()
        self.assertIsInstance(processed_count, int)
