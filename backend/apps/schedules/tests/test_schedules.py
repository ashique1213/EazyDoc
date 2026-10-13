from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.schedules.models import BlockedSlot, DoctorSchedule, DoctorUnavailability, Weekday


class ScheduleAndAvailabilityTests(APITestCase):
    """
    Comprehensive test suite for Doctor Schedule & Availability Management (Day 7).
    Validates:
    - Multi-tenant schedule configuration
    - Overlap prevention (same clinic and cross-clinic)
    - Split shifts allowance
    - Cross-clinic travel buffer enforcement
    - Timezone-aware slot generation
    - Doctor leaves / unavailability slot filtering
    - Administrative blocked slot filtering
    - Soft-deactivation preserving history
    - Tenant isolation & unauthorized tampering rejection
    """

    def setUp(self):
        # 1. Clinic Owners
        self.owner_a = User.objects.create_user(
            email="owner_a@clinic-a.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.owner_b = User.objects.create_user(
            email="owner_b@clinic-b.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        # 2. Approved Clinics
        self.clinic_a = Clinic.objects.create(
            name="Apollo Care Clinic",
            owner=self.owner_a,
            email="contact@apollocare.com",
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
            owner=self.owner_b,
            email="contact@fortiswellness.com",
            phone="9876543211",
            address_line_1="200 Brigade Road",
            city="Bengaluru",
            state="Karnataka",
            pincode="560025",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
        )

        # 3. Verified Doctor
        self.doctor_user = User.objects.create_user(
            email="dr.rahul@medcare.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            full_name="Dr. Rahul Verma",
            registration_number="KMC-445566",
            registration_council="Karnataka Medical Council",
            specialization="General Medicine",
            qualifications="MBBS, MD",
            years_of_experience=8,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # 4. Active Doctor-Clinic Associations
        self.assoc_a = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            appointment_duration_minutes=15,
        )
        self.assoc_b = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_b,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("600.00"),
            appointment_duration_minutes=20,
        )

        self.schedules_url = reverse("api-v1:schedules:schedule-list-create")
        self.conflict_check_url = reverse("api-v1:schedules:schedule-check-conflict")
        self.unavail_url = reverse("api-v1:schedules:unavailability-list-create")
        self.blocked_url = reverse("api-v1:schedules:blocked-slots-list-create")
        self.availability_url = reverse("api-v1:schedules:availability-slots")

    # =========================================================================
    # 1. Schedule Creation & Tenant Isolation
    # =========================================================================

    def test_clinic_owner_can_create_schedule(self):
        """Rule 1 & 5: Clinic owner can configure shifts for active doctor at their clinic."""
        self.client.force_authenticate(user=self.owner_a)
        payload = {
            "doctor_clinic": str(self.assoc_a.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "09:00",
            "end_time": "13:00",
            "slot_duration_minutes": 15,
            "buffer_minutes": 0,
        }
        response = self.client.post(self.schedules_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["day_of_week"], Weekday.MONDAY)
        self.assertEqual(response.data["start_time"], "09:00:00")
        self.assertEqual(response.data["end_time"], "13:00:00")
        self.assertEqual(response.data["clinic_name"], "Apollo Care Clinic")

    def test_clinic_owner_cannot_create_schedule_for_other_clinic(self):
        """Rule 5 & 6: Clinic owner A cannot configure schedules for Clinic B."""
        self.client.force_authenticate(user=self.owner_a)
        payload = {
            "doctor_clinic": str(self.assoc_b.id),  # Belongs to clinic_b (owner_b)
            "day_of_week": Weekday.MONDAY,
            "start_time": "14:00",
            "end_time": "18:00",
        }
        response = self.client.post(self.schedules_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # 2. Split Shifts & Same-Clinic Overlaps
    # =========================================================================

    def test_same_clinic_split_shifts_are_allowed(self):
        """Rule 12: Legitimate split shifts (morning 09-13 and evening 14-18) at the same clinic succeed."""
        self.client.force_authenticate(user=self.owner_a)

        # Shift 1: 09:00 - 13:00
        res1 = self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_a.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "09:00",
            "end_time": "13:00",
        }, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Shift 2: 14:00 - 18:00
        res2 = self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_a.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "14:00",
            "end_time": "18:00",
        }, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DoctorSchedule.objects.filter(doctor_clinic=self.assoc_a).count(), 2)

    def test_same_clinic_overlapping_shifts_are_rejected(self):
        """Rule 17: Shifts overlapping within the same clinic return 409 Conflict."""
        self.client.force_authenticate(user=self.owner_a)

        # Shift 1: 09:00 - 13:00
        self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_a.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "09:00",
            "end_time": "13:00",
        }, format="json")

        # Shift 2 (overlapping 11:00 - 15:00)
        res = self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_a.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "11:00",
            "end_time": "15:00",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("SAME_CLINIC_OVERLAP", str(res.data))

    # =========================================================================
    # 3. Cross-Clinic Conflicts & Travel Buffer Enforcement
    # =========================================================================

    def test_cross_clinic_overlapping_shifts_are_rejected(self):
        """Rule 11: Cross-clinic overlapping shifts for the same doctor return 409 Conflict."""
        # Clinic A schedules Dr. Rahul on Monday 09:00 - 13:00
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )

        # Clinic B owner attempts to schedule Dr. Rahul on Monday 12:00 - 16:00
        self.client.force_authenticate(user=self.owner_b)
        response = self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_b.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "12:00",
            "end_time": "16:00",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("CROSS_CLINIC_OVERLAP", str(response.data))
        self.assertIn("Apollo Care Clinic", str(response.data))

    def test_cross_clinic_travel_buffer_violation_is_rejected(self):
        """Rule 13: Shifts across clinics without minimum travel buffer (30m) return 409 Conflict."""
        # Clinic A: Monday 09:00 - 13:00
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )

        # Clinic B attempts 13:15 - 17:00 (only 15 min gap, requires 30 mins)
        self.client.force_authenticate(user=self.owner_b)
        response = self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_b.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "13:15",
            "end_time": "17:00",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("TRAVEL_BUFFER_VIOLATION", str(response.data))

    def test_cross_clinic_valid_buffer_succeeds(self):
        """Rule 13: Shift across clinics satisfying travel buffer (e.g. 13:45 with 45m gap) succeeds."""
        # Clinic A: Monday 09:00 - 13:00
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )

        # Clinic B starts at 13:45 (gap is 45 min >= 30 min buffer)
        self.client.force_authenticate(user=self.owner_b)
        response = self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_b.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "13:45",
            "end_time": "17:00",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # =========================================================================
    # 4. Association Eligibility (Rules 3 & 4)
    # =========================================================================

    def test_cannot_schedule_for_unverified_doctor(self):
        """Rule 3: Unverified doctor cannot receive new schedules."""
        unverified_user = User.objects.create_user(
            email="unverified@doc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
        )
        unverified_doc = Doctor.objects.create(
            user=unverified_user,
            full_name="Dr. Unverified",
            registration_number="REG-9999",
            registration_council="Council",
            verification_status=DoctorVerificationStatus.PENDING,
        )
        assoc = DoctorClinic.objects.create(
            doctor=unverified_doc,
            clinic=self.clinic_a,
            status=DoctorClinicStatus.ACTIVE,
        )

        self.client.force_authenticate(user=self.owner_a)
        res = self.client.post(self.schedules_url, {
            "doctor_clinic": str(assoc.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "09:00",
            "end_time": "13:00",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_schedule_for_inactive_association(self):
        """Rule 3: Association in INVITED / REMOVED status cannot receive new schedules."""
        self.assoc_a.status = DoctorClinicStatus.INVITED
        self.assoc_a.save()

        self.client.force_authenticate(user=self.owner_a)
        res = self.client.post(self.schedules_url, {
            "doctor_clinic": str(self.assoc_a.id),
            "day_of_week": Weekday.MONDAY,
            "start_time": "09:00",
            "end_time": "13:00",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # 5. Doctor Multi-Clinic View (Rule 2)
    # =========================================================================

    def test_doctor_can_view_unified_master_schedule(self):
        """Rule 2: Doctor can view unified schedule across all clinics."""
        # Clinic A shift
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        # Clinic B shift
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_b,
            day_of_week=Weekday.MONDAY,
            start_time=time(14, 0),
            end_time=time(18, 0),
        )

        self.client.force_authenticate(user=self.doctor_user)
        res = self.client.get(reverse("api-v1:schedules:doctor-master-schedule"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_active_shifts"], 2)

        # Check Monday shifts contain both clinics
        monday_data = [d for d in res.data["weekly_schedule"] if d["day_of_week"] == Weekday.MONDAY][0]
        self.assertEqual(len(monday_data["shifts"]), 2)

    # =========================================================================
    # 6. Soft Deactivation (Rule 16)
    # =========================================================================

    def test_schedule_deactivation_preserves_history(self):
        """Rule 16: Deletion soft-deactivates the shift without deleting history."""
        shift = DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.TUESDAY,
            start_time=time(10, 0),
            end_time=time(14, 0),
        )

        self.client.force_authenticate(user=self.owner_a)
        detail_url = reverse("api-v1:schedules:schedule-detail", kwargs={"pk": shift.id})
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify still in database but is_active is False
        shift.refresh_from_db()
        self.assertFalse(shift.is_active)

    # =========================================================================
    # 7. Real-Time Availability Slot Engine (Rule 8, 10, 14, 15)
    # =========================================================================

    def test_availability_generation_with_leaves_and_blocked_slots(self):
        """
        Tests slot generation on a specific date:
        - 09:00 to 11:00 shift (8 slots of 15m).
        - Doctor takes sick leave from 09:30 to 10:15 in clinic local time (stored in UTC).
        - Administrative blocked slot at 10:30.
        - Verifies accurate is_available flags and reasons.
        """
        # Create schedule: Monday 09:00 - 11:00 (15 min duration)
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(11, 0),
            slot_duration_minutes=15,
        )

        # Next Monday date
        today = date.today()
        days_ahead = (0 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        next_monday = today + timedelta(days=days_ahead)

        # Create doctor leave from 09:30 to 10:15 local time (Asia/Kolkata is UTC+5:30)
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        leave_start_local = datetime.combine(next_monday, time(9, 30), tzinfo=kolkata_tz)
        leave_end_local = datetime.combine(next_monday, time(10, 15), tzinfo=kolkata_tz)

        DoctorUnavailability.objects.create(
            doctor=self.doctor,
            clinic=self.clinic_a,
            start_datetime=leave_start_local.astimezone(dt_timezone.utc),
            end_datetime=leave_end_local.astimezone(dt_timezone.utc),
            reason="SICK_LEAVE",
            notes="Flu recovery",
        )

        # Administrative blocked slot at 10:30
        BlockedSlot.objects.create(
            doctor_clinic=self.assoc_a,
            date=next_monday,
            start_time=time(10, 30),
            reason="VIP Visit",
        )

        self.client.force_authenticate(user=self.owner_a)
        res = self.client.get(
            f"{self.availability_url}?doctor_clinic_id={self.assoc_a.id}&date={next_monday.isoformat()}"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        slots = res.data["slots"]
        self.assertEqual(len(slots), 8)  # 2 hours / 15 mins = 8 slots

        slot_map = {s["start_time"]: s for s in slots}

        # 09:00 - 09:15 -> Available
        self.assertTrue(slot_map["09:00"]["is_available"])
        self.assertIsNone(slot_map["09:00"]["reason"])

        # 09:15 - 09:30 -> Available
        self.assertTrue(slot_map["09:15"]["is_available"])

        # 09:30 - 09:45 -> Unavailable due to doctor leave
        self.assertFalse(slot_map["09:30"]["is_available"])
        self.assertIn("Doctor unavailable", slot_map["09:30"]["reason"])

        # 09:45 - 10:00 -> Unavailable due to doctor leave
        self.assertFalse(slot_map["09:45"]["is_available"])

        # 10:00 - 10:15 -> Unavailable due to doctor leave
        self.assertFalse(slot_map["10:00"]["is_available"])

        # 10:15 - 10:30 -> Available
        self.assertTrue(slot_map["10:15"]["is_available"])

        # 10:30 - 10:45 -> Blocked slot
        self.assertFalse(slot_map["10:30"]["is_available"])
        self.assertIn("VIP Visit", slot_map["10:30"]["reason"])

        # 10:45 - 11:00 -> Available
        self.assertTrue(slot_map["10:45"]["is_available"])

    # =========================================================================
    # 8. Dry-Run Conflict Check Endpoint
    # =========================================================================

    def test_dry_run_conflict_check_endpoint(self):
        """Tests the pre-validation dry-run conflict check endpoint."""
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a,
            day_of_week=Weekday.WEDNESDAY,
            start_time=time(10, 0),
            end_time=time(14, 0),
        )

        self.client.force_authenticate(user=self.owner_b)

        # Conflict case
        res_conflict = self.client.post(self.conflict_check_url, {
            "doctor_clinic": str(self.assoc_b.id),
            "day_of_week": Weekday.WEDNESDAY,
            "start_time": "12:00",
            "end_time": "16:00",
        }, format="json")
        self.assertEqual(res_conflict.status_code, status.HTTP_200_OK)
        self.assertTrue(res_conflict.data["has_conflict"])
        self.assertIsNotNone(res_conflict.data["conflict"])

        # Non-conflict case
        res_ok = self.client.post(self.conflict_check_url, {
            "doctor_clinic": str(self.assoc_b.id),
            "day_of_week": Weekday.WEDNESDAY,
            "start_time": "15:00",
            "end_time": "19:00",
        }, format="json")
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.assertFalse(res_ok.data["has_conflict"])
        self.assertIsNone(res_ok.data["conflict"])
