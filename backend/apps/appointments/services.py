import hashlib
import logging
import secrets
import uuid
from datetime import datetime, time, timedelta, timezone as dt_timezone
from typing import Any, Optional, Tuple
from zoneinfo import ZoneInfo
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.schedules.services import generate_doctor_availability_slots
from .exceptions import (
    CutoffExceededException,
    IdempotencyConflictException,
    InvalidAppointmentStateException,
    InvalidBookingException,
    SlotUnavailableException,
)
from .models import (
    Appointment,
    AppointmentHistory,
    AppointmentHistoryEventType,
    AppointmentIdempotency,
    AppointmentStatus,
)

logger = logging.getLogger("apps.appointments")


def dispatch_appointment_event(event_name: str, appointment_id: Any, **kwargs):
    """
    Dispatches appointment events after database transactions successfully commit.
    Safe against exceptions; will not roll back committed data.
    """
    logger.info(
        "Dispatched appointment event '%s' for appointment '%s' with payload: %s",
        event_name,
        appointment_id,
        kwargs,
    )


def generate_booking_reference() -> str:
    """
    Generates a unique, non-sequential, alphanumeric booking reference.
    Format: EZD-YYYYMM-XXXXXX (e.g. EZD-202610-7B4K9A)
    """
    now = timezone.now()
    prefix = f"EZD-{now.strftime('%Y%m')}"
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Excludes ambiguous characters (0, 1, I, O)

    for _ in range(10):
        random_suffix = "".join(secrets.choice(alphabet) for _ in range(6))
        candidate = f"{prefix}-{random_suffix}"
        if not Appointment.objects.filter(booking_reference=candidate).exists():
            return candidate

    # Fallback with uuid if 10 collisions in a row
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"


