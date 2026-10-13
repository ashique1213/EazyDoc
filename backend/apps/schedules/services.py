from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import UserStatus
from apps.clinics.models import ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import DoctorVerificationStatus
from .exceptions import InactiveAssociationException, ScheduleConflictException
from .models import BlockedSlot, DoctorSchedule, DoctorUnavailability, Weekday


def time_to_minutes(t: time) -> int:
    """Converts a datetime.time object to integer minutes from midnight."""
    return t.hour * 60 + t.minute


def minutes_to_time(m: int) -> time:
    """Converts integer minutes from midnight to a datetime.time object."""
    hours = (m // 60) % 24
    minutes = m % 60
    return time(hour=hours, minute=minutes)


def add_minutes_to_time(t: time, minutes: int) -> time:
    """Adds minutes to a time object, clamping or rolling within the day."""
    total_minutes = time_to_minutes(t) + minutes
    return minutes_to_time(total_minutes)


def validate_association_eligibility(doctor_clinic: DoctorClinic) -> None:
    """
    Enforces business rules regarding doctor and clinic eligibility for scheduling:
    Rule 3: Only verified, active doctors with active doctor-clinic associations can receive new availability.
    Rule 4: Only approved and active clinics can publish bookable availability.
    """
    # 1. Association status
    if doctor_clinic.status != DoctorClinicStatus.ACTIVE:
        raise InactiveAssociationException(
            _("Cannot configure schedules. The doctor-clinic affiliation is not active (current status: %(status)s).")
            % {"status": doctor_clinic.get_status_display()}
        )

    # 2. Clinic verification status
    clinic = doctor_clinic.clinic
    if clinic.status != ClinicStatus.APPROVED:
        raise InactiveAssociationException(
            _("Cannot configure schedules. Clinic '%(name)s' is not approved (current status: %(status)s).")
            % {"name": clinic.name, "status": clinic.get_status_display()}
        )

    # 3. Doctor verification and user account status
    doctor = doctor_clinic.doctor
    if doctor.verification_status != DoctorVerificationStatus.VERIFIED:
        raise InactiveAssociationException(
            _("Cannot configure schedules. Doctor '%(name)s' is not verified by administration.")
            % {"name": doctor.full_name}
        )

    if not doctor.user or not doctor.user.is_active or doctor.user.status != UserStatus.ACTIVE:
        raise InactiveAssociationException(
            _("Cannot configure schedules. Doctor account is inactive or suspended.")
        )


def check_schedule_conflicts(
    doctor_id: Any,
    day_of_week: int,
    start_time: time,
    end_time: time,
    clinic_id: Any,
    exclude_schedule_id: Optional[Any] = None,
    buffer_minutes: int = 0,
    travel_buffer_minutes: int = 30,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validates proposed working shift for physical feasibility and cross-clinic conflict prevention:
    - Rule 11: Prevent overlapping working intervals for the same doctor across clinics.
    - Rule 12: Allow legitimate split shifts (e.g. 09:00-13:00 and 14:00-18:00) at the same clinic.
    - Rule 13: Account for configurable travel or transition buffer time between different clinics.
    """
    p_start = time_to_minutes(start_time)
    p_end = time_to_minutes(end_time)

    if p_start >= p_end:
        return True, {
            "conflict_type": "INVALID_INTERVAL",
            "message": _("Shift start time must be strictly before shift end time."),
        }

    # Query all active shifts for this doctor on the requested day_of_week across ALL clinics
    qs = DoctorSchedule.objects.filter(
        doctor_clinic__doctor_id=doctor_id,
        day_of_week=day_of_week,
        is_active=True,
    ).select_related("doctor_clinic__clinic")

    if exclude_schedule_id:
        qs = qs.exclude(pk=exclude_schedule_id)

    for existing in qs:
        e_start = time_to_minutes(existing.start_time)
        e_end = time_to_minutes(existing.end_time)
        existing_clinic = existing.doctor_clinic.clinic
        is_same_clinic = str(existing_clinic.id) == str(clinic_id)

        # 1. Direct Interval Overlap Check: max(p_start, e_start) < min(p_end, e_end)
        if p_start < e_end and e_start < p_end:
            if is_same_clinic:
                return True, {
                    "conflict_type": "SAME_CLINIC_OVERLAP",
                    "message": _(
                        "Proposed shift %(start)s - %(end)s overlaps with an existing shift (%(e_start)s - %(e_end)s) at this clinic."
                    ) % {
                        "start": start_time.strftime("%H:%M"),
                        "end": end_time.strftime("%H:%M"),
                        "e_start": existing.start_time.strftime("%H:%M"),
                        "e_end": existing.end_time.strftime("%H:%M"),
                    },
                    "conflicting_clinic_id": str(existing_clinic.id),
                    "conflicting_clinic_name": existing_clinic.name,
                    "day_of_week": day_of_week,
                    "start_time": existing.start_time.strftime("%H:%M"),
                    "end_time": existing.end_time.strftime("%H:%M"),
                    "schedule_id": str(existing.id),
                }
            else:
                return True, {
                    "conflict_type": "CROSS_CLINIC_OVERLAP",
                    "message": _(
                        "Cross-clinic conflict: Doctor is already scheduled at '%(clinic)s' on %(weekday)s from %(e_start)s to %(e_end)s."
                    ) % {
                        "clinic": existing_clinic.name,
                        "weekday": Weekday(day_of_week).label,
                        "e_start": existing.start_time.strftime("%H:%M"),
                        "e_end": existing.end_time.strftime("%H:%M"),
                    },
                    "conflicting_clinic_id": str(existing_clinic.id),
                    "conflicting_clinic_name": existing_clinic.name,
                    "day_of_week": day_of_week,
                    "start_time": existing.start_time.strftime("%H:%M"),
                    "end_time": existing.end_time.strftime("%H:%M"),
                    "schedule_id": str(existing.id),
                }

        # 2. Travel Buffer Check for DIFFERENT clinics
        if not is_same_clinic:
            effective_travel_buffer = max(travel_buffer_minutes, buffer_minutes, existing.buffer_minutes)

            # If proposed shift is AFTER existing shift
            if p_start >= e_end:
                gap = p_start - e_end
                if gap < effective_travel_buffer:
                    return True, {
                        "conflict_type": "TRAVEL_BUFFER_VIOLATION",
                        "message": _(
                            "Insufficient travel buffer between clinics. Doctor completes shift at '%(clinic)s' at %(e_end)s. "
                            "A minimum %(buffer)d minutes travel buffer is required before starting at next clinic (available gap: %(gap)d mins)."
                        ) % {
                            "clinic": existing_clinic.name,
                            "e_end": existing.end_time.strftime("%H:%M"),
                            "buffer": effective_travel_buffer,
                            "gap": gap,
                        },
                        "conflicting_clinic_id": str(existing_clinic.id),
                        "conflicting_clinic_name": existing_clinic.name,
                        "day_of_week": day_of_week,
                        "start_time": existing.start_time.strftime("%H:%M"),
                        "end_time": existing.end_time.strftime("%H:%M"),
                        "schedule_id": str(existing.id),
                        "required_buffer_minutes": effective_travel_buffer,
                        "actual_gap_minutes": gap,
                    }

            # If proposed shift is BEFORE existing shift
            elif p_end <= e_start:
                gap = e_start - p_end
                if gap < effective_travel_buffer:
                    return True, {
                        "conflict_type": "TRAVEL_BUFFER_VIOLATION",
                        "message": _(
                            "Insufficient travel buffer between clinics. Doctor begins shift at '%(clinic)s' at %(e_start)s. "
                            "A minimum %(buffer)d minutes travel buffer is required after this clinic shift (available gap: %(gap)d mins)."
                        ) % {
                            "clinic": existing_clinic.name,
                            "e_start": existing.start_time.strftime("%H:%M"),
                            "buffer": effective_travel_buffer,
                            "gap": gap,
                        },
                        "conflicting_clinic_id": str(existing_clinic.id),
                        "conflicting_clinic_name": existing_clinic.name,
                        "day_of_week": day_of_week,
                        "start_time": existing.start_time.strftime("%H:%M"),
                        "end_time": existing.end_time.strftime("%H:%M"),
                        "schedule_id": str(existing.id),
                        "required_buffer_minutes": effective_travel_buffer,
                        "actual_gap_minutes": gap,
                    }

    return False, None


def generate_doctor_availability_slots(
    doctor_clinic: DoctorClinic,
    target_date: date,
) -> Dict[str, Any]:
    """
    Computes precise, bookable appointment slots for a given doctor-clinic affiliation and date:
    - Uses clinic operating timezone (default: Asia/Kolkata).
    - Incorporates recurring weekly shifts.
    - Excludes doctor unavailabilities / leaves (converted from UTC).
    - Excludes administrative blocked slots.
    - Computes slot start and end times in local clinic time and UTC.
    """
    clinic = doctor_clinic.clinic
    doctor = doctor_clinic.doctor

    # 1. Eligibility validation
    try:
        validate_association_eligibility(doctor_clinic)
        is_eligible = True
        eligibility_error = None
    except InactiveAssociationException as e:
        is_eligible = False
        eligibility_error = str(e.detail.get("message", e.default_detail) if isinstance(e.detail, dict) else e.detail)

    # 2. Timezone resolution (Rules 8 & 9)
    tz_name = clinic.timezone or "Asia/Kolkata"
    try:
        clinic_tz = ZoneInfo(tz_name)
    except Exception:
        clinic_tz = ZoneInfo("Asia/Kolkata")

    day_of_week = target_date.weekday()

    if not is_eligible:
        return {
            "clinic": {
                "id": str(clinic.id),
                "name": clinic.name,
                "timezone": tz_name,
                "status": clinic.status,
            },
            "doctor": {
                "id": str(doctor.id),
                "full_name": doctor.full_name,
                "specialization": doctor.specialization,
                "verification_status": doctor.verification_status,
            },
            "date": target_date.isoformat(),
            "day_of_week": day_of_week,
            "day_name": Weekday(day_of_week).label,
            "is_eligible": False,
            "eligibility_error": eligibility_error,
            "total_slots": 0,
            "available_slots_count": 0,
            "slots": [],
        }

    # 3. Fetch active shifts for this day of the week
    schedules = DoctorSchedule.objects.filter(
        doctor_clinic=doctor_clinic,
        day_of_week=day_of_week,
        is_active=True,
    ).order_by("start_time")

    active_shifts: List[DoctorSchedule] = []
    for s in schedules:
        if s.effective_from and target_date < s.effective_from:
            continue
        if s.effective_until and target_date > s.effective_until:
            continue
        active_shifts.append(s)

    # 4. Fetch doctor unavailabilities overlapping with target date in UTC
    day_start_local = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=clinic_tz)
    day_end_local = day_start_local + timedelta(days=1)
    day_start_utc = day_start_local.astimezone(dt_timezone.utc)
    day_end_utc = day_end_local.astimezone(dt_timezone.utc)

    unavailabilities = list(
        DoctorUnavailability.objects.filter(doctor=doctor)
        .filter(Q(clinic__isnull=True) | Q(clinic=clinic))
        .filter(start_datetime__lt=day_end_utc, end_datetime__gt=day_start_utc)
    )

    # 5. Fetch blocked slots for this date
    blocked_slots = list(
        BlockedSlot.objects.filter(doctor_clinic=doctor_clinic, date=target_date)
    )

    generated_slots: List[Dict[str, Any]] = []

    # 6. Generate discrete slots per shift
    for shift in active_shifts:
        slot_duration = shift.effective_slot_duration
        current_time = shift.start_time

        while True:
            next_time = add_minutes_to_time(current_time, slot_duration)
            if time_to_minutes(next_time) > time_to_minutes(shift.end_time):
                break

            slot_start = current_time
            slot_end = next_time

            # Local & UTC timestamp calculations
            slot_start_dt = datetime.combine(target_date, slot_start, tzinfo=clinic_tz)
            slot_end_dt = datetime.combine(target_date, slot_end, tzinfo=clinic_tz)
            slot_start_utc = slot_start_dt.astimezone(dt_timezone.utc)
            slot_end_utc = slot_end_dt.astimezone(dt_timezone.utc)

            is_slot_available = True
            unavailable_reason = None

            # Check Doctor Unavailability / Leave
            for unavail in unavailabilities:
                if slot_start_utc < unavail.end_datetime and slot_end_utc > unavail.start_datetime:
                    is_slot_available = False
                    unavailable_reason = f"Doctor unavailable ({unavail.get_reason_display()})"
                    break

            # Check Administrative Blocked Slot
            if is_slot_available:
                for blocked in blocked_slots:
                    b_end = blocked.end_time or add_minutes_to_time(blocked.start_time, slot_duration)
                    if (
                        time_to_minutes(slot_start) < time_to_minutes(b_end)
                        and time_to_minutes(slot_end) > time_to_minutes(blocked.start_time)
                    ):
                        is_slot_available = False
                        unavailable_reason = f"Blocked: {blocked.reason or 'Administrative reservation'}"
                        break

            generated_slots.append({
                "schedule_id": str(shift.id),
                "start_time": slot_start.strftime("%H:%M"),
                "end_time": slot_end.strftime("%H:%M"),
                "start_datetime_utc": slot_start_utc.isoformat(),
                "end_datetime_utc": slot_end_utc.isoformat(),
                "duration_minutes": slot_duration,
                "is_available": is_slot_available,
                "reason": unavailable_reason,
            })

            current_time = next_time

    available_count = sum(1 for s in generated_slots if s["is_available"])

    return {
        "clinic": {
            "id": str(clinic.id),
            "name": clinic.name,
            "timezone": tz_name,
            "status": clinic.status,
        },
        "doctor": {
            "id": str(doctor.id),
            "full_name": doctor.full_name,
            "specialization": doctor.specialization,
            "verification_status": doctor.verification_status,
        },
        "date": target_date.isoformat(),
        "day_of_week": day_of_week,
        "day_name": Weekday(day_of_week).label,
        "is_eligible": True,
        "eligibility_error": None,
        "total_slots": len(generated_slots),
        "available_slots_count": available_count,
        "slots": generated_slots,
    }
