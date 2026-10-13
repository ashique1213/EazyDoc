from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.clinics.models import DoctorClinic
from apps.doctors.models import Doctor
from .exceptions import ScheduleConflictException
from .models import BlockedSlot, DoctorSchedule, DoctorUnavailability, Weekday
from .services import check_schedule_conflicts, validate_association_eligibility


class DoctorScheduleSerializer(serializers.ModelSerializer):
    """Read serializer with comprehensive doctor, clinic, and shift context."""

    doctor_id = serializers.UUIDField(source="doctor_clinic.doctor.id", read_only=True)
    doctor_name = serializers.CharField(source="doctor_clinic.doctor.full_name", read_only=True)
    doctor_specialization = serializers.CharField(source="doctor_clinic.doctor.specialization", read_only=True)
    clinic_id = serializers.UUIDField(source="doctor_clinic.clinic.id", read_only=True)
    clinic_name = serializers.CharField(source="doctor_clinic.clinic.name", read_only=True)
    clinic_timezone = serializers.CharField(source="doctor_clinic.clinic.timezone", read_only=True)
    weekday_name = serializers.SerializerMethodField()
    effective_slot_duration = serializers.IntegerField(read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor_clinic",
            "doctor_id",
            "doctor_name",
            "doctor_specialization",
            "clinic_id",
            "clinic_name",
            "clinic_timezone",
            "day_of_week",
            "weekday_name",
            "start_time",
            "end_time",
            "effective_from",
            "effective_until",
            "slot_duration_minutes",
            "effective_slot_duration",
            "buffer_minutes",
            "max_patients_per_slot",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_weekday_name(self, obj) -> str:
        return Weekday(obj.day_of_week).label


class DoctorScheduleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Write serializer for configuring doctor recurring working intervals.
    Validates association eligibility, shift duration, start/end times,
    and cross-clinic conflicts including travel buffers.
    """

    weekday = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor_clinic",
            "day_of_week",
            "weekday",
            "start_time",
            "end_time",
            "effective_from",
            "effective_until",
            "slot_duration_minutes",
            "buffer_minutes",
            "max_patients_per_slot",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        # Allow 'weekday' alias if supplied
        if "weekday" in attrs and "day_of_week" not in attrs:
            attrs["day_of_week"] = attrs.pop("weekday")

        doctor_clinic = attrs.get("doctor_clinic") or (self.instance.doctor_clinic if self.instance else None)
        day_of_week = attrs.get("day_of_week", getattr(self.instance, "day_of_week", None))
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        buffer_minutes = attrs.get("buffer_minutes", getattr(self.instance, "buffer_minutes", 0))

        if not doctor_clinic:
            raise serializers.ValidationError({"doctor_clinic": _("Doctor clinic association is required.")})

        # 1. Enforce business rules on doctor & clinic status
        validate_association_eligibility(doctor_clinic)

        # 2. Time interval validation
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({
                "end_time": _("Shift end time must be strictly after start time.")
            })

        effective_from = attrs.get("effective_from", getattr(self.instance, "effective_from", None))
        effective_until = attrs.get("effective_until", getattr(self.instance, "effective_until", None))
        if effective_from and effective_until and effective_from > effective_until:
            raise serializers.ValidationError({
                "effective_until": _("Effective until date must be on or after effective from date.")
            })

        slot_duration = attrs.get(
            "slot_duration_minutes", getattr(self.instance, "slot_duration_minutes", None)
        )
        if slot_duration is not None and (slot_duration < 5 or slot_duration > 240):
            raise serializers.ValidationError({
                "slot_duration_minutes": _("Slot duration must be between 5 and 240 minutes.")
            })

        # 3. Cross-Clinic and Same-Clinic Conflict & Travel Buffer Validation
        exclude_id = self.instance.pk if self.instance else None
        has_conflict, conflict_details = check_schedule_conflicts(
            doctor_id=doctor_clinic.doctor_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            clinic_id=doctor_clinic.clinic_id,
            exclude_schedule_id=exclude_id,
            buffer_minutes=buffer_minutes,
        )

        if has_conflict and conflict_details:
            raise ScheduleConflictException(
                detail=conflict_details.get("message"),
                conflict_data=conflict_details,
            )

        return attrs


class ScheduleConflictCheckSerializer(serializers.Serializer):
    """Payload serializer for dry-run schedule conflict checking."""

    doctor_clinic = serializers.PrimaryKeyRelatedField(queryset=DoctorClinic.objects.all())
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    buffer_minutes = serializers.IntegerField(required=False, default=0, min_value=0)
    exclude_schedule_id = serializers.UUIDField(required=False, allow_null=True)


class DoctorUnavailabilitySerializer(serializers.ModelSerializer):
    """Serializer for doctor leaves, time-off, and unavailability periods."""

    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True, allow_null=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = DoctorUnavailability
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "clinic",
            "clinic_name",
            "start_datetime",
            "end_datetime",
            "reason",
            "reason_display",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        start_dt = attrs.get("start_datetime") or getattr(self.instance, "start_datetime", None)
        end_dt = attrs.get("end_datetime") or getattr(self.instance, "end_datetime", None)
        if start_dt and end_dt and start_dt >= end_dt:
            raise serializers.ValidationError({
                "end_datetime": _("End datetime must be strictly after start datetime.")
            })
        return attrs


class BlockedSlotSerializer(serializers.ModelSerializer):
    """Serializer for administrative blocked slots."""

    doctor_name = serializers.CharField(source="doctor_clinic.doctor.full_name", read_only=True)
    clinic_name = serializers.CharField(source="doctor_clinic.clinic.name", read_only=True)

    class Meta:
        model = BlockedSlot
        fields = [
            "id",
            "doctor_clinic",
            "doctor_name",
            "clinic_name",
            "date",
            "start_time",
            "end_time",
            "reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
