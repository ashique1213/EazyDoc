import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from django.db.models import Count, Prefetch, Q
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus, Specialization
from apps.schedules.services import generate_doctor_availability_slots

from .pagination import StandardResultsSetPagination
from .serializers import (
    PublicClinicDetailSerializer,
    PublicClinicListSerializer,
    PublicDoctorDetailSerializer,
    PublicDoctorListSerializer,
    PublicSpecializationSerializer,
)


class PublicDoctorSearchView(APIView):
    """
    Public search and discovery for verified healthcare practitioners.
    Guarantees that only verified doctors with active clinic associations are returned.
    Safely prevents doctor record duplication across multi-clinic affiliations.
    """
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="Search Public Doctors",
        description="Filter and search verified doctors by name, specialization, city, area, clinic, and availability date.",
        parameters=[
            OpenApiParameter(name="search", type=str, description="Doctor name or keyword search", required=False),
            OpenApiParameter(name="specialization", type=str, description="Filter by primary medical specialty", required=False),
            OpenApiParameter(name="city", type=str, description="Filter by clinic city", required=False),
            OpenApiParameter(name="area", type=str, description="Filter by clinic locality / address / pincode", required=False),
            OpenApiParameter(name="clinic", type=str, description="Filter by clinic name, slug, or ID", required=False),
            OpenApiParameter(name="date", type=str, description="Requested appointment date (YYYY-MM-DD)", required=False),
            OpenApiParameter(
                name="ordering",
                type=str,
                description="Sort order (name, -name, experience, -experience, created_at, -created_at)",
                required=False,
            ),
            OpenApiParameter(name="page", type=int, description="Page number", required=False),
            OpenApiParameter(name="page_size", type=int, description="Results per page (max 50)", required=False),
        ],
        responses={200: PublicDoctorListSerializer(many=True)},
    )
    def get(self, request):
        search_query = request.query_params.get("search", "").strip()[:100]
        specialization = request.query_params.get("specialization", "").strip()[:100]
        city = request.query_params.get("city", "").strip()[:100]
        area = request.query_params.get("area", "").strip()[:100]
        clinic_param = request.query_params.get("clinic", "").strip()[:100]
        date_param = request.query_params.get("date", "").strip()
        ordering_param = request.query_params.get("ordering", "name").strip()

        # 1. Base eligibility: Verified doctor, active user account, not suspended, with at least one active approved clinic association
        base_qs = Doctor.objects.filter(
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
            user__is_active=True,
            user__status=UserStatus.ACTIVE,
            clinic_associations__status=DoctorClinicStatus.ACTIVE,
            clinic_associations__clinic__status=ClinicStatus.APPROVED,
        )

        # 2. Text Search: Doctor full name or specialization
        if search_query:
            base_qs = base_qs.filter(
                Q(full_name__icontains=search_query)
                | Q(specialization__icontains=search_query)
                | Q(clinic_associations__clinic__name__icontains=search_query)
            )

        # 3. Specialization Filter
        if specialization:
            base_qs = base_qs.filter(
                Q(specialization__iexact=specialization) | Q(specialization__icontains=specialization)
            )

        # 4. Association-level Filters (City, Area, Clinic)
        clinic_filter_q = Q(status=DoctorClinicStatus.ACTIVE, clinic__status=ClinicStatus.APPROVED)
        has_association_filter = False

        if city:
            base_qs = base_qs.filter(
                clinic_associations__status=DoctorClinicStatus.ACTIVE,
                clinic_associations__clinic__status=ClinicStatus.APPROVED,
                clinic_associations__clinic__city__iexact=city,
            )
            clinic_filter_q &= Q(clinic__city__iexact=city)
            has_association_filter = True

        if area:
            base_qs = base_qs.filter(
                clinic_associations__status=DoctorClinicStatus.ACTIVE,
                clinic_associations__clinic__status=ClinicStatus.APPROVED,
            ).filter(
                Q(clinic_associations__clinic__address_line_1__icontains=area)
                | Q(clinic_associations__clinic__address_line_2__icontains=area)
                | Q(clinic_associations__clinic__pincode__icontains=area)
            )
            clinic_filter_q &= (
                Q(clinic__address_line_1__icontains=area)
                | Q(clinic__address_line_2__icontains=area)
                | Q(clinic__pincode__icontains=area)
            )
            has_association_filter = True

        if clinic_param:
            is_uuid = False
            try:
                parsed_uuid = uuid.UUID(clinic_param)
                is_uuid = True
            except ValueError:
                is_uuid = False

            if is_uuid:
                base_qs = base_qs.filter(
                    clinic_associations__status=DoctorClinicStatus.ACTIVE,
                    clinic_associations__clinic__status=ClinicStatus.APPROVED,
                    clinic_associations__clinic__id=parsed_uuid,
                )
                clinic_filter_q &= Q(clinic_id=parsed_uuid)
            else:
                base_qs = base_qs.filter(
                    clinic_associations__status=DoctorClinicStatus.ACTIVE,
                    clinic_associations__clinic__status=ClinicStatus.APPROVED,
                ).filter(
                    Q(clinic_associations__clinic__slug__iexact=clinic_param)
                    | Q(clinic_associations__clinic__name__icontains=clinic_param)
                )
                clinic_filter_q &= (
                    Q(clinic__slug__iexact=clinic_param) | Q(clinic__name__icontains=clinic_param)
                )
            has_association_filter = True

        # 5. Optional Date Filter
        if date_param:
            target_date = parse_date(date_param)
            if not target_date:
                raise ValidationError({"date": "Invalid date format. Expected YYYY-MM-DD."})
            # Doctors with recurring shift on this weekday
            weekday = target_date.weekday()
            base_qs = base_qs.filter(
                clinic_associations__schedules__day_of_week=weekday,
                clinic_associations__schedules__is_active=True,
            )

        # 6. Distinct to guarantee no doctor duplicate across multiple clinics
        base_qs = base_qs.distinct()

        # 7. Safe deterministic ordering
        ordering_map = {
            "name": ["full_name", "id"],
            "-name": ["-full_name", "id"],
            "full_name": ["full_name", "id"],
            "-full_name": ["-full_name", "id"],
            "experience": ["years_of_experience", "full_name", "id"],
            "-experience": ["-years_of_experience", "full_name", "id"],
            "created_at": ["created_at", "id"],
            "-created_at": ["-created_at", "id"],
        }
        order_fields = ordering_map.get(ordering_param, ["full_name", "id"])
        base_qs = base_qs.order_by(*order_fields)

        # 8. Optimized Prefetch
        # If user filtered by clinic/city/area, only prefetch matching practice locations
        locations_qs = DoctorClinic.objects.filter(clinic_filter_q).select_related("clinic")
        base_qs = base_qs.select_related("user").prefetch_related(
            Prefetch("clinic_associations", queryset=locations_qs, to_attr="prefetched_eligible_locations")
        )

        # 9. Pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(base_qs, request, view=self)

        # Attach filtered_locations to each doctor instance
        for doc in page:
            doc.filtered_locations = getattr(doc, "prefetched_eligible_locations", [])

        serializer = PublicDoctorListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class PublicDoctorDetailView(APIView):
    """
    Public profile for an individual verified doctor.
    Returns doctor credentials, verification indicator, and active clinic practice locations with fees.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Retrieve Public Doctor Profile",
        description="Returns verified doctor public profile and eligible clinic practice locations.",
        responses={200: PublicDoctorDetailSerializer},
    )
    def get(self, request, doctor_id):
        # Lookup doctor
        try:
            doc_uuid = uuid.UUID(str(doctor_id))
        except ValueError:
            raise NotFound("Invalid doctor identifier.")

        try:
            doctor = Doctor.objects.select_related("user").prefetch_related(
                Prefetch(
                    "clinic_associations",
                    queryset=DoctorClinic.objects.filter(
                        status=DoctorClinicStatus.ACTIVE,
                        clinic__status=ClinicStatus.APPROVED,
                    ).select_related("clinic"),
                )
            ).get(
                pk=doc_uuid,
                verification_status=DoctorVerificationStatus.VERIFIED,
                is_verified=True,
                user__is_active=True,
                user__status=UserStatus.ACTIVE,
            )
        except Doctor.DoesNotExist:
            raise NotFound("Doctor profile not found or is currently ineligible for public display.")

        # Ensure doctor has at least one active approved clinic association
        active_locations = [
            assoc for assoc in doctor.clinic_associations.all()
            if assoc.status == DoctorClinicStatus.ACTIVE and assoc.clinic.status == ClinicStatus.APPROVED
        ]
        if not active_locations:
            raise NotFound("Doctor profile has no active clinic practice locations.")

        serializer = PublicDoctorDetailSerializer(doctor, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicClinicSearchView(APIView):
    """
    Public search and discovery for approved clinics.
    Returns clinic profile, public contact, location, and count of associated doctors.
    """
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="Search Public Clinics",
        description="Filter and search approved clinics by name, city, area, and services.",
        parameters=[
            OpenApiParameter(name="search", type=str, description="Clinic name or description keyword", required=False),
            OpenApiParameter(name="city", type=str, description="Filter by city", required=False),
            OpenApiParameter(name="area", type=str, description="Filter by address / pincode / locality", required=False),
            OpenApiParameter(name="service", type=str, description="Filter by services or keywords", required=False),
            OpenApiParameter(
                name="ordering",
                type=str,
                description="Sort order (name, -name, city, -city, created_at, -created_at)",
                required=False,
            ),
            OpenApiParameter(name="page", type=int, description="Page number", required=False),
            OpenApiParameter(name="page_size", type=int, description="Results per page (max 50)", required=False),
        ],
        responses={200: PublicClinicListSerializer(many=True)},
    )
    def get(self, request):
        search_query = request.query_params.get("search", "").strip()[:100]
        city = request.query_params.get("city", "").strip()[:100]
        area = request.query_params.get("area", "").strip()[:100]
        service = request.query_params.get("service", "").strip()[:100]
        ordering_param = request.query_params.get("ordering", "name").strip()

        # 1. Base eligibility: Approved and active clinic
        base_qs = Clinic.objects.filter(
            status=ClinicStatus.APPROVED,
            is_verified=True,
        )

        # 2. Text Search
        if search_query:
            base_qs = base_qs.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            )

        # 3. City Filter
        if city:
            base_qs = base_qs.filter(city__iexact=city)

        # 4. Area / Locality Filter
        if area:
            base_qs = base_qs.filter(
                Q(address_line_1__icontains=area)
                | Q(address_line_2__icontains=area)
                | Q(pincode__icontains=area)
            )

        # 5. Service Filter
        if service:
            base_qs = base_qs.filter(
                Q(description__icontains=service) | Q(name__icontains=service)
            )

        # 6. Annotate with count of verified active doctors
        base_qs = base_qs.annotate(
            doctor_count=Count(
                "doctor_associations",
                filter=Q(
                    doctor_associations__status=DoctorClinicStatus.ACTIVE,
                    doctor_associations__doctor__verification_status=DoctorVerificationStatus.VERIFIED,
                    doctor_associations__doctor__user__is_active=True,
                    doctor_associations__doctor__user__status=UserStatus.ACTIVE,
                ),
                distinct=True,
            )
        )

        # 7. Safe ordering
        ordering_map = {
            "name": ["name", "id"],
            "-name": ["-name", "id"],
            "city": ["city", "name", "id"],
            "-city": ["-city", "name", "id"],
            "created_at": ["created_at", "id"],
            "-created_at": ["-created_at", "id"],
        }
        order_fields = ordering_map.get(ordering_param, ["name", "id"])
        base_qs = base_qs.order_by(*order_fields)

        # 8. Pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(base_qs, request, view=self)
        serializer = PublicClinicListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class PublicClinicDetailView(APIView):
    """
    Public profile for an individual approved clinic.
    Returns public clinic operational info and currently associated verified doctors.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Retrieve Public Clinic Profile",
        description="Returns approved clinic public details and its currently associated, publicly visible doctors.",
        responses={200: PublicClinicDetailSerializer},
    )
    def get(self, request, clinic_id):
        # Allow lookup by UUID or slug
        is_uuid = False
        try:
            clinic_uuid = uuid.UUID(str(clinic_id))
            is_uuid = True
        except ValueError:
            is_uuid = False

        qs = Clinic.objects.filter(
            status=ClinicStatus.APPROVED,
            is_verified=True,
        ).prefetch_related(
            Prefetch(
                "doctor_associations",
                queryset=DoctorClinic.objects.filter(
                    status=DoctorClinicStatus.ACTIVE,
                    doctor__verification_status=DoctorVerificationStatus.VERIFIED,
                    doctor__user__is_active=True,
                    doctor__user__status=UserStatus.ACTIVE,
                ).select_related("doctor"),
            )
        )

        try:
            if is_uuid:
                clinic = qs.get(pk=clinic_uuid)
            else:
                clinic = qs.get(slug__iexact=str(clinic_id))
        except Clinic.DoesNotExist:
            raise NotFound("Clinic not found or is currently ineligible for public display.")

        serializer = PublicClinicDetailSerializer(clinic, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicDoctorAvailabilityView(APIView):
    """
    Public availability slot retrieval for a specific doctor at a specific clinic on a given date.
    Integrates clinic timezone, shift recurring schedule, leaves, and blocked slots.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Query Public Doctor Availability Slots",
        description="Returns generated candidate slots for a doctor-clinic association on a given date using clinic timezone.",
        parameters=[
            OpenApiParameter(name="date", type=str, required=True, description="Target date (YYYY-MM-DD)"),
        ],
        responses={200: OpenApiResponse(description="Generated availability slots and fees.")},
    )
    def get(self, request, clinic_id, doctor_id):
        # Validate date
        date_str = request.query_params.get("date")
        if not date_str:
            raise ValidationError({"date": "The 'date' parameter (YYYY-MM-DD) is required."})

        target_date = parse_date(date_str)
        if not target_date:
            raise ValidationError({"date": "Invalid date format. Expected YYYY-MM-DD."})

        # Validate identifiers
        try:
            c_uuid = uuid.UUID(str(clinic_id))
            d_uuid = uuid.UUID(str(doctor_id))
        except ValueError:
            raise NotFound("Invalid clinic or doctor identifier.")

        # Find active association
        try:
            doctor_clinic = DoctorClinic.objects.select_related(
                "doctor__user", "clinic"
            ).get(
                clinic_id=c_uuid,
                doctor_id=d_uuid,
                status=DoctorClinicStatus.ACTIVE,
                clinic__status=ClinicStatus.APPROVED,
                doctor__verification_status=DoctorVerificationStatus.VERIFIED,
                doctor__user__is_active=True,
            )
        except DoctorClinic.DoesNotExist:
            raise NotFound("No active affiliation found between the specified doctor and clinic.")

        # Generate slots using existing service
        availability = generate_doctor_availability_slots(
            doctor_clinic=doctor_clinic,
            target_date=target_date,
        )

        # Enhance response with commercial terms for user convenience
        availability["pricing"] = {
            "consultation_fee": str(doctor_clinic.consultation_fee),
            "follow_up_fee": str(doctor_clinic.follow_up_fee),
            "appointment_duration_minutes": doctor_clinic.appointment_duration_minutes,
        }

        return Response(availability, status=status.HTTP_200_OK)


class PublicSpecializationListView(APIView):
    """
    Public catalog of medical specializations for search filter dropdowns.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List Public Medical Specializations",
        description="Returns all active medical specializations for filter menus.",
        responses={200: PublicSpecializationSerializer(many=True)},
    )
    def get(self, request):
        specializations = Specialization.objects.all().order_by("name")
        serializer = PublicSpecializationSerializer(specializations, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)


class PublicCityListView(APIView):
    """
    Public list of distinct cities where approved clinics are located.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List Active Clinic Cities",
        description="Returns distinct cities where approved clinics currently operate.",
        responses={200: OpenApiResponse(description="List of active cities.")},
    )
    def get(self, request):
        cities = (
            Clinic.objects.filter(status=ClinicStatus.APPROVED, is_verified=True)
            .values_list("city", flat=True)
            .distinct()
            .order_by("city")
        )
        clean_cities = [c for c in cities if c]
        return Response({"success": True, "data": clean_cities}, status=status.HTTP_200_OK)