def compute_booking_request_hash(
    patient_id, clinic_id, doctor_id, start_at_iso: str, patient_note: str = ""
) -> str:
    """Computes a SHA-256 fingerprint of canonical booking parameters."""
    normalized = f"{str(patient_id).strip()}:{str(clinic_id).strip()}:{str(doctor_id).strip()}:{start_at_iso.strip()}:{patient_note.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def book_appointment(
    patient: User,
    clinic_id,
    doctor_id,
    start_at: datetime,
    patient_note: str = "",
    idempotency_key: Optional[str] = None,
) -> Tuple[Appointment, bool]:
    """
    Atomically books a patient appointment with rigorous validation, cross-clinic
    conflict prevention, travel buffer checks, and concurrency protection.

    Returns:
        Tuple[Appointment, bool]: (appointment, is_newly_created)
    """
    # 1. Patient eligibility validation (Rules 1 & 2)
    if not patient or not patient.is_authenticated:
        raise InvalidBookingException(_("Authentication required to book an appointment."))
    if not patient.is_active or patient.status != UserStatus.ACTIVE:
        raise InvalidBookingException(_("Your patient account is inactive or suspended."))
    if patient.role != UserRole.PATIENT:
        raise InvalidBookingException(_("Only patient accounts are permitted to book appointments."))

    # 2. Start time validation (Rules 10 & 11)
    if not timezone.is_aware(start_at):
        raise InvalidBookingException(_("Appointment start timestamp must be timezone-aware."))

    now_utc = timezone.now()
    if start_at <= now_utc:
        raise InvalidBookingException(_("Cannot book an appointment in the past."))

    start_at_iso = start_at.isoformat()
    req_hash = compute_booking_request_hash(
        patient.id, clinic_id, doctor_id, start_at_iso, patient_note
    )

    # 3. Idempotency Check (Rule 8)
    if idempotency_key:
        idempotency_key = str(idempotency_key).strip()
        existing_idemp = AppointmentIdempotency.objects.filter(
            patient=patient, idempotency_key=idempotency_key
        ).select_related("appointment", "appointment__doctor", "appointment__clinic").first()

        if existing_idemp and existing_idemp.appointment:
            # Check payload consistency
            if existing_idemp.request_hash != req_hash:
                raise IdempotencyConflictException(
                    _("Idempotency key has already been used with different booking parameters.")
                )
            # Legitimate retry: return original appointment
            return existing_idemp.appointment, False

    # 4. Association & Pre-flight Eligibility (Rules 3, 4, 5)
    doctor_clinic = (
        DoctorClinic.objects.filter(doctor_id=doctor_id, clinic_id=clinic_id)
        .select_related("doctor", "clinic", "doctor__user")
        .first()
    )
    if not doctor_clinic:
        raise InvalidBookingException(_("No affiliation found between the specified doctor and clinic."))

    if doctor_clinic.status != DoctorClinicStatus.ACTIVE:
        raise InvalidBookingException(_("The doctor-clinic affiliation is not active."))

    clinic = doctor_clinic.clinic
    if clinic.status != ClinicStatus.APPROVED:
        raise InvalidBookingException(_("The selected clinic is not approved for public bookings."))

    doctor = doctor_clinic.doctor
    if doctor.verification_status != DoctorVerificationStatus.VERIFIED:
        raise InvalidBookingException(_("The selected doctor is not verified."))

    if not doctor.user or not doctor.user.is_active or doctor.user.status != UserStatus.ACTIVE:
        raise InvalidBookingException(_("Doctor account is inactive or suspended."))

    # 5. Database-level serialized transaction with pessimistic locking (Rule 6 & 16)
    with transaction.atomic():
        # Lock the global Doctor record to serialize booking requests across all clinics for this doctor
        try:
            Doctor.objects.select_for_update().get(id=doctor.id)
        except Doctor.DoesNotExist:
            raise InvalidBookingException(_("Doctor profile not found."))

        # Re-fetch association within the lock
        locked_dc = (
            DoctorClinic.objects.select_related("doctor", "clinic", "doctor__user")
            .get(id=doctor_clinic.id)
        )
        if locked_dc.status != DoctorClinicStatus.ACTIVE or locked_dc.clinic.status != ClinicStatus.APPROVED:
            raise InvalidBookingException(_("Doctor or clinic affiliation is no longer active."))

        # Interpret date in clinic's timezone (Rule 12)
        tz_name = locked_dc.clinic.timezone or "Asia/Kolkata"
        try:
            clinic_tz = ZoneInfo(tz_name)
        except Exception:
            clinic_tz = ZoneInfo("Asia/Kolkata")

        start_at_local = start_at.astimezone(clinic_tz)
        target_date = start_at_local.date()
        start_time_str = start_at_local.strftime("%H:%M")

        # 6. Validate slot using canonical availability service (Rule 6, 7, 9)
        availability_data = generate_doctor_availability_slots(
            doctor_clinic=locked_dc,
            target_date=target_date,
        )
        if not availability_data.get("is_eligible"):
            err = availability_data.get("eligibility_error") or _("Doctor is not eligible for bookings on this date.")
            raise InvalidBookingException(err)

        matching_slot = None
        for s in availability_data.get("slots", []):
            if s["start_time"] == start_time_str:
                matching_slot = s
                break

        if not matching_slot:
            raise SlotUnavailableException(_("The requested time does not match an active doctor shift slot."))

        if not matching_slot["is_available"]:
            reason = matching_slot.get("reason") or _("Slot is not available.")
            raise SlotUnavailableException(
                _("The selected slot is no longer available: %(reason)s") % {"reason": reason}
            )

        # 7. Slot duration & end timestamp calculation (Rule 7)
        duration_minutes = matching_slot["duration_minutes"]
        end_at = start_at + timedelta(minutes=duration_minutes)

        # 8. Physical overlap check against active appointments (Rule 8)
        blocking_statuses = [
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.PENDING_CONFIRMATION,
            AppointmentStatus.COMPLETED,
        ]

        direct_conflict = Appointment.objects.filter(
            doctor=doctor,
            status__in=blocking_statuses,
            start_at__lt=end_at,
            end_at__gt=start_at,
        ).exists()
        if direct_conflict:
            raise SlotUnavailableException(_("Slot conflict: Doctor already has an appointment during this time."))

        # 9. Cross-clinic travel buffer check (Rule 9 & 14)
        travel_buffer_mins = max(30, locked_dc.appointment_duration_minutes)
        buffer_delta = timedelta(minutes=travel_buffer_mins)

        other_clinic_appts = Appointment.objects.filter(
            doctor=doctor,
            status__in=blocking_statuses,
        ).exclude(clinic=locked_dc.clinic).filter(
            start_at__lt=end_at + buffer_delta,
            end_at__gt=start_at - buffer_delta,
        )
        if other_clinic_appts.exists():
            conflicting_clinic = other_clinic_appts.first().clinic.name
            raise SlotUnavailableException(
                _("Cross-clinic schedule conflict: A %(buffer)d-minute travel buffer is required between clinic visits (conflict with '%(clinic)s').")
                % {"buffer": travel_buffer_mins, "clinic": conflicting_clinic}
            )

        # 10. Fee snapshot resolution from trusted backend configuration (Rules 13 & 14)
        consultation_fee = locked_dc.consultation_fee
        booking_ref = generate_booking_reference()

        try:
            appointment = Appointment.objects.create(
                booking_reference=booking_ref,
                patient=patient,
                doctor_clinic=locked_dc,
                doctor=doctor,
                clinic=locked_dc.clinic,
                start_at=start_at,
                end_at=end_at,
                status=AppointmentStatus.CONFIRMED,
                consultation_fee=consultation_fee,
                currency="INR",
                patient_note=patient_note.strip() if patient_note else "",
            )
        except IntegrityError as exc:
            # Catch PostgreSQL exclusion or unique constraint violations cleanly
            raise SlotUnavailableException(
                _("This slot was just booked by another patient. Please select another slot.")
            )

        # 11. Initial History record
        AppointmentHistory.objects.create(
            appointment=appointment,
            event_type=AppointmentHistoryEventType.CREATED,
            previous_status="",
            new_status=AppointmentStatus.CONFIRMED,
            new_start_at=start_at,
            new_end_at=end_at,
            actor=patient,
            actor_role=UserRole.PATIENT,
            reason=patient_note.strip() if patient_note else "",
            is_exception=False,
            metadata={"action": "create"},
        )

        # 12. Persist Idempotency record (Rule 8)
        if idempotency_key:
            AppointmentIdempotency.objects.create(
                patient=patient,
                idempotency_key=idempotency_key,
                request_hash=req_hash,
                appointment=appointment,
                response_status_code=201,
            )

        # 13. Deferred notification hook
        transaction.on_commit(
            lambda: dispatch_appointment_event(
                "appointment_created",
                appointment.id,
                booking_reference=booking_ref,
            )
        )

        return appointment, True


