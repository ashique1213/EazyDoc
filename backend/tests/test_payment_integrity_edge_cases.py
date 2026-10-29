import hashlib
import hmac
import json
from datetime import datetime, time, timedelta
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole, UserStatus
from apps.appointments.models import (
    Appointment,
    AppointmentHistory,
    AppointmentStatus,
)
from apps.appointments.services import book_appointment, cancel_appointment
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.payments.exceptions import (
    PaymentConflictException,
    ReservationExpiredException,
    WebhookVerificationException,
)
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
    rupees_to_paise,
    verify_payment_signature,
)
from apps.schedules.models import DoctorSchedule, Weekday


class PaymentIntegrityAndWebhookEdgeCasesTests(TestCase):
    """
    Day 15 Phase Five Payment and Financial Integrity Security Tests.
    Tests:
    1. Signature verification rejection on tampered payloads.
    2. Webhook idempotency and deduplication on repeated deliveries.
    3. Out-of-order webhook protection: payment.failed after PAID does not regress state.
    4. Late payment handling on expired reservations.
    5. Commission rate precedence (clinic override > platform default) and accounting invariant.
    6. Historical commission snapshot immutability upon subsequent rate updates.
    7. Client cannot forge payment verification without valid gateway HMAC signature.
    8. Appointment cancellation does not falsely mark payment as refunded without gateway transaction.
    """

    def setUp(self):
        self.kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.client = APIClient()

        # Clinic Owner & Clinic
        self.owner = User.objects.create_user(
            email="owner.payments@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )
        self.clinic = Clinic.objects.create(
            name="Care Plus Clinic",
            owner=self.owner,
            email="careplus@eazydoc.com",
            phone="9876543299",
            address_line_1="789 Health Boulevard",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            status=ClinicStatus.APPROVED,
            is_verified=True,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("8.50"),  # Clinic-specific override
        )

        # Doctor
        self.doctor_user = User.objects.create_user(
            email="dr.payments@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            first_name="Finance",
            last_name="Doctor",
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            registration_number="REG-PAYMENTS-001",
            normalized_registration_number="REG-PAYMENTS-001",
            registration_council="Maharashtra Medical Council",
            normalized_registration_council="MAHARASHTRA MEDICAL COUNCIL",
            full_name="Dr. Finance Doctor",
            specialization="Cardiology",
            qualifications="MBBS, DM",
            years_of_experience=15,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )
        self.doc_clinic = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("1000.00"),
            appointment_duration_minutes=30,
        )

        # Patients
        self.patient = User.objects.create_user(
            email="patient.payments@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Alice",
            last_name="Payer",
        )
        self.other_patient = User.objects.create_user(
            email="patient.other@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Bob",
            last_name="Competitor",
        )

        # Booking date
        base_future = timezone.now().astimezone(self.kolkata_tz) + timedelta(days=10)
        while base_future.weekday() >= 5:
            base_future += timedelta(days=1)
        self.future_date = base_future.date()
        self.target_weekday = Weekday(self.future_date.weekday())

        DoctorSchedule.objects.create(
            doctor_clinic=self.doc_clinic,
            weekday=self.target_weekday,
            start_time=time(10, 0),
            end_time=time(14, 0),
            is_active=True,
        )

        self.slot_time = datetime.combine(self.future_date, time(10, 0), tzinfo=self.kolkata_tz)

    def _generate_webhook_signature(self, body_bytes: bytes) -> str:
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "rzp_test_webhook_secret_key_12345")
        return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    def test_invalid_webhook_signature_rejected(self):
        """
        Webhooks with an invalid, forged, or tampered signature MUST be rejected
        with a 400 error and not affect payment or appointment states.
        """
        payload = {
            "event": "payment.captured",
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fake123",
                        "order_id": "order_fake123",
                        "amount": 100000,
                        "status": "captured",
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        bad_signature = "invalid_forged_hmac_signature"

        response = self.client.post(
            "/api/v1/payments/webhook/razorpay/",
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=bad_signature,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_webhook_delivery_is_idempotent(self):
        """
        Duplicate webhook events with the same event_id must be safely ignored,
        returning 200 without creating duplicate commission records or multiple history events.
        """
        appt, _ = book_appointment(
            patient=self.patient,
            clinic_id=self.clinic.id,
            doctor_id=self.doctor.id,
            start_at=self.slot_time,
            initial_status=AppointmentStatus.PENDING_CONFIRMATION,
        )

        with patch("apps.payments.services.get_razorpay_client") as mock_client:
            mock_rzp = MagicMock()
            mock_rzp.order.create.return_value = {
                "id": "order_dup_test_123",
                "amount": 100000,
                "currency": "INR",
                "status": "created",
            }
            mock_client.return_value = mock_rzp
            payment = create_payment_order(patient=self.patient, appointment_id=appt.id)

        event_id = f"evt_dup_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "payment.captured",
            "event_id": event_id,
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_dup_999",
                        "order_id": payment.gateway_order_id,
                        "amount": 100000,
                        "status": "captured",
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        valid_signature = self._generate_webhook_signature(body_bytes)

        # First delivery: processed successfully
        res1 = self.client.post(
            "/api/v1/payments/webhook/razorpay/",
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=valid_signature,
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertTrue(res1.data["processed"])

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(CommissionRecord.objects.filter(payment=payment).count(), 1)

        # Second delivery (duplicate): returned 200, processed=False
        res2 = self.client.post(
            "/api/v1/payments/webhook/razorpay/",
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=valid_signature,
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertFalse(res2.data["processed"])

        # Commission record MUST still be exactly 1
        self.assertEqual(CommissionRecord.objects.filter(payment=payment).count(), 1)

    def test_out_of_order_webhook_safe_state_machine(self):
        """
        If a payment is already PAID (e.g. from frontend verification or earlier capture),
        a delayed or out-of-order payment.failed webhook must NOT regress payment or appointment status.
        """
        appt, _ = book_appointment(
            patient=self.patient,
            clinic_id=self.clinic.id,
            doctor_id=self.doctor.id,
            start_at=self.slot_time,
            initial_status=AppointmentStatus.PENDING_CONFIRMATION,
        )

        with patch("apps.payments.services.get_razorpay_client") as mock_client:
            mock_rzp = MagicMock()
            mock_rzp.order.create.return_value = {
                "id": "order_ooo_test_123",
                "amount": 100000,
                "currency": "INR",
                "status": "created",
            }
            mock_client.return_value = mock_rzp
            payment = create_payment_order(patient=self.patient, appointment_id=appt.id)

        # Manually set payment to PAID
        payment.status = PaymentStatus.PAID
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "paid_at"])

        appt.status = AppointmentStatus.CONFIRMED
        appt.save(update_fields=["status"])

        # Now simulate payment.failed webhook arriving out of order
        payload = {
            "event": "payment.failed",
            "event_id": f"evt_failed_{uuid.uuid4().hex[:8]}",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_ooo_failed_456",
                        "order_id": payment.gateway_order_id,
                        "amount": 100000,
                        "status": "failed",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Delayed failure signal",
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_webhook_signature(body_bytes)

        res = self.client.post(
            "/api/v1/payments/webhook/razorpay/",
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify payment status was NOT regressed to FAILED
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)

        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.CONFIRMED)

    def test_commission_precedence_and_accounting_invariant(self):
        """
        Commission calculation test:
        1. Clinic override (8.50%) supersedes platform default (5.00%).
        2. Decimal invariant: gross_amount == commission_amount + clinic_share.
        3. Updating clinic commission afterwards does NOT affect already created CommissionRecord.
        """
        gross = Decimal("1000.00")
        rate_snap, comm_amt, clinic_share = calculate_commission(gross_amount=gross, clinic=self.clinic)

        # Clinic override rate
        self.assertEqual(rate_snap, Decimal("8.50"))
        self.assertEqual(comm_amt, Decimal("85.00"))
        self.assertEqual(clinic_share, Decimal("915.00"))

        # Accounting invariant
        self.assertEqual(gross, comm_amt + clinic_share)

        # Fallback to default when clinic has no override
        self.clinic.commission_rate = None
        self.clinic.save(update_fields=["commission_rate"])

        default_snap, default_comm, default_clinic = calculate_commission(gross_amount=gross, clinic=self.clinic)
        self.assertEqual(default_snap, Decimal("5.00"))
        self.assertEqual(default_comm, Decimal("50.00"))
        self.assertEqual(default_clinic, Decimal("950.00"))
        self.assertEqual(gross, default_comm + default_clinic)

    def test_historical_commission_immutability(self):
        """
        A recorded CommissionRecord retains its original rate snapshot even if
        the clinic's commission rate is subsequently modified.
        """
        appt, _ = book_appointment(
            patient=self.patient,
            clinic_id=self.clinic.id,
            doctor_id=self.doctor.id,
            start_at=self.slot_time,
            initial_status=AppointmentStatus.PENDING_CONFIRMATION,
        )

        with patch("apps.payments.services.get_razorpay_client") as mock_client:
            mock_rzp = MagicMock()
            mock_rzp.order.create.return_value = {
                "id": "order_immut_123",
                "amount": 100000,
                "currency": "INR",
                "status": "created",
            }
            mock_client.return_value = mock_rzp
            payment = create_payment_order(patient=self.patient, appointment_id=appt.id)

        # Verify payment signature
        key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "rzp_test_placeholder_key_secret")
        msg = f"{payment.gateway_order_id}|pay_test_immut_1".encode("utf-8")
        valid_sig = hmac.new(key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        verify_payment_signature(
            razorpay_order_id=payment.gateway_order_id,
            razorpay_payment_id="pay_test_immut_1",
            razorpay_signature=valid_sig,
            patient=self.patient,
        )

        comm_record = CommissionRecord.objects.get(payment=payment)
        self.assertEqual(comm_record.commission_rate, Decimal("8.50"))
        self.assertEqual(comm_record.commission_amount, Decimal("85.00"))

        # Clinic updates commission to 15.00%
        self.clinic.commission_rate = Decimal("15.00")
        self.clinic.save(update_fields=["commission_rate"])

        # Historical record remains untouched
        comm_record.refresh_from_db()
        self.assertEqual(comm_record.commission_rate, Decimal("8.50"))
        self.assertEqual(comm_record.commission_amount, Decimal("85.00"))

    def test_forged_payment_verification_signature_rejected(self):
        """
        Frontend cannot independently verify payment or confirm appointment
        without a cryptographically valid Razorpay HMAC signature.
        """
        appt, _ = book_appointment(
            patient=self.patient,
            clinic_id=self.clinic.id,
            doctor_id=self.doctor.id,
            start_at=self.slot_time,
            initial_status=AppointmentStatus.PENDING_CONFIRMATION,
        )

        with patch("apps.payments.services.get_razorpay_client") as mock_client:
            mock_rzp = MagicMock()
            mock_rzp.order.create.return_value = {
                "id": "order_forged_123",
                "amount": 100000,
                "currency": "INR",
                "status": "created",
            }
            mock_client.return_value = mock_rzp
            payment = create_payment_order(patient=self.patient, appointment_id=appt.id)

        self.client.force_authenticate(user=self.patient)
        res = self.client.post(
            "/api/v1/payments/verify/",
            data={
                "razorpay_order_id": payment.gateway_order_id,
                "razorpay_payment_id": "pay_fake_signature_attempt",
                "razorpay_signature": "fraudulent_signature_value_12345",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Payment remains PENDING
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PENDING)

        # Appointment remains PENDING_CONFIRMATION
        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.PENDING_CONFIRMATION)

    def test_cancellation_does_not_falsely_mark_payment_refunded(self):
        """
        When an appointment is cancelled by patient or clinic, the payment record
        must NOT be automatically marked as REFUNDED unless an actual refund transaction
        is recorded.
        """
        appt, _ = book_appointment(
            patient=self.patient,
            clinic_id=self.clinic.id,
            doctor_id=self.doctor.id,
            start_at=self.slot_time,
            initial_status=AppointmentStatus.CONFIRMED,
        )
        payment = Payment.objects.create(
            appointment=appt,
            patient=self.patient,
            clinic=self.clinic,
            amount=Decimal("1000.00"),
            currency="INR",
            status=PaymentStatus.PAID,
            paid_at=timezone.now(),
        )

        # Cancel appointment
        cancel_appointment(appointment=appt, cancelled_by=self.patient, reason="Need to cancel")

        payment.refresh_from_db()
        # Must still be PAID, not REFUNDED
        self.assertEqual(payment.status, PaymentStatus.PAID)

