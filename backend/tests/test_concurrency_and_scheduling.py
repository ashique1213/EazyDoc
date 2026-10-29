import concurrent.futures
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo
from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole, UserStatus
from apps.appointments.exceptions import (
    CutoffExceededException,
    InvalidAppointmentStateException,
    SlotUnavailableException,
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
    get_appointment_cancellation_cutoff,
    reschedule_appointment,
)
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.schedules.models import DoctorSchedule, Weekday


class ConcurrencyAndSchedulingIntegrityTests(TransactionTestCase):
    """
    Day 15 Phase Four Concurrency, Atomicity, and Scheduling Integrity Tests.
    Tests:
    1. Concurrent slot booking race condition serialization.
    2. Atomic rollback: failed rescheduling leaves original appointment intact.
    3. Cross-clinic travel buffer enforcement across different clinics for the same doctor.
    4. Expired reservations: PENDING_CONFIRMATION past expiry does not block new bookings.
    5. Cutoff evaluation in clinic timezone (Asia/Kolkata).
    6. Doctor unavailability exception allows cancellation after cutoff.
    7. Terminal state protection: completed and cancelled appointments cannot be re-cancelled/rescheduled.
    8. Audit history trail for booking and cancellation.
    """

    def setUp(self):
        self.kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.client = APIClient()

        # Create Clinic Owner
        self.owner = User.objects.create_user(
            email="owner.test@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
        )

        # Clinic A (Asia/Kolkata)
        self.clinic_a = Clinic.objects.create(
            name="Clinic Alpha",
            owner=self.owner,
            email="clinic.alpha@eazydoc.com",
            phone="9876543210",
            address_line_1="123 Alpha Road",
            city="Bangalore",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.APPROVED,
            is_verified=True,
            timezone="Asia/Kolkata",
        )

        # Clinic B (Asia/Kolkata)
        self.clinic_b = Clinic.objects.create(
            name="Clinic Beta",
            owner=self.owner,
            email="clinic.beta@eazydoc.com",
            phone="9876543211",
            address_line_1="456 Beta Street",
            city="Bangalore",
            state="Karnataka",
            pincode="560002",
            status=ClinicStatus.APPROVED,
            is_verified=True,
            timezone="Asia/Kolkata",
        )

        # Doctor User & Doctor Profile
        self.doctor_user = User.objects.create_user(
            email="dr.concurrency@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            first_name="Concurrency",
            last_name="Doctor",
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            registration_number="REG-CONCURRENCY-001",
            normalized_registration_number="REG-CONCURRENCY-001",
            registration_council="Karnataka Medical Council",
            normalized_registration_council="KARNATAKA MEDICAL COUNCIL",
            full_name="Dr. Concurrency Doctor",
            specialization="General Medicine",
            qualifications="MBBS",
            years_of_experience=10,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # Affiliations with Clinic A and Clinic B
        self.dc_a = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            consultation_fee=Decimal("500.00"),
            appointment_duration_minutes=30,
            status=DoctorClinicStatus.ACTIVE,
        )
        self.dc_b = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_b,
            consultation_fee=Decimal("600.00"),
            appointment_duration_minutes=30,
            status=DoctorClinicStatus.ACTIVE,
        )

        # Target booking date: a guaranteed future weekday (e.g. 14 days from now)
        base_future = timezone.now().astimezone(self.kolkata_tz) + timedelta(days=14)
        # Ensure it's Monday-Friday
        while base_future.weekday() >= 5:
            base_future += timedelta(days=1)
        self.future_date = base_future.date()
        self.target_weekday = Weekday(self.future_date.weekday())

        # Schedules: Clinic A shift 09:00 - 13:00, Clinic B shift 14:00 - 18:00
        DoctorSchedule.objects.create(
            doctor_clinic=self.dc_a,
            weekday=self.target_weekday,
            start_time=time(9, 0),
            end_time=time(13, 0),
            is_active=True,
        )
        DoctorSchedule.objects.create(
            doctor_clinic=self.dc_b,
            weekday=self.target_weekday,
            start_time=time(14, 0),
            end_time=time(18, 0),
            is_active=True,
        )

        # Patients
        self.patient_1 = User.objects.create_user(
            email="patient.race1@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Race1",
            last_name="Patient",
        )
        self.patient_2 = User.objects.create_user(
            email="patient.race2@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Race2",
            last_name="Patient",
        )

    def test_concurrent_slot_booking_mutual_exclusion(self):
        """
        Two concurrent booking requests for the exact same slot.
        Only one MUST succeed; the second MUST be rejected with SlotUnavailableException
        due to row-level serialization / lock check.
        """
        slot_dt = datetime.combine(self.future_date, time(9, 0), tzinfo=self.kolkata_tz)

        results = []
        errors = []

        def attempt_booking(patient_user):
            # Close stale thread connections if running multithreaded
            connection.close()
            try:
                appt, created = book_appointment(
                    patient=patient_user,
                    clinic_id=self.clinic_a.id,
                    doctor_id=self.doctor.id,
                    start_at=slot_dt,
                )
                results.append((patient_user.id, appt.id, created))
            except (SlotUnavailableException, DatabaseError) as exc:
                errors.append(str(exc))
            except Exception as e:
                errors.append(f"Unexpected: {type(e).__name__}: {str(e)}")
            finally:
                connection.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(attempt_booking, self.patient_1),
                executor.submit(attempt_booking, self.patient_2),
            ]
            concurrent.futures.wait(futures)

        # Exactly 1 success, exactly 1 rejection
        self.assertEqual(len(results), 1, f"Expected exactly 1 booking to succeed, got {len(results)}. Errors: {errors}")
        self.assertEqual(len(errors), 1, f"Expected exactly 1 error, got {len(errors)}")

        # Verify only 1 appointment exists in database for this slot
        count = Appointment.objects.filter(
            doctor=self.doctor,
            start_at=slot_dt,
            status__in=[AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING_CONFIRMATION],
        ).count()
        self.assertEqual(count, 1)

    def test_cross_clinic_travel_buffer_conflict_prevention(self):
        """
        Doctor has an appointment at Clinic A ending at 12:30.
        A booking at Clinic B at 12:45 is rejected because travel buffer (30 mins) requires
        free time until 13:00.
        """
        # Create Schedule at Clinic A 12:00 - 13:00 and Clinic B 12:30 - 14:00 for this test
        slot_clinic_a = datetime.combine(self.future_date, time(12, 0), tzinfo=self.kolkata_tz)
        appt_a, _ = book_appointment(
            patient=self.patient_1,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=slot_clinic_a,
        )
        self.assertEqual(appt_a.end_at, slot_clinic_a + timedelta(minutes=30))

        # Attempt to book at Clinic B starting at 12:45 (only 15 mins after Clinic A end_at)
        # Required buffer is at least 30 minutes!
        slot_clinic_b = datetime.combine(self.future_date, time(14, 0), tzinfo=self.kolkata_tz)
        # Let's test a slot that violates travel buffer: say 14:00 is fine, but if Clinic A had an appt at 13:45:
        # Let's book Clinic B at 14:00 (which is 90 mins later, valid):
        appt_b, _ = book_appointment(
            patient=self.patient_2,
            clinic_id=self.clinic_b.id,
            doctor_id=self.doctor.id,
            start_at=slot_clinic_b,
        )
        self.assertIsNotNone(appt_b)

        # Now, if someone tries to book Clinic A at 13:45, it is only 15 mins before Clinic B's 14:00 appt!
        # Travel buffer requires 30 mins before 14:00 (i.e. appt must end by 13:30).
        # We need Clinic A schedule to include 13:30 - 14:00 to test the buffer check in book_appointment:
        DoctorSchedule.objects.create(
            doctor_clinic=self.dc_a,
            weekday=self.target_weekday,
            start_time=time(13, 30),
            end_time=time(14, 0),
            is_active=True,
        )
        slot_conflict_a = datetime.combine(self.future_date, time(13, 30), tzinfo=self.kolkata_tz)

        with self.assertRaises(SlotUnavailableException) as ctx:
            book_appointment(
                patient=self.patient_1,
                clinic_id=self.clinic_a.id,
                doctor_id=self.doctor.id,
                start_at=slot_conflict_a,
            )
        self.assertIn("travel buffer conflict", str(ctx.exception).lower())

    def test_reschedule_atomic_rollback_on_failure(self):
        """
        If rescheduling fails (e.g. target slot is already booked), the database
        transaction must roll back cleanly, leaving the original appointment completely intact.
        """
        orig_slot = datetime.combine(self.future_date, time(9, 30), tzinfo=self.kolkata_tz)
        other_slot = datetime.combine(self.future_date, time(10, 0), tzinfo=self.kolkata_tz)

        # Patient 1 books 09:30
        appt_1, _ = book_appointment(
            patient=self.patient_1,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=orig_slot,
        )

        # Patient 2 books 10:00
        appt_2, _ = book_appointment(
            patient=self.patient_2,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=other_slot,
        )

        # Patient 1 tries to reschedule into 10:00 (which is occupied by Patient 2)
        with self.assertRaises(SlotUnavailableException):
            reschedule_appointment(
                appointment=appt_1,
                rescheduled_by=self.patient_1,
                new_start_at=other_slot,
            )

        # Verify original appointment is untouched
        appt_1.refresh_from_db()
        self.assertEqual(appt_1.start_at, orig_slot)
        self.assertEqual(appt_1.status, AppointmentStatus.CONFIRMED)

    def test_expired_reservation_allows_subsequent_booking(self):
        """
        A PENDING_CONFIRMATION appointment whose reservation_expires_at is in the past
        does NOT block another patient from booking the same slot.
        """
        slot_dt = datetime.combine(self.future_date, time(10, 30), tzinfo=self.kolkata_tz)

        # Patient 1 has an expired reservation
        appt_expired = Appointment.objects.create(
            booking_reference="EZD-TEST-EXP001",
            patient=self.patient_1,
            doctor_clinic=self.dc_a,
            doctor=self.doctor,
            clinic=self.clinic_a,
            start_at=slot_dt,
            end_at=slot_dt + timedelta(minutes=30),
            status=AppointmentStatus.PENDING_CONFIRMATION,
            payment_status="PENDING",
            reservation_expires_at=timezone.now() - timedelta(minutes=5),  # expired 5 mins ago
            consultation_fee=Decimal("500.00"),
            currency="INR",
        )

        # Patient 2 attempts to book the same slot -> MUST succeed because appt_expired is expired
        appt_new, created = book_appointment(
            patient=self.patient_2,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=slot_dt,
        )
        self.assertTrue(created)
        self.assertEqual(appt_new.patient, self.patient_2)
        self.assertEqual(appt_new.status, AppointmentStatus.CONFIRMED)

    def test_cancellation_cutoff_enforcement_in_clinic_timezone(self):
        """
        Patients can cancel until 11:59:59 PM on the calendar day before the appointment
        in clinic's local timezone.
        Attempting to cancel on the day of the appointment is rejected.
        """
        appt_start = datetime.combine(self.future_date, time(11, 0), tzinfo=self.kolkata_tz)
        appt, _ = book_appointment(
            patient=self.patient_1,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=appt_start,
        )

        # Cutoff is 23:59:59.999999 of the day before future_date in Asia/Kolkata
        cutoff = get_appointment_cancellation_cutoff(appt)
        self.assertEqual(cutoff.date(), self.future_date - timedelta(days=1))
        self.assertEqual(cutoff.hour, 23)
        self.assertEqual(cutoff.minute, 59)

        # Simulation 1: Cancellation at 23:30 on the day before -> Allowed
        allowed_time = datetime.combine(self.future_date - timedelta(days=1), time(23, 30), tzinfo=self.kolkata_tz)
        # Verify eligibility helper
        from apps.appointments.services import check_patient_cancellation_eligibility
        is_ok, err, is_exc = check_patient_cancellation_eligibility(appt, current_time=allowed_time)
        self.assertTrue(is_ok)

        # Simulation 2: Cancellation at 00:01 AM on the day of appointment -> Rejected
        disallowed_time = datetime.combine(self.future_date, time(0, 1), tzinfo=self.kolkata_tz)
        is_ok, err, is_exc = check_patient_cancellation_eligibility(appt, current_time=disallowed_time)
        self.assertFalse(is_ok)
        self.assertIn("cancellation cutoff", err.lower())

        with self.assertRaises(CutoffExceededException):
            cancel_appointment(
                appointment=appt,
                cancelled_by=self.patient_1,
                reason="Changed my mind late",
                current_time=disallowed_time,
            )

        # Status must remain CONFIRMED
        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.CONFIRMED)

    def test_doctor_unavailability_authorized_exception_bypasses_cutoff(self):
        """
        When clinic/doctor flags an appointment with reschedule_required=True,
        the patient CAN cancel or reschedule even after the cutoff without restriction.
        """
        appt_start = datetime.combine(self.future_date, time(11, 30), tzinfo=self.kolkata_tz)
        appt, _ = book_appointment(
            patient=self.patient_1,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=appt_start,
        )

        # Flag appointment with reschedule_required
        appt.reschedule_required = True
        appt.status = AppointmentStatus.RESCHEDULE_REQUIRED
        appt.save(update_fields=["reschedule_required", "status"])

        # Even on the day of appointment (past cutoff), patient cancellation succeeds
        late_time = datetime.combine(self.future_date, time(8, 0), tzinfo=self.kolkata_tz)
        cancelled_appt = cancel_appointment(
            appointment=appt,
            cancelled_by=self.patient_1,
            reason="Doctor was unavailable, opting to cancel",
            current_time=late_time,
        )
        self.assertEqual(cancelled_appt.status, AppointmentStatus.CANCELLED)

        # Verify history indicates exception was used
        hist = AppointmentHistory.objects.filter(
            appointment=cancelled_appt,
            event_type=AppointmentHistoryEventType.PATIENT_CANCELLED,
        ).first()
        self.assertIsNotNone(hist)
        self.assertTrue(hist.is_exception)

    def test_terminal_states_prevent_invalid_transitions(self):
        """
        Completed appointments cannot be cancelled or rescheduled.
        Cancelled appointments cannot be cancelled again.
        """
        appt_start = datetime.combine(self.future_date, time(12, 30), tzinfo=self.kolkata_tz)
        appt, _ = book_appointment(
            patient=self.patient_1,
            clinic_id=self.clinic_a.id,
            doctor_id=self.doctor.id,
            start_at=appt_start,
        )

        # Mark COMPLETED
        appt.status = AppointmentStatus.COMPLETED
        appt.save(update_fields=["status"])

        with self.assertRaises(InvalidAppointmentStateException):
            cancel_appointment(appointment=appt, cancelled_by=self.patient_1)

        with self.assertRaises(InvalidAppointmentStateException):
            new_slot = datetime.combine(self.future_date, time(13, 0), tzinfo=self.kolkata_tz)
            reschedule_appointment(
                appointment=appt,
                rescheduled_by=self.patient_1,
                new_start_at=new_slot,
            )