def get_appointment_cancellation_cutoff(appointment: Appointment) -> datetime:
    """
    Calculates the precise cutoff timestamp for patient-initiated cancellation and rescheduling.
    Cutoff Rule:
    Patients may cancel or reschedule until 11:59:59 PM on the calendar day before the appointment,
    according to the clinic's configured timezone.
    For example: If appointment is on 25 October, cutoff is 24 October 23:59:59.999999 in clinic timezone.
    Once the clinic's local date reaches 25 October (00:00:00), patient actions are no longer permitted.
    """
    tz_name = appointment.clinic.timezone or "Asia/Kolkata"
    try:
        clinic_tz = ZoneInfo(tz_name)
    except Exception:
        clinic_tz = ZoneInfo("Asia/Kolkata")

    start_at_local = appointment.start_at.astimezone(clinic_tz)
    appt_local_date = start_at_local.date()
    day_before = appt_local_date - timedelta(days=1)
    return datetime.combine(day_before, time(23, 59, 59, 999999), tzinfo=clinic_tz)


def check_patient_cancellation_eligibility(
    appointment: Appointment, current_time: Optional[datetime] = None
) -> Tuple[bool, Optional[str], bool]:
    """
    Validates whether a patient is currently permitted to cancel this appointment.
    Returns:
        (is_eligible: bool, error_message: Optional[str], is_exception: bool)
    """
    if appointment.status == AppointmentStatus.CANCELLED:
        raise InvalidAppointmentStateException(_("This appointment is already cancelled."))

    if appointment.status == AppointmentStatus.COMPLETED:
        raise InvalidAppointmentStateException(_("Completed appointments cannot be cancelled."))

    if appointment.status == AppointmentStatus.NO_SHOW:
        raise InvalidAppointmentStateException(_("No-show appointments cannot be cancelled."))

    if appointment.status not in (
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.PENDING_CONFIRMATION,
        AppointmentStatus.RESCHEDULE_REQUIRED,
    ):
        raise InvalidAppointmentStateException(
            _("Appointments in status '%(status)s' cannot be cancelled.")
            % {"status": appointment.status}
        )

    # Check authorized exception flag (e.g. doctor/clinic reported unavailability)
    if appointment.status == AppointmentStatus.RESCHEDULE_REQUIRED or appointment.reschedule_required:
        return True, None, True

    # Standard clinic-timezone cutoff policy check
    now = current_time or timezone.now()
    cutoff = get_appointment_cancellation_cutoff(appointment)
    if now > cutoff:
        return (
            False,
            _(
                "The cancellation cutoff for this appointment has passed. "
                "Cancellations are allowed until 11:59:59 PM on the calendar day before the appointment "
                "in the clinic's local timezone (%(tz)s)."
            )
            % {"tz": appointment.clinic.timezone or "Asia/Kolkata"},
            False,
        )

    return True, None, False


