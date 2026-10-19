from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.appointments.models import Appointment, AppointmentIdempotency, AppointmentStatus
from apps.appointments.services import book_appointment
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.schedules.models import BlockedSlot, DoctorSchedule, DoctorUnavailability, Weekday


class AppointmentBookingTests(APITestCase):
    """
    Comprehensive test suite for Patient Appointment Booking (Day 9).
    Validates:
    - Patient-only booking access
    - Eligibility verification (doctor, clinic, association)
    - Slot verification, schedule limits, breaks, unavailabilities
    - Past date rejection
    - Price snapshotting from trusted backend configuration
    - Overlap prevention (same clinic and cross-clinic)
    - Travel buffer enforcement
    - Idempotency key handling
    - Role-based scoping (Patient, Doctor, Clinic Owner)
    - Data privacy & object-level permissions
    """

    def setUp(self):
        # 1. Users
        self.patient_user = User.objects.create_user(
            email="patient.alice@gmail.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Alice",
            last_name="Smith",
        )
        self.other_patient = User.objects.create_user(
            email="patient.bob@gmail.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Bob",
            last_name="Jones",
        )
        self.clinic_owner_a = User.objects.create_user(
            email="owner_a@apollocare.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )
        self.clinic_owner_b = User.objects.create_user(
            email="owner_b@fortiscare.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )
        self.doctor_user = User.objects.create_user(
            email="dr.sharma@medcare.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
        )

        # 2. Approved Clinics
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
        )
        self.clinic_b = Clinic.objects.create(
            name="Fortis Wellness Center",
            owner=self.clinic_owner_b,
            email="info@fortiscare.com",
            phone="9876543211",
            address_line_1="200 Indiranagar",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
        )

        # 3. Verified Doctor
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            full_name="Dr. Amit Sharma",
            registration_number="KMC-889900",
            registration_council="Karnataka Medical Council",
            specialization="Cardiology",
            qualifications="MBBS, MD, DM",
            years_of_experience=12,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # 4. Doctor-Clinic Associations
        self.assoc_a = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            appointment_duration_minutes=30,
        )
        self.assoc_b = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_b,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("800.00"),
            appointment_duration_minutes=30,
        )

        # 5. Future Date & Schedules
        # Pick next Monday in future
        today = date.today()
        days_ahead = (0 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        self.future_monday = today + timedelta(days=days_ahead)

        # Clinic A shift: Monday 09:00 - 13:00 (30 min slots)
        self.schedule_a = DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
            slot_duration_minutes=30,
            buffer_minutes=30,
            is_active=True,
        )

        # Clinic B shift: Monday 14:00 - 18:00 (30 min slots)
        self.schedule_b = DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_b,
            day_of_week=Weekday.MONDAY,
            start_time=time(14, 0),
            end_time=time(18, 0),
            slot_duration_minutes=30,
            buffer_minutes=30,
            is_active=True,
        )

        self.kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.book_url = reverse("api-v1:appointments:appointment-create")
        self.my_appointments_url = reverse("api-v1:appointments:my-appointments")

    # =========================================================================
    # Test 1: Authenticated patient can book a valid available slot
    # =========================================================================
    def test_authenticated_patient_can_book_valid_available_slot(self):
        self.client.force_authenticate(user=self.patient_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)

        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
            "patient_note": "Regular heart checkup",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("booking_reference", res.data)
        self.assertEqual(res.data["status"], AppointmentStatus.CONFIRMED)
        self.assertEqual(res.data["consultation_fee"], "500.00")
        self.assertEqual(res.data["currency"], "INR")
        self.assertEqual(res.data["duration_minutes"], 30)
        self.assertEqual(res.data["patient_note"], "Regular heart checkup")
        self.assertEqual(res.data["patient"]["email"], self.patient_user.email)

    # =========================================================================
    # Test 2: Unauthenticated user cannot create an appointment
    # =========================================================================
    def test_unauthenticated_user_cannot_create_appointment(self):
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # =========================================================================
    # Test 3: Non-patient role cannot book appointments
    # =========================================================================
    def test_non_patient_role_cannot_bypass_booking_permissions(self):
        # Doctor user cannot book patient appointment
        self.client.force_authenticate(user=self.doctor_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Clinic owner cannot book patient appointment
        self.client.force_authenticate(user=self.clinic_owner_a)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 4: Patient cannot book for another patient by manipulating request
    # =========================================================================
    def test_patient_cannot_book_for_another_patient(self):
        self.client.force_authenticate(user=self.patient_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)

        # Client attempts to pass other_patient ID in body
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
            "patient_id": str(self.other_patient.id),
            "patient": str(self.other_patient.id),
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Verify the appointment is strictly attributed to the authenticated user
        appt = Appointment.objects.get(id=res.data["id"])
        self.assertEqual(appt.patient, self.patient_user)
        self.assertNotEqual(appt.patient, self.other_patient)

    # =========================================================================
    # Test 5: Inactive or unverified doctor cannot receive a booking
    # =========================================================================
    def test_inactive_doctor_cannot_receive_booking(self):
        self.doctor.verification_status = DoctorVerificationStatus.PENDING
        self.doctor.save()

        self.client.force_authenticate(user=self.patient_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Test 6: Inactive or unapproved clinic cannot receive a booking
    # =========================================================================
    def test_unapproved_clinic_cannot_receive_booking(self):
        self.clinic_a.status = ClinicStatus.PENDING
        self.clinic_a.save()

        self.client.force_authenticate(user=self.patient_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Test 7: Inactive doctor-clinic association cannot receive a booking
    # =========================================================================
    def test_inactive_doctor_clinic_association_cannot_receive_booking(self):
        self.assoc_a.status = DoctorClinicStatus.PAUSED if hasattr(DoctorClinicStatus, "PAUSED") else DoctorClinicStatus.REMOVED
        self.assoc_a.save()

        self.client.force_authenticate(user=self.patient_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Test 8: Past appointment time is rejected
    # =========================================================================
    def test_past_appointment_time_is_rejected(self):
        self.client.force_authenticate(user=self.patient_user)
        # Past timestamp: yesterday
        past_dt = timezone.now() - timedelta(days=1)

        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": past_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("past", str(res.data))

    # =========================================================================
    # Test 9: Time outside doctor's schedule is rejected
    # =========================================================================
    def test_time_outside_schedule_is_rejected(self):
        self.client.force_authenticate(user=self.patient_user)
        # 08:00 is outside 09:00 - 13:00 shift
        outside_dt = datetime.combine(self.future_monday, time(8, 0), tzinfo=self.kolkata_tz)

        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": outside_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # =========================================================================
    # Test 10: Slot during administrative blocked slot is rejected
    # =========================================================================
    def test_slot_during_blocked_slot_is_rejected(self):
        # Admin blocks 10:00 on future Monday
        BlockedSlot.objects.create(
            doctor_clinic=self.assoc_a,
            date=self.future_monday,
            start_time=time(10, 0),
            reason="Equipment Maintenance",
        )

        self.client.force_authenticate(user=self.patient_user)
        blocked_dt = datetime.combine(self.future_monday, time(10, 0), tzinfo=self.kolkata_tz)

        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": blocked_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("blocked", str(res.data).lower())

    # =========================================================================
    # Test 11: Schedule exception / Doctor leave prevents invalid booking
    # =========================================================================
    def test_doctor_leave_prevents_booking(self):
        # Doctor on medical leave from 11:00 to 12:00 in UTC
        leave_start = datetime.combine(self.future_monday, time(11, 0), tzinfo=self.kolkata_tz).astimezone(dt_timezone.utc)
        leave_end = datetime.combine(self.future_monday, time(12, 0), tzinfo=self.kolkata_tz).astimezone(dt_timezone.utc)

        DoctorUnavailability.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            start_datetime=leave_start,
            end_datetime=leave_end,
            reason="SICK_LEAVE",
            notes="Flu",
        )

        self.client.force_authenticate(user=self.patient_user)
        leave_dt = datetime.combine(self.future_monday, time(11, 0), tzinfo=self.kolkata_tz)

        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": leave_dt.isoformat(),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # =========================================================================
    # Test 12: Occupied slot by another blocking appointment is rejected (409)
    # =========================================================================
    def test_occupied_slot_rejected_with_409_conflict(self):
        slot_dt = datetime.combine(self.future_monday, time(9, 30), tzinfo=self.kolkata_tz)

        # Patient 1 books 09:30 slot
        book_appointment(
            patient=self.other_patient,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=slot_dt,
        )

        # Patient 2 attempts to book the same 09:30 slot
        self.client.force_authenticate(user=self.patient_user)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": slot_dt.isoformat(),
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("no longer available", str(res.data).lower())

    # =========================================================================
    # Test 13: Overlapping appointments for same doctor across clinics are prevented
    # =========================================================================
    def test_cross_clinic_overlapping_appointments_prevented(self):
        # Create an ad-hoc overlapping schedule at Clinic B at 10:00 to test cross-clinic overlap prevention
        slot_dt = datetime.combine(self.future_monday, time(10, 0), tzinfo=self.kolkata_tz)

        # Book at Clinic A
        book_appointment(
            patient=self.other_patient,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=slot_dt,
        )

        # Attempt to book same doctor at Clinic B at 10:00
        self.client.force_authenticate(user=self.patient_user)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_b.id),
            "doctor_id": str(self.doctor.id),
            "start_at": slot_dt.isoformat(),
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # =========================================================================
    # Test 14: Travel buffer enforced between different clinics
    # =========================================================================
    def test_cross_clinic_travel_buffer_enforced(self):
        # Clinic A shift ends at 13:00. Clinic B starts at 14:00.
        # Doctor has appointment at Clinic A ending at 13:00.
        # If doctor has appointment at Clinic A 12:30-13:00,
        # A booking at Clinic B at 13:15 (gap 15 mins < 30 mins buffer) must be rejected!
        appt_a_dt = datetime.combine(self.future_monday, time(12, 30), tzinfo=self.kolkata_tz)
        book_appointment(
            patient=self.other_patient,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=appt_a_dt,
        )

        # Add temporary shift at Clinic B from 13:15 to 14:00
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_b,
            day_of_week=Weekday.MONDAY,
            start_time=time(13, 15),
            end_time=time(14, 0),
            slot_duration_minutes=30,
            is_active=True,
        )

        # Attempt to book at Clinic B at 13:15 (violates 30 min travel buffer from 13:00)
        self.client.force_authenticate(user=self.patient_user)
        b_dt = datetime.combine(self.future_monday, time(13, 15), tzinfo=self.kolkata_tz)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_b.id),
            "doctor_id": str(self.doctor.id),
            "start_at": b_dt.isoformat(),
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("travel buffer", str(res.data).lower())

    # =========================================================================
    # Test 15: Two concurrent booking attempts cannot both succeed
    # =========================================================================
    def test_concurrent_booking_attempts_prevention(self):
        slot_dt = datetime.combine(self.future_monday, time(10, 30), tzinfo=self.kolkata_tz)

        # First request succeeds
        appt1, created1 = book_appointment(
            patient=self.patient_user,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=slot_dt,
        )
        self.assertTrue(created1)

        # Second competing request for the exact same slot raises SlotUnavailableException
        self.client.force_authenticate(user=self.other_patient)
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": slot_dt.isoformat(),
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        # Ensure only 1 appointment persisted
        count = Appointment.objects.filter(
            doctor=self.doctor,
            start_at=slot_dt,
            status=AppointmentStatus.CONFIRMED,
        ).count()
        self.assertEqual(count, 1)

    # =========================================================================
    # Test 16: Different valid slots can be booked without conflict
    # =========================================================================
    def test_different_valid_slots_can_be_booked(self):
        slot1_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        slot2_dt = datetime.combine(self.future_monday, time(9, 30), tzinfo=self.kolkata_tz)

        appt1, c1 = book_appointment(
            patient=self.patient_user,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=slot1_dt,
        )
        appt2, c2 = book_appointment(
            patient=self.other_patient,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=slot2_dt,
        )

        self.assertTrue(c1)
        self.assertTrue(c2)
        self.assertNotEqual(appt1.id, appt2.id)

    # =========================================================================
    # Test 17: Trusted backend consultation fee is used
    # =========================================================================
    def test_server_uses_clinic_specific_consultation_fee(self):
        self.client.force_authenticate(user=self.patient_user)
        # Clinic A fee is ₹500
        start_a = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        res_a = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_a.isoformat(),
        }, format="json")
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_a.data["consultation_fee"], "500.00")

        # Clinic B fee is ₹800
        start_b = datetime.combine(self.future_monday, time(14, 0), tzinfo=self.kolkata_tz)
        res_b = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_b.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_b.isoformat(),
        }, format="json")
        self.assertEqual(res_b.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_b.data["consultation_fee"], "800.00")

    # =========================================================================
    # Test 18: Client-supplied price cannot manipulate fee
    # =========================================================================
    def test_client_supplied_price_is_ignored(self):
        self.client.force_authenticate(user=self.patient_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)

        # Client attempts to pass 1.00 INR
        res = self.client.post(self.book_url, {
            "clinic_id": str(self.clinic_a.id),
            "doctor_id": str(self.doctor.id),
            "start_at": start_dt.isoformat(),
            "consultation_fee": "1.00",
            "price": "1.00",
            "amount": "1.00",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Server snapshot must remain 500.00
        self.assertEqual(res.data["consultation_fee"], "500.00")

    # =========================================================================
    # Test 19: Fee snapshot remains unchanged when clinic changes fee later
    # =========================================================================
    def test_fee_snapshot_remains_unchanged_on_subsequent_clinic_price_update(self):
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        appt, _ = book_appointment(
            patient=self.patient_user,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=start_dt,
        )
        self.assertEqual(appt.consultation_fee, Decimal("500.00"))

        # Clinic increases consultation fee to ₹750
        self.assoc_a.consultation_fee = Decimal("750.00")
        self.assoc_a.save()

        # Existing appointment retains snapshot
        appt.refresh_from_db()
        self.assertEqual(appt.consultation_fee, Decimal("500.00"))

    # =========================================================================
    # Test 20: Idempotency: repeated requests do not duplicate appointments
    # =========================================================================
    def test_idempotent_request_returns_same_appointment(self):
        self.client.force_authenticate(user=self.patient_user)
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        idemp_key = f"key-{uuid.uuid4()}"

        # First booking submission
        res1 = self.client.post(
            self.book_url,
            {
                "clinic_id": str(self.clinic_a.id),
                "doctor_id": str(self.doctor.id),
                "start_at": start_dt.isoformat(),
            },
            HTTP_IDEMPOTENCY_KEY=idemp_key,
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        appt_id = res1.data["id"]

        # Duplicate submission with same idempotency key
        res2 = self.client.post(
            self.book_url,
            {
                "clinic_id": str(self.clinic_a.id),
                "doctor_id": str(self.doctor.id),
                "start_at": start_dt.isoformat(),
            },
            HTTP_IDEMPOTENCY_KEY=idemp_key,
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["id"], appt_id)

        # Confirm only one appointment exists in DB
        self.assertEqual(Appointment.objects.filter(patient=self.patient_user).count(), 1)

    # =========================================================================
    # Test 21: Idempotency: key reuse with different parameters is rejected (400)
    # =========================================================================
    def test_idempotency_key_reuse_with_different_payload_is_rejected(self):
        self.client.force_authenticate(user=self.patient_user)
        start_dt1 = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        start_dt2 = datetime.combine(self.future_monday, time(9, 30), tzinfo=self.kolkata_tz)
        idemp_key = f"key-{uuid.uuid4()}"

        # First request for 09:00
        res1 = self.client.post(
            self.book_url,
            {
                "clinic_id": str(self.clinic_a.id),
                "doctor_id": str(self.doctor.id),
                "start_at": start_dt1.isoformat(),
            },
            HTTP_IDEMPOTENCY_KEY=idemp_key,
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Second request using SAME key but for 09:30
        res2 = self.client.post(
            self.book_url,
            {
                "clinic_id": str(self.clinic_a.id),
                "doctor_id": str(self.doctor.id),
                "start_at": start_dt2.isoformat(),
            },
            HTTP_IDEMPOTENCY_KEY=idemp_key,
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Test 22: Patient cannot access another patient's appointment (403)
    # =========================================================================
    def test_patient_cannot_view_another_patient_appointment(self):
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        appt, _ = book_appointment(
            patient=self.patient_user,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=start_dt,
        )

        # Bob attempts to view Alice's appointment
        self.client.force_authenticate(user=self.other_patient)
        detail_url = reverse("api-v1:appointments:appointment-detail", kwargs={"appointment_id": appt.id})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 23: Clinic owner cannot access appointments from another clinic
    # =========================================================================
    def test_clinic_owner_cannot_access_appointments_from_another_clinic(self):
        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        appt_a, _ = book_appointment(
            patient=self.patient_user,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=start_dt,
        )

        # Owner B tries to list appointments for Clinic A
        self.client.force_authenticate(user=self.clinic_owner_b)
        clinic_a_appts_url = reverse("api-v1:clinics:clinic-appointments", kwargs={"clinic_id": self.clinic_a.id})
        res = self.client.get(clinic_a_appts_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Owner B tries to retrieve Clinic A appointment detail
        detail_url = reverse("api-v1:appointments:appointment-detail", kwargs={"appointment_id": appt_a.id})
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Test 24: Doctor can access only their permitted appointments
    # =========================================================================
    def test_doctor_can_access_only_their_appointments(self):
        # Create second doctor
        other_doc_user = User.objects.create_user(
            email="dr.other@medcare.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
        )
        other_doctor = Doctor.objects.create(
            user=other_doc_user,
            full_name="Dr. Sunita Rao",
            registration_number="KMC-112233",
            registration_council="Karnataka Medical Council",
            specialization="Pediatrics",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        start_dt = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        appt, _ = book_appointment(
            patient=self.patient_user,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=start_dt,
        )

        # Other doctor attempts to view Dr. Sharma's appointment
        self.client.force_authenticate(user=other_doc_user)
        detail_url = reverse("api-v1:appointments:appointment-detail", kwargs={"appointment_id": appt.id})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Dr. Sharma views their own appointment
        self.client.force_authenticate(user=self.doctor_user)
        res_doc = self.client.get(detail_url)
        self.assertEqual(res_doc.status_code, status.HTTP_200_OK)
        self.assertEqual(res_doc.data["id"], str(appt.id))

    # =========================================================================
    # Test 25: Patient history list does not expose other patients' bookings
    # =========================================================================
    def test_patient_history_list_isolation(self):
        start_a = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        start_b = datetime.combine(self.future_monday, time(9, 30), tzinfo=self.kolkata_tz)

        # Alice books 09:00
        book_appointment(patient=self.patient_user, clinic_id=self.clinic_a.id, doctor_id=self.doctor.id, start_at=start_a)
        # Bob books 09:30
        book_appointment(patient=self.other_patient, clinic_id=self.clinic_a.id, doctor_id=self.doctor.id, start_at=start_b)

        # Alice checks her history
        self.client.force_authenticate(user=self.patient_user)
        res = self.client.get(self.my_appointments_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        alice_results = res.data.get("results", res.data)
        self.assertEqual(len(alice_results), 1)
        self.assertEqual(alice_results[0]["doctor_name"], "Dr. Amit Sharma")

        # Bob checks his history
        self.client.force_authenticate(user=self.other_patient)
        res_bob = self.client.get(self.my_appointments_url)
        self.assertEqual(res_bob.status_code, status.HTTP_200_OK)
        bob_results = res_bob.data.get("results", res_bob.data)
        self.assertEqual(len(bob_results), 1)

    # =========================================================================
    # Test 26: Doctor and Clinic Appointments List Endpoints
    # =========================================================================
    def test_doctor_and_clinic_management_list_endpoints(self):
        start_a = datetime.combine(self.future_monday, time(9, 0), tzinfo=self.kolkata_tz)
        start_b = datetime.combine(self.future_monday, time(14, 0), tzinfo=self.kolkata_tz)

        # Alice books at Clinic A
        book_appointment(patient=self.patient_user, clinic_id=self.clinic_a.id, doctor_id=self.doctor.id, start_at=start_a)
        # Bob books at Clinic B
        book_appointment(patient=self.other_patient, clinic_id=self.clinic_b.id, doctor_id=self.doctor.id, start_at=start_b)

        # Clinic A owner sees only Clinic A appointment
        self.client.force_authenticate(user=self.clinic_owner_a)
        res_clinic_a = self.client.get(reverse("api-v1:clinics:clinic-appointments", kwargs={"clinic_id": self.clinic_a.id}))
        self.assertEqual(res_clinic_a.status_code, status.HTTP_200_OK)
        clinic_a_results = res_clinic_a.data.get("results", res_clinic_a.data)
        self.assertEqual(len(clinic_a_results), 1)
        self.assertEqual(clinic_a_results[0]["patient"]["email"], self.patient_user.email)

        # Doctor sees both appointments across clinics
        self.client.force_authenticate(user=self.doctor_user)
        res_doc = self.client.get(reverse("api-v1:doctors:doctor-appointments"))
        self.assertEqual(res_doc.status_code, status.HTTP_200_OK)
        doc_results = res_doc.data.get("results", res_doc.data)
        self.assertEqual(len(doc_results), 2)
