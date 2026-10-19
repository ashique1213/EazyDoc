from datetime import datetime, time, timedelta, timezone as dt_timezone
import hashlib
import secrets
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.schedules.services import generate_doctor_availability_slots
from .exceptions import (
    IdempotencyConflictException,
    InvalidBookingException,
    SlotUnavailableException,
)
from .models import Appointment, AppointmentIdempotency, AppointmentStatus


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

        # 11. Persist Idempotency record (Rule 8)
        if idempotency_key:
            AppointmentIdempotency.objects.create(
                patient=patient,
                idempotency_key=idempotency_key,
                request_hash=req_hash,
                appointment=appointment,
                response_status_code=201,
            )

        return appointment, True


def cancel_appointment(appointment: Appointment, cancelled_by: User, reason: str = "") -> Appointment:
    """Cancels an appointment with status transition validation."""
    if appointment.status == AppointmentStatus.CANCELLED:
        return appointment

    if appointment.status == AppointmentStatus.COMPLETED:
        raise InvalidBookingException(_("Completed appointments cannot be cancelled."))

    appointment.status = AppointmentStatus.CANCELLED
    if reason:
        prefix = f"[Cancelled by {cancelled_by.email}: {reason}]"
        appointment.patient_note = f"{appointment.patient_note}\n{prefix}".strip()
    appointment.save(update_fields=["status", "patient_note", "updated_at"])
    return appointment


def complete_appointment(appointment: Appointment, user: User) -> Appointment:
    """Marks an appointment as COMPLETED."""
    if appointment.status == AppointmentStatus.CANCELLED:
        raise InvalidBookingException(_("Cancelled appointments cannot be marked completed."))

    appointment.status = AppointmentStatus.COMPLETED
    appointment.save(update_fields=["status", "updated_at"])
    return appointment


def mark_no_show(appointment: Appointment, user: User) -> Appointment:
    """Marks an appointment as NO_SHOW."""
    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise InvalidBookingException(_("Cannot mark a completed or cancelled appointment as No-Show."))

    appointment.status = AppointmentStatus.NO_SHOW
    appointment.save(update_fields=["status", "updated_at"])
    return appointment