def check_patient_rescheduling_eligibility(
    appointment: Appointment, current_time: Optional[datetime] = None
) -> Tuple[bool, Optional[str], bool]:
    """
    Validates whether a patient is currently permitted to reschedule this appointment.
    Returns:
        (is_eligible: bool, error_message: Optional[str], is_exception: bool)
    """
    if appointment.status == AppointmentStatus.CANCELLED:
        raise InvalidAppointmentStateException(_("Cancelled appointments cannot be rescheduled."))

    if appointment.status == AppointmentStatus.COMPLETED:
        raise InvalidAppointmentStateException(_("Completed appointments cannot be rescheduled."))

    if appointment.status == AppointmentStatus.NO_SHOW:
        raise InvalidAppointmentStateException(_("No-show appointments cannot be rescheduled."))

    if appointment.status not in (
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.PENDING_CONFIRMATION,
        AppointmentStatus.RESCHEDULE_REQUIRED,
    ):
        raise InvalidAppointmentStateException(
            _("Appointments in status '%(status)s' cannot be rescheduled.")
            % {"status": appointment.status}
        )

    # Check authorized exception flag
    if appointment.status == AppointmentStatus.RESCHEDULE_REQUIRED or appointment.reschedule_required:
        return True, None, True

    # Standard clinic-timezone cutoff policy check
    now = current_time or timezone.now()
    cutoff = get_appointment_cancellation_cutoff(appointment)
    if now > cutoff:
        return (
            False,
            _(
                "The rescheduling cutoff for this appointment has passed. "
                "Rescheduling is allowed until 11:59:59 PM on the calendar day before the appointment "
                "in the clinic's local timezone (%(tz)s)."
            )
            % {"tz": appointment.clinic.timezone or "Asia/Kolkata"},
            False,
        )

    return True, None, False


