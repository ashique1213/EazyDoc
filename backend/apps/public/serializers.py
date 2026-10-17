from decimal import Decimal
from typing import List, Optional
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.clinics.models import Clinic, DoctorClinic
from apps.doctors.models import Doctor, Specialization


class PublicClinicLocationSerializer(serializers.Serializer):
    """
    Public representation of a clinic location where a doctor actively practices.
    Maintains clean separation of clinic-specific commercial fees and operational parameters.
    """
    doctor_clinic_id = serializers.UUIDField(source="id", read_only=True)
    clinic_id = serializers.UUIDField(source="clinic.id", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    clinic_slug = serializers.CharField(source="clinic.slug", read_only=True)
    address_line_1 = serializers.CharField(source="clinic.address_line_1", read_only=True)
    address_line_2 = serializers.CharField(source="clinic.address_line_2", read_only=True, allow_null=True)
    city = serializers.CharField(source="clinic.city", read_only=True)
    state = serializers.CharField(source="clinic.state", read_only=True)
    pincode = serializers.CharField(source="clinic.pincode", read_only=True)
    country = serializers.CharField(source="clinic.country", read_only=True)
    phone = serializers.CharField(source="clinic.phone", read_only=True)
    email = serializers.EmailField(source="clinic.email", read_only=True)
    logo = serializers.ImageField(source="clinic.logo", read_only=True, allow_null=True)
    timezone = serializers.CharField(source="clinic.timezone", read_only=True)
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    follow_up_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    appointment_duration_minutes = serializers.IntegerField(read_only=True)


class PublicDoctorListSerializer(serializers.ModelSerializer):
    """
    Safe public summary serializer for doctor search results.
    Includes verified credentials, experience, and eligible practice locations.
    """
    profile_photo = serializers.ImageField(read_only=True, allow_null=True)
    practice_locations = serializers.SerializerMethodField()
    min_consultation_fee = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            "id",
            "full_name",
            "specialization",
            "qualifications",
            "years_of_experience",
            "languages",
            "bio",
            "profile_photo",
            "is_verified",
            "practice_locations",
            "min_consultation_fee",
        ]
        read_only_fields = fields

    @extend_schema_field(PublicClinicLocationSerializer(many=True))
    def get_practice_locations(self, obj: Doctor):
        # Locations passed or prefetched on doctor
        locations = getattr(obj, "filtered_locations", None)
        if locations is None:
            locations = [
                assoc for assoc in obj.clinic_associations.all()
                if assoc.status == "ACTIVE" and assoc.clinic.status == "APPROVED"
            ]
        return PublicClinicLocationSerializer(locations, many=True, context=self.context).data

    def get_min_consultation_fee(self, obj: Doctor) -> Optional[Decimal]:
        locations = getattr(obj, "filtered_locations", None)
        if locations is None:
            locations = [
                assoc for assoc in obj.clinic_associations.all()
                if assoc.status == "ACTIVE" and assoc.clinic.status == "APPROVED"
            ]
        if not locations:
            return None
        fees = [loc.consultation_fee for loc in locations if loc.consultation_fee is not None]
        return min(fees) if fees else None


class PublicDoctorDetailSerializer(serializers.ModelSerializer):
    """
    Detailed public doctor profile for doctor detail page.
    Exposes complete practitioner info, verified status, and practice clinics with fees.
    """
    profile_photo = serializers.ImageField(read_only=True, allow_null=True)
    practice_locations = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            "id",
            "full_name",
            "specialization",
            "qualifications",
            "years_of_experience",
            "languages",
            "bio",
            "profile_photo",
            "is_verified",
            "practice_locations",
        ]
        read_only_fields = fields

    @extend_schema_field(PublicClinicLocationSerializer(many=True))
    def get_practice_locations(self, obj: Doctor):
        locations = [
            assoc for assoc in obj.clinic_associations.all()
            if assoc.status == "ACTIVE" and assoc.clinic.status == "APPROVED"
        ]
        return PublicClinicLocationSerializer(locations, many=True, context=self.context).data


class PublicClinicListSerializer(serializers.ModelSerializer):
    """
    Public representation of a clinic in clinic search results.
    Includes basic address, branding, and count of verified associated doctors.
    """
    logo = serializers.ImageField(read_only=True, allow_null=True)
    doctor_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "country",
            "logo",
            "timezone",
            "doctor_count",
        ]
        read_only_fields = fields


class PublicClinicDoctorSummarySerializer(serializers.Serializer):
    """
    Public representation of a verified doctor practicing at a specific clinic.
    """
    doctor_id = serializers.UUIDField(source="doctor.id", read_only=True)
    doctor_clinic_id = serializers.UUIDField(source="id", read_only=True)
    full_name = serializers.CharField(source="doctor.full_name", read_only=True)
    specialization = serializers.CharField(source="doctor.specialization", read_only=True)
    qualifications = serializers.CharField(source="doctor.qualifications", read_only=True)
    years_of_experience = serializers.IntegerField(source="doctor.years_of_experience", read_only=True)
    languages = serializers.CharField(source="doctor.languages", read_only=True)
    bio = serializers.CharField(source="doctor.bio", read_only=True)
    profile_photo = serializers.ImageField(source="doctor.profile_photo", read_only=True, allow_null=True)
    is_verified = serializers.BooleanField(source="doctor.is_verified", read_only=True)
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    follow_up_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    appointment_duration_minutes = serializers.IntegerField(read_only=True)


class PublicClinicDetailSerializer(serializers.ModelSerializer):
    """
    Detailed public clinic profile with affiliated verified practitioners.
    """
    logo = serializers.ImageField(read_only=True, allow_null=True)
    doctors = serializers.SerializerMethodField()

    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "country",
            "logo",
            "timezone",
            "doctors",
        ]
        read_only_fields = fields

    @extend_schema_field(PublicClinicDoctorSummarySerializer(many=True))
    def get_doctors(self, obj: Clinic):
        associations = [
            assoc for assoc in obj.doctor_associations.all()
            if assoc.status == "ACTIVE"
            and assoc.doctor.verification_status == "VERIFIED"
            and assoc.doctor.user.is_active
        ]
        return PublicClinicDoctorSummarySerializer(associations, many=True, context=self.context).data


class PublicSpecializationSerializer(serializers.ModelSerializer):
    """Catalog of medical specializations for search filter dropdowns."""
    class Meta:
        model = Specialization
        fields = ["id", "name", "slug", "description"]
        read_only_fields = fields
