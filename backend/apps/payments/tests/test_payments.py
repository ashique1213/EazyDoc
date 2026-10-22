import hashlib
import hmac
import json
from datetime import datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.appointments.models import Appointment, AppointmentHistoryEventType, AppointmentStatus
from apps.appointments.services import book_appointment
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.payments.models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentAuditAction,
    PaymentAuditLog,
    PaymentStatus,
    PaymentWebhookEvent,
    WebhookProcessingStatus,
)
from apps.payments.services import (
    calculate_commission,
    expire_pending_reservations,
    rupees_to_paise,
)
from apps.schedules.models import DoctorSchedule, Weekday


class RazorpayPaymentAndCommissionTests(APITestCase):
    """
    Comprehensive test suite for Razorpay Payments and Platform Commission (Day 11).
    Validates all 25 specific security, business, and lifecycle requirements.
    """

    def setUp(self):
        self.kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.now_utc = timezone.now()

        # Users
        self.patient_alice = User.objects.create_user(
            email="alice.patient@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Alice",
            last_name="Patient",
        )
        self.patient_bob = User.objects.create_user(
            email="bob.patient@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Bob",
            last_name="Patient",
        )
        self.clinic_owner_a = User.objects.create_user(
            email="owner_a@clinic.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )
        self.clinic_owner_b = User.objects.create_user(
            email="owner_b@clinic.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )
        self.super_admin = User.objects.create_user(
            email="superadmin@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )
        self.doctor_user = User.objects.create_user(
            email="doctor.sharma@medcare.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
        )

        # Clinics
        self.clinic_a = Clinic.objects.create(
            name="Apollo Care Clinic",
            owner=self.clinic_owner_a,
            email="info@apollocare.com",
            phone="9876543210",
            address_line_1="100 MG Road",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            commission_rate=None,  # Uses platform default 5%
        )
        self.clinic_b = Clinic.objects.create(
            name="Fortis Speciality Clinic",
            owner=self.clinic_owner_b,
            email="info@fortiscare.com",
            phone="9876543211",
            address_line_1="200 Indiranagar",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("8.00"),  # Clinic-specific 8%
        )

        # Doctor Profile
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            full_name="Dr. Amit Sharma",
            registration_number="KMC-D11-999",
            registration_council="Karnataka Medical Council",
            verification_status=DoctorVerificationStatus.VERIFIED,
        )

        # Doctor-Clinic Affiliations
        self.assoc_a = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            appointment_duration_minutes=15,
            accepted_at=self.now_utc,
        )
        self.assoc_b = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_b,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("750.00"),
            appointment_duration_minutes=15,
            accepted_at=self.now_utc,
        )

        # Doctor Schedule (Monday 9 AM to 5 PM at Clinic A)
        self.schedule_a = DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_duration_minutes=15,
            buffer_minutes=15,
            is_active=True,
        )

        # Next Monday date
        today = self.now_utc.astimezone(self.kolkata_tz).date()
        days_ahead = (0 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        self.next_monday = today + timedelta(days=days_ahead)
        self.slot_time_utc = datetime.combine(self.next_monday, time(10, 0), tzinfo=self.kolkata_tz).astimezone(dt_timezone.utc)

        # Appointment for Alice
        self.appointment, _ = book_appointment(
            patient=self.patient_alice,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=self.slot_time_utc,
            initial_status=AppointmentStatus.PENDING_CONFIRMATION,
        )

        # Endpoints
        self.create_order_url = reverse("api-v1:payments:create-order")
        self.verify_url = reverse("api-v1:payments:verify")
        self.webhook_url = reverse("api-v1:payments:webhook-razorpay")

    def _mock_razorpay_client(self, order_id="order_test_123456"):
        """Creates a mock Razorpay client for testing order creation and signature verification."""
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            "id": order_id,
            "entity": "order",
            "amount": 50000,
            "currency": "INR",
            "receipt": f"rcpt_{self.appointment.booking_reference}",
            "status": "created",
            "created_at": 1700000000,
        }
        return mock_client

    def _generate_valid_signature(self, order_id: str, payment_id: str) -> str:
        """Generates a valid HMAC-SHA256 signature matching backend test settings."""
        secret = getattr(settings, "RAZORPAY_KEY_SECRET", "placeholder_secret_key_not_used_in_day2")
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def _generate_webhook_signature(self, body_bytes: bytes) -> str:
        """Generates a valid webhook HMAC-SHA256 signature."""
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "placeholder_webhook_secret_key")
        return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    # =========================================================================
    # Test 1: A patient can create a payment order for their own eligible appointment
    # =========================================================================
    @patch("apps.payments.services.get_razorpay_client")
    def test_01_patient_can_create_payment_order_for_own_eligible_appointment(self, mock_get_client):
        mock_get_client.return_value = self._mock_razorpay_client(order_id="order_alice_01")
        self.client.force_authenticate(user=self.patient_alice)

        res = self.client.post(self.create_order_url, {
            "appointment_id": str(self.appointment.id),
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["order_id"], "order_alice_01")
        self.assertEqual(res.data["amount_paise"], 50000)
        self.assertEqual(res.data["currency"], "INR")
        self.assertNotIn("secret", res.data)
        self.assertNotIn("commission", res.data)
        self.assertNotIn("clinic_share", res.data)

        # Verify Payment model state
        payment = Payment.objects.get(gateway_order_id="order_alice_01")
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(payment.patient, self.patient_alice)
        self.assertEqual(payment.amount, Decimal("500.00"))

    # =========================================================================
    # Test 2: An unauthenticated user cannot initiate a payment
    # =========================================================================
    def test_02_unauthenticated_user_cannot_initiate_payment(self):
        res = self.client.post(self.create_order_url, {
            "appointment_id": str(self.appointment.id),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # =========================================================================
    # Test 3: A patient cannot pay for another patient's appointment
    # =========================================================================
    def test_03_patient_cannot_pay_for_another_patient_appointment(self):
        self.client.force_authenticate(user=self.patient_bob)

        res = self.client.post(self.create_order_url, {
            "appointment_id": str(self.appointment.id),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("permission", str(res.data))

    # =========================================================================
    # Test 4: The server uses the trusted appointment amount
    # =========================================================================
    @patch("apps.payments.services.get_razorpay_client")
    def test_04_server_uses_trusted_appointment_amount(self, mock_get_client):
        mock_client = self._mock_razorpay_client(order_id="order_trusted_04")
        mock_get_client.return_value = mock_client
        self.client.force_authenticate(user=self.patient_alice)

        res = self.client.post(self.create_order_url, {
            "appointment_id": str(self.appointment.id),
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Verify order creation received exact trusted paise amount
        mock_client.order.create.assert_called_once()
        called_args = mock_client.order.create.call_args[1]["data"]
        self.assertEqual(called_args["amount"], 50000)

    # =========================================================================
    # Test 5: Client-supplied amounts cannot manipulate payment orders
    # =========================================================================
    @patch("apps.payments.services.get_razorpay_client")
    def test_05_client_supplied_amounts_cannot_manipulate_payment_orders(self, mock_get_client):
        mock_client = self._mock_razorpay_client(order_id="order_tamper_05")
        mock_get_client.return_value = mock_client
        self.client.force_authenticate(user=self.patient_alice)

        # Attacker tries to inject 1 Rupee (100 paise)
        res = self.client.post(self.create_order_url, {
            "appointment_id": str(self.appointment.id),
            "amount": "1.00",
            "amount_paise": 100,
            "currency": "USD",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Server must ignore client input and use trusted ₹500 (50000 paise)
        called_args = mock_client.order.create.call_args[1]["data"]
        self.assertEqual(called_args["amount"], 50000)
        self.assertEqual(called_args["currency"], "INR")

    # =========================================================================
    # Test 6: Duplicate order requests do not create unintended duplicate payable records
    # =========================================================================
    @patch("apps.payments.services.get_razorpay_client")
    def test_06_duplicate_order_requests_do_not_create_unintended_duplicate_payable_records(self, mock_get_client):
        mock_client = self._mock_razorpay_client(order_id="order_idemp_06")
        mock_get_client.return_value = mock_client
        self.client.force_authenticate(user=self.patient_alice)

        # Request 1
        res1 = self.client.post(self.create_order_url, {
            "appointment_id": str(self.appointment.id),
            "idempotency_key": "idemp_key_001",
        }, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Request 2 (Duplicate retry)
        res2 = self.client.post(self.create_order_url, {
            "appointment_id": str(self.appointment.id),
            "idempotency_key": "idemp_key_001",
        }, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["order_id"], res2.data["order_id"])

        # Exactly 1 Payment record created
        self.assertEqual(Payment.objects.filter(appointment=self.appointment).count(), 1)
        # Razorpay SDK called only once
        self.assertEqual(mock_client.order.create.call_count, 1)

    # =========================================================================
    # Test 7: Valid payment signatures are accepted
    # =========================================================================
    def test_07_valid_payment_signatures_are_accepted(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_sig_07",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PENDING,
        )

        pay_id = "pay_valid_007"
        valid_sig = self._generate_valid_signature("order_sig_07", pay_id)

        self.client.force_authenticate(user=self.patient_alice)
        res = self.client.post(self.verify_url, {
            "razorpay_order_id": "order_sig_07",
            "razorpay_payment_id": pay_id,
            "razorpay_signature": valid_sig,
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], PaymentStatus.PAID)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(payment.gateway_payment_id, pay_id)
        self.assertIsNotNone(payment.paid_at)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)
        self.assertEqual(self.appointment.payment_status, PaymentStatus.PAID)

    # =========================================================================
    # Test 8: Invalid signatures are rejected
    # =========================================================================
    def test_08_invalid_signatures_are_rejected(self):
        Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_sig_08",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PENDING,
        )

        self.client.force_authenticate(user=self.patient_alice)
        res = self.client.post(self.verify_url, {
            "razorpay_order_id": "order_sig_08",
            "razorpay_payment_id": "pay_fake_008",
            "razorpay_signature": "invalid_forged_signature_hex_12345",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid payment signature", str(res.data))

        # Payment remains PENDING
        payment = Payment.objects.get(gateway_order_id="order_sig_08")
        self.assertEqual(payment.status, PaymentStatus.PENDING)

    # =========================================================================
    # Test 9: Payment/order/appointment mismatches are rejected
    # =========================================================================
    def test_09_payment_order_appointment_mismatches_are_rejected(self):
        # Non-existent order
        valid_sig = self._generate_valid_signature("order_non_existent", "pay_009")
        self.client.force_authenticate(user=self.patient_alice)

        res = self.client.post(self.verify_url, {
            "razorpay_order_id": "order_non_existent",
            "razorpay_payment_id": "pay_009",
            "razorpay_signature": valid_sig,
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Test 10: A payment is not marked successful solely from a frontend callback
    # =========================================================================
    def test_10_payment_is_not_marked_successful_solely_from_frontend_callback(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_callback_10",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PENDING,
        )

        # Attacker tries to pass success=True or forged payload without valid HMAC
        self.client.force_authenticate(user=self.patient_alice)
        res = self.client.post(self.verify_url, {
            "razorpay_order_id": "order_callback_10",
            "razorpay_payment_id": "pay_10",
            "razorpay_signature": "bogus_signature",
            "success": True,
            "status": "PAID",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PENDING)

    # =========================================================================
    # Test 11: Duplicate verification requests do not duplicate financial records
    # =========================================================================
    def test_11_duplicate_verification_requests_do_not_duplicate_financial_records(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_dup_11",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PENDING,
        )
        pay_id = "pay_dup_11"
        valid_sig = self._generate_valid_signature("order_dup_11", pay_id)

        self.client.force_authenticate(user=self.patient_alice)
        payload = {
            "razorpay_order_id": "order_dup_11",
            "razorpay_payment_id": pay_id,
            "razorpay_signature": valid_sig,
        }

        # First verification
        res1 = self.client.post(self.verify_url, payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Second verification (Duplicate retry)
        res2 = self.client.post(self.verify_url, payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Ensure exactly 1 CommissionRecord exists
        self.assertEqual(CommissionRecord.objects.filter(payment=payment).count(), 1)

    # =========================================================================
    # Test 12: Duplicate webhooks do not duplicate commission records
    # =========================================================================
    def test_12_duplicate_webhooks_do_not_duplicate_commission_records(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_webhook_12",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PENDING,
        )

        webhook_body = {
            "event_id": "evt_duplicate_test_12",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook_12",
                        "order_id": "order_webhook_12",
                        "amount": 50000,
                        "currency": "INR",
                        "status": "captured",
                    }
                }
            }
        }
        body_bytes = json.dumps(webhook_body).encode("utf-8")
        sig = self._generate_webhook_signature(body_bytes)

        # Webhook Call 1
        res1 = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Webhook Call 2 (Duplicate delivery)
        res2 = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Ensure commission record is strictly unique
        self.assertEqual(CommissionRecord.objects.filter(payment=payment).count(), 1)

    # =========================================================================
    # Test 13: Invalid webhook signatures are rejected
    # =========================================================================
    def test_13_invalid_webhook_signatures_are_rejected(self):
        body_bytes = b'{"event": "payment.captured"}'
        res = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="invalid_webhook_hmac_signature",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Test 14: Out-of-order webhook events cannot incorrectly regress payment state
    # =========================================================================
    def test_14_out_of_order_webhook_events_cannot_incorrectly_regress_payment_state(self):
        # Payment is already marked PAID
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_ooo_14",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PAID,
            paid_at=self.now_utc,
        )

        # Out-of-order delayed payment.failed event arrives
        failed_body = {
            "event_id": "evt_ooo_failed_14",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_failed_old",
                        "order_id": "order_ooo_14",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Initial card attempt failed",
                    }
                }
            }
        }
        body_bytes = json.dumps(failed_body).encode("utf-8")
        sig = self._generate_webhook_signature(body_bytes)

        res = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # State must NOT regress from PAID to FAILED
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)

    # =========================================================================
    # Test 15: Commission defaults to 5% when no clinic override exists
    # =========================================================================
    def test_15_commission_defaults_to_5_percent_when_no_clinic_override_exists(self):
        self.assertIsNone(self.clinic_a.commission_rate)
        rate, comm, clinic_share = calculate_commission(Decimal("500.00"), clinic=self.clinic_a)

        self.assertEqual(rate, Decimal("5.00"))
        self.assertEqual(comm, Decimal("25.00"))
        self.assertEqual(clinic_share, Decimal("475.00"))

    # =========================================================================
    # Test 16: Clinic-specific commission rates take precedence when configured
    # =========================================================================
    def test_16_clinic_specific_commission_rates_take_precedence_when_configured(self):
        self.assertEqual(self.clinic_b.commission_rate, Decimal("8.00"))
        rate, comm, clinic_share = calculate_commission(Decimal("1000.00"), clinic=self.clinic_b)

        self.assertEqual(rate, Decimal("8.00"))
        self.assertEqual(comm, Decimal("80.00"))
        self.assertEqual(clinic_share, Decimal("920.00"))

    # =========================================================================
    # Test 17: Commission rounding follows the documented rule
    # =========================================================================
    def test_17_commission_rounding_follows_documented_rule(self):
        # ₹333.33 at 5%: 333.33 * 0.05 = 16.6665 -> ROUND_HALF_UP => 16.67
        rate, comm, clinic_share = calculate_commission(Decimal("333.33"), custom_rate=Decimal("5.00"))
        self.assertEqual(comm, Decimal("16.67"))
        self.assertEqual(clinic_share, Decimal("316.66"))

        # ₹123.45 at 7.5%: 123.45 * 0.075 = 9.25875 -> ROUND_HALF_UP => 9.26
        rate, comm, clinic_share = calculate_commission(Decimal("123.45"), custom_rate=Decimal("7.50"))
        self.assertEqual(comm, Decimal("9.26"))
        self.assertEqual(clinic_share, Decimal("114.19"))

    # =========================================================================
    # Test 18: Gross amount equals commission plus calculated clinic share
    # =========================================================================
    def test_18_gross_amount_equals_commission_plus_calculated_clinic_share(self):
        amounts = [
            Decimal("0.00"), Decimal("1.00"), Decimal("99.99"),
            Decimal("500.00"), Decimal("1499.50"), Decimal("10000.00"),
        ]
        rates = [Decimal("0.00"), Decimal("2.50"), Decimal("5.00"), Decimal("7.33"), Decimal("100.00")]

        for amt in amounts:
            for r in rates:
                rate_snap, comm, share = calculate_commission(amt, custom_rate=r)
                self.assertEqual(amt, comm + share)

    # =========================================================================
    # Test 19: Historical commission snapshots do not change after configuration updates
    # =========================================================================
    def test_19_historical_commission_snapshots_do_not_change_after_configuration_updates(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_hist_19",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PAID,
            paid_at=self.now_utc,
        )
        rate, comm, share = calculate_commission(payment.amount, clinic=self.clinic_a)
        record = CommissionRecord.objects.create(
            payment=payment,
            appointment=self.appointment,
            clinic=self.clinic_a,
            gross_amount=payment.amount,
            commission_rate=rate,
            commission_amount=comm,
            clinic_share=share,
        )

        # Later, Super Admin updates Clinic A's commission rate to 15%
        self.clinic_a.commission_rate = Decimal("15.00")
        self.clinic_a.save()

        # Historical transaction record must remain 100% untouched
        record.refresh_from_db()
        self.assertEqual(record.commission_rate, Decimal("5.00"))
        self.assertEqual(record.commission_amount, Decimal("25.00"))
        self.assertEqual(record.clinic_share, Decimal("475.00"))

    # =========================================================================
    # Test 20: Expired reservations cannot silently become confirmed overlapping appointments
    # =========================================================================
    def test_20_expired_reservations_cannot_silently_become_confirmed_overlapping_appointments(self):
        # 1. Appointment was pending confirmation and expired 30 minutes ago
        self.appointment.status = AppointmentStatus.PENDING_CONFIRMATION
        self.appointment.reservation_expires_at = self.now_utc - timedelta(minutes=30)
        self.appointment.save()

        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_late_20",
            amount=Decimal("500.00"),
            status=PaymentStatus.PENDING,
        )

        # 2. In the meantime, another patient (Bob) booked and confirmed the exact same slot!
        bob_appointment, _ = book_appointment(
            patient=self.patient_bob,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=self.slot_time_utc,
            initial_status=AppointmentStatus.CONFIRMED,
        )
        self.assertEqual(bob_appointment.status, AppointmentStatus.CONFIRMED)

        # 3. Late payment verification arrives for Alice
        pay_id = "pay_late_20"
        sig = self._generate_valid_signature("order_late_20", pay_id)

        self.client.force_authenticate(user=self.patient_alice)
        res = self.client.post(self.verify_url, {
            "razorpay_order_id": "order_late_20",
            "razorpay_payment_id": pay_id,
            "razorpay_signature": sig,
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify Alice's appointment was NOT silently confirmed to overlap Bob's
        self.appointment.refresh_from_db()
        self.assertNotEqual(self.appointment.status, AppointmentStatus.CONFIRMED)
        self.assertTrue(self.appointment.reschedule_required)

        # Bob's appointment is still intact
        bob_appointment.refresh_from_db()
        self.assertEqual(bob_appointment.status, AppointmentStatus.CONFIRMED)

        # Alice's payment is logged with conflict note
        payment.refresh_from_db()
        self.assertTrue(payment.metadata.get("late_payment_conflict"))

    # =========================================================================
    # Test 21: Payment-pending reservations expire according to the configured policy
    # =========================================================================
    def test_21_payment_pending_reservations_expire_according_to_configured_policy(self):
        # Set reservation expired in the past
        self.appointment.status = AppointmentStatus.PENDING_CONFIRMATION
        self.appointment.reservation_expires_at = self.now_utc - timedelta(minutes=5)
        self.appointment.save()

        pending_payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_expire_21",
            amount=Decimal("500.00"),
            status=PaymentStatus.PENDING,
        )

        expired_count = expire_pending_reservations()
        self.assertGreaterEqual(expired_count, 1)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)
        self.assertIn("timed out", self.appointment.cancellation_reason)

        pending_payment.refresh_from_db()
        self.assertEqual(pending_payment.status, PaymentStatus.FAILED)
        self.assertEqual(pending_payment.failure_code, "RESERVATION_EXPIRED")

    # =========================================================================
    # Test 22: Patient payment history is private
    # =========================================================================
    def test_22_patient_payment_history_is_private(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_priv_22",
            amount=Decimal("500.00"),
            status=PaymentStatus.PAID,
        )

        status_url = reverse("api-v1:payments:appointment-status", kwargs={"appointment_id": self.appointment.id})

        # Alice (owner) can view
        self.client.force_authenticate(user=self.patient_alice)
        res_alice = self.client.get(status_url)
        self.assertEqual(res_alice.status_code, status.HTTP_200_OK)
        self.assertEqual(res_alice.data["amount"], "500.00")
        self.assertNotIn("commission", res_alice.data)

        # Bob (other patient) receives 403 Forbidden
        self.client.force_authenticate(user=self.patient_bob)
        res_bob = self.client.get(status_url)
        self.assertEqual(res_bob.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 23: Clinic owners cannot access another clinic's financial records
    # =========================================================================
    def test_23_clinic_owners_cannot_access_another_clinic_financial_records(self):
        # Clinic A has a commission record
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_fin_23",
            amount=Decimal("500.00"),
            status=PaymentStatus.PAID,
        )
        CommissionRecord.objects.create(
            payment=payment,
            appointment=self.appointment,
            clinic=self.clinic_a,
            gross_amount=Decimal("500.00"),
            commission_rate=Decimal("5.00"),
            commission_amount=Decimal("25.00"),
            clinic_share=Decimal("475.00"),
        )

        clinic_a_records_url = reverse("api-v1:payments:clinic-financial-records", kwargs={"clinic_id": self.clinic_a.id})

        # Clinic A owner can view Clinic A records
        self.client.force_authenticate(user=self.clinic_owner_a)
        res_owner_a = self.client.get(clinic_a_records_url)
        self.assertEqual(res_owner_a.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_owner_a.data["results"] if "results" in res_owner_a.data else res_owner_a.data), 1)

        # Clinic B owner cannot view Clinic A records (403 Forbidden)
        self.client.force_authenticate(user=self.clinic_owner_b)
        res_owner_b = self.client.get(clinic_a_records_url)
        self.assertEqual(res_owner_b.status_code, status.HTTP_403_FORBIDDEN)

        # Patient cannot view clinic records (403 Forbidden)
        self.client.force_authenticate(user=self.patient_alice)
        res_patient = self.client.get(clinic_a_records_url)
        self.assertEqual(res_patient.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 24: Payment failures and uncertain states are handled correctly
    # =========================================================================
    def test_24_payment_failures_and_uncertain_states_are_handled_correctly(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic_a,
            gateway_order_id="order_fail_24",
            amount=Decimal("500.00"),
            status=PaymentStatus.PENDING,
        )

        webhook_payload = {
            "event_id": "evt_fail_24",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_failed_24",
                        "order_id": "order_fail_24",
                        "error_code": "PAYMENT_DECLINED",
                        "error_description": "Card was declined by issuing bank",
                    }
                }
            }
        }
        body_bytes = json.dumps(webhook_payload).encode("utf-8")
        sig = self._generate_webhook_signature(body_bytes)

        res = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(payment.failure_code, "PAYMENT_DECLINED")
        self.assertIn("declined", payment.failure_description)

        # Commission record was NOT created on failure
        self.assertFalse(CommissionRecord.objects.filter(payment=payment).exists())

    # =========================================================================
    # Test 25: Admin can update clinic commission rate with audit log
    # =========================================================================
    def test_25_admin_can_update_clinic_commission_rate_with_audit(self):
        admin_update_url = reverse("api-v1:payments:admin-clinic-commission", kwargs={"clinic_id": self.clinic_a.id})

        # Non-admin rejected (403 Forbidden)
        self.client.force_authenticate(user=self.clinic_owner_a)
        res_forbidden = self.client.patch(admin_update_url, {"commission_rate": "7.50"}, format="json")
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Super Admin authorized
        self.client.force_authenticate(user=self.super_admin)
        res_admin = self.client.patch(admin_update_url, {"commission_rate": "7.50"}, format="json")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)

        self.clinic_a.refresh_from_db()
        self.assertEqual(self.clinic_a.commission_rate, Decimal("7.50"))

        # Commission rate out of range rejected
        res_invalid = self.client.patch(admin_update_url, {"commission_rate": "150.00"}, format="json")
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)