def cancel_appointment(
    appointment: Appointment,
    cancelled_by: User,
    reason: str = "",
    is_exception: bool = False,
    actor_role: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> Appointment:
    """
    Atomically cancels an appointment with state transition checks, cutoff enforcement,
    audit history logging, and immediate restoration of doctor slot availability.
    """
    if not cancelled_by or not cancelled_by.is_authenticated:
        raise InvalidBookingException(_("Authentication required to cancel an appointment."))

    effective_role = actor_role or getattr(cancelled_by, "role", UserRole.PATIENT)

    with transaction.atomic():
        # Re-fetch and lock appointment
        try:
            locked_appt = (
                Appointment.objects.select_for_update()
                .select_related("clinic", "doctor", "patient")
                .get(id=appointment.id)
            )
        except Appointment.DoesNotExist:
            raise InvalidBookingException(_("Appointment not found."))

        # If patient is cancelling, enforce patient eligibility & cutoff rules
        if effective_role == UserRole.PATIENT:
            is_eligible, err_msg, used_exception = check_patient_cancellation_eligibility(
                locked_appt, current_time=current_time
            )
            if not is_eligible:
                raise CutoffExceededException(err_msg)
            if used_exception:
                is_exception = True
        else:
            # Authorized clinic / doctor / admin override
            if locked_appt.status == AppointmentStatus.CANCELLED:
                raise InvalidAppointmentStateException(_("This appointment is already cancelled."))
            if locked_appt.status == AppointmentStatus.COMPLETED:
                raise InvalidAppointmentStateException(_("Completed appointments cannot be cancelled."))
            is_exception = True

        prev_status = locked_appt.status
        now_utc = current_time or timezone.now()

        locked_appt.status = AppointmentStatus.CANCELLED
        locked_appt.cancellation_reason = reason.strip() if reason else ""
        locked_appt.cancelled_at = now_utc
        locked_appt.cancelled_by = cancelled_by
        locked_appt.reschedule_required = False
        locked_appt.save(
            update_fields=[
                "status",
                "cancellation_reason",
                "cancelled_at",
                "cancelled_by",
                "reschedule_required",
                "updated_at",
            ]
        )

        # Record append-only history audit
        event_type = (
            AppointmentHistoryEventType.PATIENT_CANCELLED
            if effective_role == UserRole.PATIENT
            else AppointmentHistoryEventType.CLINIC_CANCELLED
        )
        AppointmentHistory.objects.create(
            appointment=locked_appt,
            event_type=event_type,
            previous_status=prev_status,
            new_status=AppointmentStatus.CANCELLED,
            previous_start_at=locked_appt.start_at,
            previous_end_at=locked_appt.end_at,
            actor=cancelled_by,
            actor_role=effective_role,
            reason=reason.strip() if reason else "",
            is_exception=is_exception,
            metadata={
                "action": "cancel",
                "clinic_timezone": locked_appt.clinic.timezone or "Asia/Kolkata",
            },
        )

        # Deferred notification hook
        transaction.on_commit(
            lambda: dispatch_appointment_event(
                "appointment_cancelled",
                locked_appt.id,
                reason=reason,
                cancelled_by_id=cancelled_by.id,
            )
        )

        return locked_appt


def reschedule_appointment(
    appointment: Appointment,
    rescheduled_by: User,
    new_start_at: datetime,
    reason: str = "",
    is_exception: bool = False,
    actor_role: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> Appointment:
    """
    Atomically reschedules an appointment to a new date/time:
    - Enforces clinic timezone cutoff rules (with exception support).
    - Validates that new slot is in the future and timezone-aware.
    - Validates doctor's working shifts, unavailabilities, and administrative blocks.
    - Prevents direct conflicts with OTHER active appointments for this doctor.
    - Enforces cross-clinic travel buffer rules.
    - Records atomic audit history with previous and new start/end timestamps.
    - Fails cleanly leaving original appointment untouched if slot is unavailable.
    """
    if not rescheduled_by or not rescheduled_by.is_authenticated:
        raise InvalidBookingException(_("Authentication required to reschedule an appointment."))

    if not timezone.is_aware(new_start_at):
        raise InvalidBookingException(_("New appointment start timestamp must be timezone-aware."))

    now_utc = current_time or timezone.now()
    if new_start_at <= now_utc:
        raise InvalidBookingException(_("Cannot reschedule to a slot in the past."))

    effective_role = actor_role or getattr(rescheduled_by, "role", UserRole.PATIENT)

    with transaction.atomic():
        # 1. Lock doctor record to serialize doctor bookings/reschedulings globally
        try:
            Doctor.objects.select_for_update().get(id=appointment.doctor_id)
        except Doctor.DoesNotExist:
            raise InvalidBookingException(_("Doctor profile not found."))

        # 2. Lock and re-fetch appointment record
        try:
            locked_appt = (
                Appointment.objects.select_for_update()
                .select_related("clinic", "doctor", "doctor_clinic", "patient")
                .get(id=appointment.id)
            )
        except Appointment.DoesNotExist:
            raise InvalidBookingException(_("Appointment not found."))

        # 3. State & Cutoff Validation
        if effective_role == UserRole.PATIENT:
            is_eligible, err_msg, used_exception = check_patient_rescheduling_eligibility(
                locked_appt, current_time=current_time
            )
            if not is_eligible:
                raise CutoffExceededException(err_msg)
            if used_exception:
                is_exception = True
        else:
            # Authorized clinic / staff / admin rescheduling
            if locked_appt.status == AppointmentStatus.CANCELLED:
                raise InvalidAppointmentStateException(_("Cancelled appointments cannot be rescheduled."))
            if locked_appt.status == AppointmentStatus.COMPLETED:
                raise InvalidAppointmentStateException(_("Completed appointments cannot be rescheduled."))
            if locked_appt.status == AppointmentStatus.NO_SHOW:
                raise InvalidAppointmentStateException(_("No-show appointments cannot be rescheduled."))
            is_exception = True

        # 4. Association & Clinic Validation
        locked_dc = (
            DoctorClinic.objects.select_related("doctor", "clinic", "doctor__user")
            .get(id=locked_appt.doctor_clinic_id)
        )
        if locked_dc.status != DoctorClinicStatus.ACTIVE or locked_dc.clinic.status != ClinicStatus.APPROVED:
            raise InvalidBookingException(_("Doctor or clinic affiliation is no longer active."))

        tz_name = locked_dc.clinic.timezone or "Asia/Kolkata"
        try:
            clinic_tz = ZoneInfo(tz_name)
        except Exception:
            clinic_tz = ZoneInfo("Asia/Kolkata")

        start_at_local = new_start_at.astimezone(clinic_tz)
        target_date = start_at_local.date()
        start_time_str = start_at_local.strftime("%H:%M")

        # 5. Validate availability on target date
        availability_data = generate_doctor_availability_slots(
            doctor_clinic=locked_dc,
            target_date=target_date,
        )
        if not availability_data.get("is_eligible"):
            err = availability_data.get("eligibility_error") or _("Doctor is not eligible on this date.")
            raise InvalidBookingException(err)

        matching_slot = None
        for s in availability_data.get("slots", []):
            if s["start_time"] == start_time_str:
                matching_slot = s
                break

        if not matching_slot:
            raise SlotUnavailableException(_("The requested time does not match an active doctor shift slot."))

        duration_minutes = matching_slot["duration_minutes"]
        new_end_at = new_start_at + timedelta(minutes=duration_minutes)

        # 6. Physical overlap check against active appointments (excluding current appointment)
        blocking_statuses = [
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.PENDING_CONFIRMATION,
            AppointmentStatus.COMPLETED,
        ]

        direct_conflict = (
            Appointment.objects.filter(
                doctor_id=locked_appt.doctor_id,
                status__in=blocking_statuses,
                start_at__lt=new_end_at,
                end_at__gt=new_start_at,
            )
            .exclude(id=locked_appt.id)
            .exists()
        )
        if direct_conflict:
            raise SlotUnavailableException(
                _("Slot conflict: The selected slot is already booked for this doctor.")
            )

        # 7. Cross-clinic travel buffer check (excluding current appointment)
        travel_buffer_mins = max(30, locked_dc.appointment_duration_minutes)
        buffer_delta = timedelta(minutes=travel_buffer_mins)

        other_clinic_appts = (
            Appointment.objects.filter(
                doctor_id=locked_appt.doctor_id,
                status__in=blocking_statuses,
            )
            .exclude(clinic=locked_dc.clinic)
            .exclude(id=locked_appt.id)
            .filter(
                start_at__lt=new_end_at + buffer_delta,
                end_at__gt=new_start_at - buffer_delta,
            )
        )
        if other_clinic_appts.exists():
            conflicting_clinic = other_clinic_appts.first().clinic.name
            raise SlotUnavailableException(
                _(
                    "Cross-clinic schedule conflict: A %(buffer)d-minute travel buffer is required between clinic visits (conflict with '%(clinic)s')."
                )
                % {"buffer": travel_buffer_mins, "clinic": conflicting_clinic}
            )

        # 8. Check doctor unavailability and administrative blocked slots from slot calculation
        if not matching_slot["is_available"]:
            reason_text = matching_slot.get("reason", "")
            # If slot is unavailable due to something OTHER than this appointment itself, reject
            if "already booked" not in reason_text.lower():
                raise SlotUnavailableException(
                    _("The selected slot is unavailable: %(reason)s") % {"reason": reason_text}
                )

        # 9. Update appointment details atomically
        prev_status = locked_appt.status
        prev_start_at = locked_appt.start_at
        prev_end_at = locked_appt.end_at

        locked_appt.start_at = new_start_at
        locked_appt.end_at = new_end_at
        locked_appt.status = AppointmentStatus.CONFIRMED
        locked_appt.reschedule_required = False
        locked_appt.cancellation_reason = ""
        locked_appt.save(
            update_fields=[
                "start_at",
                "end_at",
                "status",
                "reschedule_required",
                "cancellation_reason",
                "updated_at",
            ]
        )

        # 10. Record append-only history audit
        AppointmentHistory.objects.create(
            appointment=locked_appt,
            event_type=AppointmentHistoryEventType.RESCHEDULED,
            previous_status=prev_status,
            new_status=AppointmentStatus.CONFIRMED,
            previous_start_at=prev_start_at,
            previous_end_at=prev_end_at,
            new_start_at=new_start_at,
            new_end_at=new_end_at,
            actor=rescheduled_by,
            actor_role=effective_role,
            reason=reason.strip() if reason else "",
            is_exception=is_exception,
            metadata={
                "action": "reschedule",
                "clinic_timezone": tz_name,
            },
        )

        # 11. Deferred notification hook
        transaction.on_commit(
            lambda: dispatch_appointment_event(
                "appointment_rescheduled",
                locked_appt.id,
                new_start_at=new_start_at.isoformat(),
                rescheduled_by_id=rescheduled_by.id,
            )
        )

        return locked_appt


def report_doctor_unavailability_for_appointment(
    appointment: Appointment,
    reported_by: User,
    reason: str = "",
    action: str = "RESCHEDULE_REQUIRED",
) -> Appointment:
    """
    Marks an appointment as requiring resolution due to doctor or clinic unavailability,
    or cancels it directly if requested by authorized staff.
    Enables affected patients to reschedule or cancel even past normal cutoff.
    """
    if not reported_by or not reported_by.is_authenticated:
        raise InvalidBookingException(_("Authentication required."))

    with transaction.atomic():
        try:
            locked_appt = (
                Appointment.objects.select_for_update()
                .select_related("clinic", "doctor", "patient")
                .get(id=appointment.id)
            )
        except Appointment.DoesNotExist:
            raise InvalidBookingException(_("Appointment not found."))

        if locked_appt.status == AppointmentStatus.CANCELLED:
            raise InvalidAppointmentStateException(_("This appointment is already cancelled."))
        if locked_appt.status == AppointmentStatus.COMPLETED:
            raise InvalidAppointmentStateException(_("Completed appointments cannot be marked unavailable."))

        if action == "CANCEL":
            return cancel_appointment(
                locked_appt,
                cancelled_by=reported_by,
                reason=reason or _("Doctor/clinic unavailability"),
                is_exception=True,
                actor_role=reported_by.role,
            )

        prev_status = locked_appt.status
        locked_appt.status = AppointmentStatus.RESCHEDULE_REQUIRED
        locked_appt.reschedule_required = True
        locked_appt.cancellation_reason = reason.strip() if reason else _("Doctor reported unavailability.")
        locked_appt.save(
            update_fields=[
                "status",
                "reschedule_required",
                "cancellation_reason",
                "updated_at",
            ]
        )

        AppointmentHistory.objects.create(
            appointment=locked_appt,
            event_type=AppointmentHistoryEventType.DOCTOR_UNAVAILABLE,
            previous_status=prev_status,
            new_status=AppointmentStatus.RESCHEDULE_REQUIRED,
            previous_start_at=locked_appt.start_at,
            previous_end_at=locked_appt.end_at,
            actor=reported_by,
            actor_role=reported_by.role,
            reason=reason.strip() if reason else "",
            is_exception=True,
            metadata={"action": "doctor_unavailable"},
        )

        transaction.on_commit(
            lambda: dispatch_appointment_event(
                "doctor_unavailability_reported",
                locked_appt.id,
                reason=reason,
                reported_by_id=reported_by.id,
            )
        )

        return locked_appt


def complete_appointment(appointment: Appointment, user: User) -> Appointment:
    """Marks an appointment as COMPLETED."""
    if appointment.status == AppointmentStatus.CANCELLED:
        raise InvalidAppointmentStateException(_("Cancelled appointments cannot be marked completed."))

    with transaction.atomic():
        locked_appt = Appointment.objects.select_for_update().get(id=appointment.id)
        prev_status = locked_appt.status
        locked_appt.status = AppointmentStatus.COMPLETED
        locked_appt.save(update_fields=["status", "updated_at"])

        AppointmentHistory.objects.create(
            appointment=locked_appt,
            event_type=AppointmentHistoryEventType.COMPLETED,
            previous_status=prev_status,
            new_status=AppointmentStatus.COMPLETED,
            actor=user,
            actor_role=getattr(user, "role", ""),
            reason=_("Consultation completed."),
        )

        return locked_appt


def mark_no_show(appointment: Appointment, user: User) -> Appointment:
    """Marks an appointment as NO_SHOW."""
    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise InvalidAppointmentStateException(_("Cannot mark a completed or cancelled appointment as No-Show."))

    with transaction.atomic():
        locked_appt = Appointment.objects.select_for_update().get(id=appointment.id)
        prev_status = locked_appt.status
        locked_appt.status = AppointmentStatus.NO_SHOW
        locked_appt.save(update_fields=["status", "updated_at"])

        AppointmentHistory.objects.create(
            appointment=locked_appt,
            event_type=AppointmentHistoryEventType.NO_SHOW,
            previous_status=prev_status,
            new_status=AppointmentStatus.NO_SHOW,
            actor=user,
            actor_role=getattr(user, "role", ""),
            reason=_("Patient did not show up for scheduled consultation."),
        )

        return locked_appt

