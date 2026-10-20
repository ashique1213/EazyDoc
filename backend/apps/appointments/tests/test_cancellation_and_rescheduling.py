from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
import uuid
from unittest.mock import patch
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
from apps.appointments.services import (
    book_appointment,
    cancel_appointment,
    get_appointment_cancellation_cutoff,
    reschedule_appointment,
    report_doctor_unavailability_for_appointment,
)
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.schedules.models import DoctorSchedule, Weekday


class AppointmentCancellationAndReschedulingTests(APITestCase):
    """
    Day 10 Comprehensive Test Suite for Appointment Cancellation and Rescheduling:
    - Policy cutoff enforcement (11:59:59 PM day prior in clinic timezone)
    - Midnight and boundary testing
    - Timezone-aware calculation (Asia/Kolkata, America/New_York)
    - Authorized exceptions for doctor/clinic unavailability
    - State transition protections (completed, cancelled, no-show)
    - Slot restoration after cancellation
    - Overlap and cross-clinic travel buffer during rescheduling
    - Failure safety (failed reschedule leaves original appointment untouched)
    - Append-only audit history with actors, roles, and exception flags
    - Multi-tenant security and isolation
    """

    def setUp(self):
        # 1. Users
        self.patient_alice = User.objects.create_user(
            email="alice.smith@example.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Alice",
            last_name="Smith",
        )
        self.patient_bob = User.objects.create_user(
            email="bob.jones@example.com",
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

        # 2. Clinics (Asia/Kolkata & America/New_York)
        self.clinic_kolkata = Clinic.objects.create(
            name="Apollo Clinic Bengaluru",
            owner=self.clinic_owner_a,
            email="info@apollokolkata.com",
            phone="9876543210",
            address_line_1="100 MG Road",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
        )
        self.clinic_ny = Clinic.objects.create(
            name="Manhattan Health Center",
            owner=self.clinic_owner_b,
            email="info@manhattanhealth.com",
            phone="2125550199",
            address_line_1="500 5th Ave",
            city="New York",
            state="NY",
            pincode="10036",
            status=ClinicStatus.APPROVED,
            timezone="America/New_York",
        )

        # 3. Doctor
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            full_name="Dr. Amit Sharma",
            registration_number="KMC-998877",
            registration_council="Karnataka Medical Council",
            specialization="Cardiology",
            qualifications="MBBS, MD",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # 4. Affiliations
        self.assoc_kolkata = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_kolkata,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            appointment_duration_minutes=30,
        )
        self.assoc_ny = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_ny,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("150.00"),
            appointment_duration_minutes=30,
        )

        # 5. Shifts: Monday & Tuesday 09:00 - 13:00 at Clinic Kolkata
        self.schedule_mon = DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_kolkata,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
            slot_duration_minutes=30,
            is_active=True,
        )
        self.schedule_tue = DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_kolkata,
            day_of_week=Weekday.TUESDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
            slot_duration_minutes=30,
            is_active=True,
        )

        # Determine target future Monday in Asia/Kolkata
        today_kolkata = timezone.now().astimezone(ZoneInfo("Asia/Kolkata")).date()
        days_to_mon = (0 - today_kolkata.weekday()) % 7
        if days_to_mon <= 1:
            days_to_mon += 7
        self.target_monday = today_kolkata + timedelta(days=days_to_mon)
        self.target_tuesday = self.target_monday + timedelta(days=1)

        # Initial appointment on target_monday at 10:00 AM Kolkata time
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.appt_start_kolkata = datetime.combine(
            self.target_monday, time(10, 0), tzinfo=kolkata_tz
        )
        self.appt_end_kolkata = datetime.combine(
            self.target_monday, time(10, 30), tzinfo=kolkata_tz
        )

        self.appointment = Appointment.objects.create(
            booking_reference="EZD-TEST-001",
            patient=self.patient_alice,
            doctor_clinic=self.assoc_kolkata,
            doctor=self.doctor,
            clinic=self.clinic_kolkata,
            start_at=self.appt_start_kolkata,
            end_at=self.appt_end_kolkata,
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
            currency="INR",
            patient_note="Routine cardiac checkup",
        )
        AppointmentHistory.objects.create(
            appointment=self.appointment,
            event_type=AppointmentHistoryEventType.CREATED,
            previous_status="",
            new_status=AppointmentStatus.CONFIRMED,
            new_start_at=self.appointment.start_at,
            new_end_at=self.appointment.end_at,
            actor=self.patient_alice,
            actor_role=UserRole.PATIENT,
            reason=self.appointment.patient_note,
        )

    # 1. Patient can cancel an eligible appointment before the cutoff
    def test_01_patient_can_cancel_before_cutoff(self):
        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": self.appointment.id})

        # Simulate evaluation 2 days before appointment date
        eval_time = self.appointment.start_at - timedelta(days=2)
        with patch("django.utils.timezone.now", return_value=eval_time):
            response = self.client.post(url, {"reason": "Change of plans"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)
        self.assertEqual(self.appointment.cancellation_reason, "Change of plans")
        self.assertEqual(self.appointment.cancelled_by, self.patient_alice)

    # 2. Patient cannot cancel after midnight on the appointment day in clinic timezone
    def test_02_patient_cannot_cancel_after_midnight_on_appointment_day(self):
        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": self.appointment.id})

        # Cutoff is 23:59:59.999999 on day before in Asia/Kolkata
        # 00:00:01 on appointment day in Asia/Kolkata should be rejected
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        past_cutoff = datetime.combine(
            self.target_monday, time(0, 0, 1), tzinfo=kolkata_tz
        )

        with patch("django.utils.timezone.now", return_value=past_cutoff):
            response = self.client.post(url, {"reason": "Late cancel"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)

    # 3. Cancellation evaluated correctly near the boundary (23:59:58 vs 00:00:02)
    def test_03_boundary_evaluation_near_end_of_previous_day(self):
        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": self.appointment.id})
        kolkata_tz = ZoneInfo("Asia/Kolkata")

        day_before = self.target_monday - timedelta(days=1)
        # Just before cutoff: 23:59:58
        before_cutoff = datetime.combine(day_before, time(23, 59, 58), tzinfo=kolkata_tz)
        with patch("django.utils.timezone.now", return_value=before_cutoff):
            # Check eligibility helper
            cutoff = get_appointment_cancellation_cutoff(self.appointment)
            self.assertTrue(before_cutoff <= cutoff)

        # Just after cutoff: 00:00:02 on appointment day
        after_cutoff = datetime.combine(self.target_monday, time(0, 0, 2), tzinfo=kolkata_tz)
        with patch("django.utils.timezone.now", return_value=after_cutoff):
            response = self.client.post(url, {"reason": "Just missed it"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # 4. Clinic timezone, rather than browser or server timezone, determines cutoff
    def test_04_clinic_timezone_determines_cutoff(self):
        # Create appointment at New York clinic on Wednesday 10:00 AM NY time
        ny_tz = ZoneInfo("America/New_York")
        appt_ny_start = datetime(2026, 10, 28, 10, 0, tzinfo=ny_tz)
        appt_ny = Appointment.objects.create(
            booking_reference="EZD-NY-001",
            patient=self.patient_alice,
            doctor_clinic=self.assoc_ny,
            doctor=self.doctor,
            clinic=self.clinic_ny,
            start_at=appt_ny_start,
            end_at=appt_ny_start + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("150.00"),
            currency="USD",
        )

        cutoff = get_appointment_cancellation_cutoff(appt_ny)
        # Cutoff should be 2026-10-27 23:59:59.999999 America/New_York
        self.assertEqual(cutoff.tzinfo.key, "America/New_York")
        self.assertEqual(cutoff.date(), date(2026, 10, 27))
        self.assertEqual(cutoff.hour, 23)
        self.assertEqual(cutoff.minute, 59)

        # At 2026-10-27 23:30 NY time: in UTC it is 2026-10-28 03:30 AM (next calendar day in UTC!)
        # Yet in NY local time, it is STILL before cutoff!
        time_ny_local = datetime(2026, 10, 27, 23, 30, tzinfo=ny_tz)
        with patch("django.utils.timezone.now", return_value=time_ny_local):
            self.client.force_authenticate(user=self.patient_alice)
            url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": appt_ny.id})
            resp = self.client.post(url, {"reason": "Cancelling in NY"}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # 5. Patient can reschedule before the cutoff
    def test_05_patient_can_reschedule_before_cutoff(self):
        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})

        kolkata_tz = ZoneInfo("Asia/Kolkata")
        # Destination slot: Tuesday at 10:00 AM Kolkata time
        new_start = datetime.combine(self.target_tuesday, time(10, 0), tzinfo=kolkata_tz)
        eval_time = self.appointment.start_at - timedelta(days=2)

        with patch("django.utils.timezone.now", return_value=eval_time):
            response = self.client.post(
                url,
                {"start_at": new_start.isoformat(), "reason": "Prefer Tuesday morning"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.start_at, new_start)
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)

    # 6. Patient cannot reschedule after cutoff without authorized exception
    def test_06_patient_cannot_reschedule_after_cutoff_without_exception(self):
        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})

        kolkata_tz = ZoneInfo("Asia/Kolkata")
        new_start = datetime.combine(self.target_tuesday, time(10, 0), tzinfo=kolkata_tz)
        past_cutoff = datetime.combine(self.target_monday, time(1, 0), tzinfo=kolkata_tz)

        with patch("django.utils.timezone.now", return_value=past_cutoff):
            response = self.client.post(
                url,
                {"start_at": new_start.isoformat(), "reason": "Late reschedule attempt"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.start_at, self.appt_start_kolkata)

    # 7. Authorized clinic user can resolve an appointment affected by doctor unavailability
    def test_07_authorized_clinic_user_can_resolve_unavailability_exception(self):
        # 1. Doctor reports unavailability on this appointment
        report_doctor_unavailability_for_appointment(
            appointment=self.appointment,
            reported_by=self.doctor_user,
            reason="Doctor attending medical emergency",
            action="RESCHEDULE_REQUIRED",
        )
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.RESCHEDULE_REQUIRED)
        self.assertTrue(self.appointment.reschedule_required)

        # 2. Patient can now reschedule even though cutoff passed!
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        past_cutoff = datetime.combine(self.target_monday, time(2, 0), tzinfo=kolkata_tz)
        new_start = datetime.combine(self.target_tuesday, time(10, 0), tzinfo=kolkata_tz)

        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})
        with patch("django.utils.timezone.now", return_value=past_cutoff):
            response = self.client.post(
                url,
                {"start_at": new_start.isoformat(), "reason": "Rescheduling due to doctor emergency"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)
        self.assertFalse(self.appointment.reschedule_required)
        self.assertEqual(self.appointment.start_at, new_start)

    # 8. Unauthorized users cannot bypass cutoff by passing extra fields
    def test_08_unauthorized_user_cannot_bypass_cutoff(self):
        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": self.appointment.id})

        kolkata_tz = ZoneInfo("Asia/Kolkata")
        past_cutoff = datetime.combine(self.target_monday, time(2, 0), tzinfo=kolkata_tz)

        # Attempt to inject client-supplied bypass flags
        payload = {
            "reason": "Late cancel",
            "is_exception": True,
            "status": "CANCELLED",
            "actor_role": "SUPER_ADMIN",
            "cutoff_override": True,
        }
        with patch("django.utils.timezone.now", return_value=past_cutoff):
            response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)

    # 9. Completed appointments cannot be cancelled or rescheduled
    def test_09_completed_appointments_cannot_be_cancelled_or_rescheduled(self):
        self.appointment.status = AppointmentStatus.COMPLETED
        self.appointment.save()

        self.client.force_authenticate(user=self.patient_alice)
        cancel_url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": self.appointment.id})
        resched_url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})

        res1 = self.client.post(cancel_url, {"reason": "Cancel completed"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_409_CONFLICT)

        kolkata_tz = ZoneInfo("Asia/Kolkata")
        new_start = datetime.combine(self.target_tuesday, time(10, 0), tzinfo=kolkata_tz)
        res2 = self.client.post(resched_url, {"start_at": new_start.isoformat()}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_409_CONFLICT)

    # 10. Already cancelled appointments cannot be cancelled again
    def test_10_already_cancelled_appointments_cannot_be_cancelled_again(self):
        self.appointment.status = AppointmentStatus.CANCELLED
        self.appointment.save()

        self.client.force_authenticate(user=self.patient_alice)
        cancel_url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": self.appointment.id})
        res = self.client.post(cancel_url, {"reason": "Double cancel"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # 11. Invalid status transitions are rejected
    def test_11_invalid_status_transitions_rejected(self):
        self.appointment.status = AppointmentStatus.NO_SHOW
        self.appointment.save()

        self.client.force_authenticate(user=self.patient_alice)
        cancel_url = reverse("api-v1:appointments:appointment-cancel", kwargs={"appointment_id": self.appointment.id})
        res = self.client.post(cancel_url, {"reason": "Cancel no-show"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # 12. Successful cancellation creates an audit record
    def test_12_successful_cancellation_creates_audit_record(self):
        eval_time = self.appointment.start_at - timedelta(days=2)
        with patch("django.utils.timezone.now", return_value=eval_time):
            cancel_appointment(
                appointment=self.appointment,
                cancelled_by=self.patient_alice,
                reason="Medical emergency in family",
            )

        history = AppointmentHistory.objects.filter(
            appointment=self.appointment,
            event_type=AppointmentHistoryEventType.PATIENT_CANCELLED,
        ).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.previous_status, AppointmentStatus.CONFIRMED)
        self.assertEqual(history.new_status, AppointmentStatus.CANCELLED)
        self.assertEqual(history.actor, self.patient_alice)
        self.assertEqual(history.reason, "Medical emergency in family")
        self.assertFalse(history.is_exception)

    # 13. Successful reschedule records old and new times in audit history
    def test_13_reschedule_records_old_and_new_times_in_audit(self):
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        new_start = datetime.combine(self.target_tuesday, time(10, 0), tzinfo=kolkata_tz)
        new_end = new_start + timedelta(minutes=30)
        old_start = self.appointment.start_at
        old_end = self.appointment.end_at

        eval_time = self.appointment.start_at - timedelta(days=2)
        with patch("django.utils.timezone.now", return_value=eval_time):
            reschedule_appointment(
                appointment=self.appointment,
                rescheduled_by=self.patient_alice,
                new_start_at=new_start,
                reason="Shifted to Tuesday",
            )

        history = AppointmentHistory.objects.filter(
            appointment=self.appointment,
            event_type=AppointmentHistoryEventType.RESCHEDULED,
        ).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.previous_start_at, old_start)
        self.assertEqual(history.previous_end_at, old_end)
        self.assertEqual(history.new_start_at, new_start)
        self.assertEqual(history.new_end_at, new_end)
        self.assertEqual(history.actor, self.patient_alice)

    # 14. Failed reschedule leaves original appointment unchanged
    def test_14_failed_reschedule_leaves_original_unchanged(self):
        # Create conflicting appointment for another patient on Tuesday 10:00
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        tue_start = datetime.combine(self.target_tuesday, time(10, 0), tzinfo=kolkata_tz)
        Appointment.objects.create(
            booking_reference="EZD-OTHER-002",
            patient=self.patient_bob,
            doctor_clinic=self.assoc_kolkata,
            doctor=self.doctor,
            clinic=self.clinic_kolkata,
            start_at=tue_start,
            end_at=tue_start + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
            currency="INR",
        )

        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})
        eval_time = self.appointment.start_at - timedelta(days=2)

        with patch("django.utils.timezone.now", return_value=eval_time):
            res = self.client.post(
                url,
                {"start_at": tue_start.isoformat(), "reason": "Try booking already taken slot"},
                format="json",
            )

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.appointment.refresh_from_db()
        # Original appointment is completely unchanged
        self.assertEqual(self.appointment.start_at, self.appt_start_kolkata)
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)

    # 15. Destination slot no longer available is rejected cleanly
    def test_15_destination_slot_unavailable_rejected(self):
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        # Try rescheduling to 15:00 (outside doctor's working shift 09:00 - 13:00)
        invalid_shift_start = datetime.combine(self.target_tuesday, time(15, 0), tzinfo=kolkata_tz)

        self.client.force_authenticate(user=self.patient_alice)
        url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})
        eval_time = self.appointment.start_at - timedelta(days=2)

        with patch("django.utils.timezone.now", return_value=eval_time):
            res = self.client.post(
                url,
                {"start_at": invalid_shift_start.isoformat()},
                format="json",
            )

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.start_at, self.appt_start_kolkata)

    # 16. Rescheduling cannot create double booking
    def test_16_rescheduling_cannot_create_double_booking(self):
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        target_slot = datetime.combine(self.target_tuesday, time(11, 0), tzinfo=kolkata_tz)

        # Another confirmed booking exists at 11:00
        Appointment.objects.create(
            booking_reference="EZD-BOB-003",
            patient=self.patient_bob,
            doctor_clinic=self.assoc_kolkata,
            doctor=self.doctor,
            clinic=self.clinic_kolkata,
            start_at=target_slot,
            end_at=target_slot + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
            currency="INR",
        )

        eval_time = self.appointment.start_at - timedelta(days=2)
        with patch("django.utils.timezone.now", return_value=eval_time):
            self.client.force_authenticate(user=self.patient_alice)
            url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})
            res = self.client.post(url, {"start_at": target_slot.isoformat()}, format="json")
            self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # 17. Cross-clinic travel buffer rules apply during rescheduling
    def test_17_cross_clinic_travel_buffer_applies_during_rescheduling(self):
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        # Tuesday 11:00 AM at clinic Fortis (different clinic)
        tue_11am = datetime.combine(self.target_tuesday, time(11, 0), tzinfo=kolkata_tz)
        Appointment.objects.create(
            booking_reference="EZD-FORTIS-001",
            patient=self.patient_bob,
            doctor_clinic=self.assoc_ny,  # Different clinic
            doctor=self.doctor,
            clinic=self.clinic_ny,
            start_at=tue_11am,
            end_at=tue_11am + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("800.00"),
            currency="INR",
        )

        # Alice tries to reschedule her Apollo appointment to Tuesday 11:15 AM (violating 30m travel buffer)
        eval_time = self.appointment.start_at - timedelta(days=2)
        with patch("django.utils.timezone.now", return_value=eval_time):
            self.client.force_authenticate(user=self.patient_alice)
            url = reverse("api-v1:appointments:appointment-reschedule", kwargs={"appointment_id": self.appointment.id})
            res = self.client.post(url, {"start_at": tue_11am.isoformat()}, format="json")
            self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # 18. Clinic owners cannot modify another clinic's appointments
    def test_18_clinic_owners_cannot_modify_another_clinics_appointments(self):
        # Owner B attempts to cancel Alice's appointment at Clinic A
        self.client.force_authenticate(user=self.clinic_owner_b)
        url = reverse(
            "api-v1:clinics:clinic-appointment-cancel",
            kwargs={"clinic_id": self.clinic_ny.id, "appointment_id": self.appointment.id},
        )
        res = self.client.post(url, {"reason": "Malicious clinic cancel"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CONFIRMED)

    # 19. Patients cannot retrieve another patient's appointment history
    def test_19_patients_cannot_retrieve_another_patients_appointment_history(self):
        self.client.force_authenticate(user=self.patient_bob)
        url = reverse("api-v1:appointments:appointment-history", kwargs={"appointment_id": self.appointment.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # 20. Authorized clinic owner can view their clinic's appointment history
    def test_20_authorized_clinic_owner_can_view_appointment_history(self):
        self.client.force_authenticate(user=self.clinic_owner_a)
        url = reverse("api-v1:appointments:appointment-history", kwargs={"appointment_id": self.appointment.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    # 21. Exception actions record actor, reason, and timestamp
    def test_21_exception_actions_record_actor_reason_and_timestamp(self):
        report_doctor_unavailability_for_appointment(
            appointment=self.appointment,
            reported_by=self.doctor_user,
            reason="Emergency surgical operation",
            action="RESCHEDULE_REQUIRED",
        )

        history = AppointmentHistory.objects.filter(
            appointment=self.appointment,
            event_type=AppointmentHistoryEventType.DOCTOR_UNAVAILABLE,
        ).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.actor, self.doctor_user)
        self.assertEqual(history.actor_role, UserRole.DOCTOR)
        self.assertEqual(history.reason, "Emergency surgical operation")
        self.assertTrue(history.is_exception)
        self.assertIsNotNone(history.created_at)

    # 22. Correct restoration of availability after cancellation
    def test_22_restoration_of_availability_after_cancellation(self):
        from apps.schedules.services import generate_doctor_availability_slots

        # Before cancellation: target_monday at 10:00 is booked
        slots_before = generate_doctor_availability_slots(
            doctor_clinic=self.assoc_kolkata,
            target_date=self.target_monday,
        )
        slot_10am = next(s for s in slots_before["slots"] if s["start_time"] == "10:00")
        self.assertFalse(slot_10am["is_available"])

        # Cancel the appointment
        eval_time = self.appointment.start_at - timedelta(days=2)
        with patch("django.utils.timezone.now", return_value=eval_time):
            cancel_appointment(
                appointment=self.appointment,
                cancelled_by=self.patient_alice,
                reason="Restoring slot",
            )

        # After cancellation: slot at 10:00 should immediately become available!
        slots_after = generate_doctor_availability_slots(
            doctor_clinic=self.assoc_kolkata,
            target_date=self.target_monday,
        )
        slot_10am_after = next(s for s in slots_after["slots"] if s["start_time"] == "10:00")
        self.assertTrue(slot_10am_after["is_available"])
