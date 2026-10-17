from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
import uuid
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorDocument, DoctorDocumentType, DoctorVerificationStatus, Specialization
from apps.schedules.models import DoctorSchedule, Weekday


class PublicDiscoveryTests(APITestCase):
    """
    Comprehensive test suite for Public Doctor and Clinic Discovery (Day 8).
    Tests visibility rules, multi-clinic doctor semantics, public serializers,
    search & filtering, pagination, availability slots, and data isolation.
    """

    def setUp(self):
        # 1. Specializations
        self.spec_cardio = Specialization.objects.create(name="Cardiology", slug="cardiology")
        self.spec_derma = Specialization.objects.create(name="Dermatology", slug="dermatology")
        self.spec_pedia = Specialization.objects.create(name="Pediatrics", slug="pediatrics")

        # 2. Clinic Owners
        self.owner_1 = User.objects.create_user(
            email="owner1@apexclinic.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.owner_2 = User.objects.create_user(
            email="owner2@metrocare.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        # 3. Approved Clinics
        self.clinic_approved_1 = Clinic.objects.create(
            name="Apex Heart Institute",
            slug="apex-heart-institute",
            owner=self.owner_1,
            email="info@apexheart.com",
            phone="9876543201",
            address_line_1="42 Brigade Road",
            address_line_2="Indiranagar",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            description="Leading cardiac care hospital.",
        )
        self.clinic_approved_2 = Clinic.objects.create(
            name="Metro Skin & Child Clinic",
            slug="metro-skin-child",
            owner=self.owner_2,
            email="help@metrocare.com",
            phone="9876543202",
            address_line_1="88 Linking Road",
            city="Mumbai",
            state="Maharashtra",
            pincode="400050",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            description="Comprehensive skin and pediatric clinic.",
        )

        # 4. Inactive / Unapproved / Suspended Clinics
        self.clinic_pending = Clinic.objects.create(
            name="Pending Review Clinic",
            slug="pending-clinic",
            owner=self.owner_1,
            email="pending@clinic.com",
            phone="9876543203",
            address_line_1="10 Market St",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.PENDING,
        )
        self.clinic_suspended = Clinic.objects.create(
            name="Suspended Clinic Facility",
            slug="suspended-clinic",
            owner=self.owner_2,
            email="suspended@clinic.com",
            phone="9876543204",
            address_line_1="20 Closed Ave",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            status=ClinicStatus.SUSPENDED,
        )

        # 5. Doctors
        # Doctor A: Verified, Active, associated with BOTH clinic 1 (Bengaluru) and clinic 2 (Mumbai)
        self.user_doc_a = User.objects.create_user(
            email="dr.sharma@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor_a = Doctor.objects.create(
            user=self.user_doc_a,
            full_name="Dr. Priya Sharma",
            registration_number="KMC-112233",
            registration_council="Karnataka Medical Council",
            specialization="Cardiology",
            qualifications="MBBS, MD (Cardiology)",
            years_of_experience=12,
            bio="Senior Interventional Cardiologist with extensive clinical experience.",
            languages="English, Hindi, Kannada",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
            verification_notes="Internal admin note: All credentials verified.",
        )
        # Private document for Doctor A (must never leak)
        DoctorDocument.objects.create(
            doctor=self.doctor_a,
            document_type=DoctorDocumentType.REGISTRATION_CERTIFICATE,
            file="doctor_documents/private/secret_cert.pdf",
            file_name="secret_cert.pdf",
            file_size=1024,
            mime_type="application/pdf",
        )

        # Associations for Doctor A
        self.assoc_a1 = DoctorClinic.objects.create(
            doctor=self.doctor_a,
            clinic=self.clinic_approved_1,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("700.00"),
            follow_up_fee=Decimal("400.00"),
            appointment_duration_minutes=15,
        )
        self.assoc_a2 = DoctorClinic.objects.create(
            doctor=self.doctor_a,
            clinic=self.clinic_approved_2,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("1000.00"),
            follow_up_fee=Decimal("600.00"),
            appointment_duration_minutes=20,
        )

        # Doctor B: Verified, Active, associated with clinic 2 (Mumbai, Dermatology)
        self.user_doc_b = User.objects.create_user(
            email="dr.patel@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor_b = Doctor.objects.create(
            user=self.user_doc_b,
            full_name="Dr. Vikram Patel",
            registration_number="MMC-998877",
            registration_council="Maharashtra Medical Council",
            specialization="Dermatology",
            qualifications="MBBS, DVD",
            years_of_experience=6,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )
        self.assoc_b = DoctorClinic.objects.create(
            doctor=self.doctor_b,
            clinic=self.clinic_approved_2,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("600.00"),
            appointment_duration_minutes=15,
        )

        # Doctor C: Pending verification (must NOT appear)
        self.user_doc_c = User.objects.create_user(
            email="dr.unverified@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=False,
        )
        self.doctor_c = Doctor.objects.create(
            user=self.user_doc_c,
            full_name="Dr. Unverified Doe",
            registration_number="KMC-001122",
            registration_council="Karnataka Medical Council",
            specialization="General Medicine",
            verification_status=DoctorVerificationStatus.PENDING,
            is_verified=False,
        )
        DoctorClinic.objects.create(
            doctor=self.doctor_c,
            clinic=self.clinic_approved_1,
            status=DoctorClinicStatus.ACTIVE,
        )

        # Doctor D: Suspended doctor (must NOT appear)
        self.user_doc_d = User.objects.create_user(
            email="dr.suspended@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor_d = Doctor.objects.create(
            user=self.user_doc_d,
            full_name="Dr. Suspended Practitioner",
            registration_number="KMC-990011",
            registration_council="Karnataka Medical Council",
            specialization="Pediatrics",
            verification_status=DoctorVerificationStatus.SUSPENDED,
            is_verified=False,
        )
        DoctorClinic.objects.create(
            doctor=self.doctor_d,
            clinic=self.clinic_approved_1,
            status=DoctorClinicStatus.ACTIVE,
        )

        # Doctor E: Verified, but has NO active clinic association (must NOT appear)
        self.user_doc_e = User.objects.create_user(
            email="dr.noassoc@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor_e = Doctor.objects.create(
            user=self.user_doc_e,
            full_name="Dr. Solo NoClinic",
            registration_number="KMC-778899",
            registration_council="Karnataka Medical Council",
            specialization="Cardiology",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

        # Doctor F: Verified, but association with clinic 1 is REMOVED/SUSPENDED
        self.user_doc_f = User.objects.create_user(
            email="dr.suspendedassoc@eazydoc.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.doctor_f = Doctor.objects.create(
            user=self.user_doc_f,
            full_name="Dr. Inactive Assoc",
            registration_number="KMC-665544",
            registration_council="Karnataka Medical Council",
            specialization="Pediatrics",
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )
        DoctorClinic.objects.create(
            doctor=self.doctor_f,
            clinic=self.clinic_approved_1,
            status=DoctorClinicStatus.SUSPENDED,
        )

        # URLs
        self.doctor_search_url = reverse("api-v1:public:doctor-search")
        self.clinic_search_url = reverse("api-v1:public:clinic-search")
        self.specializations_url = reverse("api-v1:public:specialization-list")
        self.cities_url = reverse("api-v1:public:city-list")

    # =========================================================================
    # Doctor Search Tests
    # =========================================================================

    def test_verified_doctors_with_active_clinics_appear_in_search(self):
        """Rule 1: Verified doctors with active clinic associations appear in public search."""
        response = self.client.get(self.doctor_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        doctor_ids = [d["id"] for d in results]

        self.assertIn(str(self.doctor_a.id), doctor_ids)
        self.assertIn(str(self.doctor_b.id), doctor_ids)

    def test_unverified_doctors_do_not_appear(self):
        """Rule 2: Unverified doctors do not appear in public search."""
        response = self.client.get(self.doctor_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor_ids = [d["id"] for d in response.data["results"]]
        self.assertNotIn(str(self.doctor_c.id), doctor_ids)

    def test_suspended_doctors_do_not_appear(self):
        """Rule 3: Suspended doctors do not appear in public search."""
        response = self.client.get(self.doctor_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor_ids = [d["id"] for d in response.data["results"]]
        self.assertNotIn(str(self.doctor_d.id), doctor_ids)

    def test_doctors_without_active_clinic_associations_do_not_appear(self):
        """Rule 4: Doctors without active clinic associations do not appear in public search."""
        response = self.client.get(self.doctor_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor_ids = [d["id"] for d in response.data["results"]]
        self.assertNotIn(str(self.doctor_e.id), doctor_ids)
        self.assertNotIn(str(self.doctor_f.id), doctor_ids)

    def test_doctor_search_by_name(self):
        """Rule 9: Search by name works case-insensitively."""
        response = self.client.get(self.doctor_search_url, {"search": "priya"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["full_name"], "Dr. Priya Sharma")

    def test_doctor_filter_by_specialization(self):
        """Rule 10: Specialization filtering works."""
        response = self.client.get(self.doctor_search_url, {"specialization": "Cardiology"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.doctor_a.id))

    def test_doctor_filter_by_city(self):
        """Rule 11: City filtering works and scopes practice locations to matching city."""
        response = self.client.get(self.doctor_search_url, {"city": "Bengaluru"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        doc = results[0]
        self.assertEqual(doc["id"], str(self.doctor_a.id))
        # Locations returned should only be Bengaluru clinic
        self.assertEqual(len(doc["practice_locations"]), 1)
        self.assertEqual(doc["practice_locations"][0]["city"], "Bengaluru")
        self.assertEqual(doc["practice_locations"][0]["consultation_fee"], "700.00")

    def test_doctor_associated_with_multiple_clinics_is_not_duplicated(self):
        """Rule 13: A doctor associated with multiple clinics is returned exactly once in general search."""
        response = self.client.get(self.doctor_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        # Find Dr. Priya Sharma
        priya_matches = [d for d in results if d["id"] == str(self.doctor_a.id)]
        self.assertEqual(len(priya_matches), 1)
        # Should contain both practice locations
        locations = priya_matches[0]["practice_locations"]
        self.assertEqual(len(locations), 2)
        fees = {loc["clinic_name"]: loc["consultation_fee"] for loc in locations}
        self.assertEqual(fees["Apex Heart Institute"], "700.00")
        self.assertEqual(fees["Metro Skin & Child Clinic"], "1000.00")

    def test_doctor_clinic_filtering_returns_correct_practice_location_and_fee(self):
        """Rule 12: Filtering by clinic returns only matching clinic and correct fee."""
        response = self.client.get(self.doctor_search_url, {"clinic": "Apex Heart Institute"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        doc = results[0]
        self.assertEqual(doc["id"], str(self.doctor_a.id))
        self.assertEqual(len(doc["practice_locations"]), 1)
        self.assertEqual(doc["practice_locations"][0]["clinic_name"], "Apex Heart Institute")
        self.assertEqual(doc["practice_locations"][0]["consultation_fee"], "700.00")

    def test_pagination_and_max_page_size(self):
        """Rule 14: Pagination and maximum page size work correctly."""
        response = self.client.get(self.doctor_search_url, {"page": 1, "page_size": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(response.data["total_pages"], 2)

    def test_invalid_query_parameters_handled_safely(self):
        """Rule 15: Invalid query parameters (e.g. malformed date, invalid page) handled safely."""
        response = self.client.get(self.doctor_search_url, {"date": "not-a-real-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.data.get("errors", response.data)
        self.assertIn("date", errors)

        response = self.client.get(self.doctor_search_url, {"page": 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # =========================================================================
    # Doctor Detail Tests
    # =========================================================================

    def test_doctor_detail_exposes_only_permitted_public_fields(self):
        """Rule 7 & 17: Doctor detail exposes permitted public fields and NEVER leaks private data."""
        detail_url = reverse("api-v1:public:doctor-detail", kwargs={"doctor_id": self.doctor_a.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Permitted fields
        self.assertEqual(data["full_name"], "Dr. Priya Sharma")
        self.assertEqual(data["specialization"], "Cardiology")
        self.assertEqual(data["years_of_experience"], 12)
        self.assertTrue(data["is_verified"])
        self.assertEqual(len(data["practice_locations"]), 2)

        # CRITICAL PRIVACY CHECKS: Prohibited fields
        self.assertNotIn("verification_notes", data)
        self.assertNotIn("documents", data)
        self.assertNotIn("user", data)
        self.assertNotIn("email", data)
        self.assertNotIn("password", data)
        self.assertNotIn("registration_number", data)

    def test_ineligible_doctor_detail_returns_404(self):
        """Unverified, suspended, or unassociated doctor detail returns 404."""
        # Unverified
        url_c = reverse("api-v1:public:doctor-detail", kwargs={"doctor_id": self.doctor_c.id})
        res_c = self.client.get(url_c)
        self.assertEqual(res_c.status_code, status.HTTP_404_NOT_FOUND)

        # Suspended
        url_d = reverse("api-v1:public:doctor-detail", kwargs={"doctor_id": self.doctor_d.id})
        res_d = self.client.get(url_d)
        self.assertEqual(res_d.status_code, status.HTTP_404_NOT_FOUND)

        # No clinic association
        url_e = reverse("api-v1:public:doctor-detail", kwargs={"doctor_id": self.doctor_e.id})
        res_e = self.client.get(url_e)
        self.assertEqual(res_e.status_code, status.HTTP_404_NOT_FOUND)

    # =========================================================================
    # Clinic Search & Detail Tests
    # =========================================================================

    def test_unapproved_and_suspended_clinics_do_not_appear(self):
        """Rule 5: Unapproved and suspended clinics do not appear in public search."""
        response = self.client.get(self.clinic_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        clinic_names = [c["name"] for c in response.data["results"]]

        self.assertIn("Apex Heart Institute", clinic_names)
        self.assertIn("Metro Skin & Child Clinic", clinic_names)
        self.assertNotIn("Pending Review Clinic", clinic_names)
        self.assertNotIn("Suspended Clinic Facility", clinic_names)

    def test_clinic_search_by_name_and_city(self):
        """Rule 9 & 11: Clinic search by name and city filter."""
        res_name = self.client.get(self.clinic_search_url, {"search": "Heart"})
        self.assertEqual(res_name.status_code, status.HTTP_200_OK)
        self.assertEqual(res_name.data["count"], 1)
        self.assertEqual(res_name.data["results"][0]["name"], "Apex Heart Institute")

        res_city = self.client.get(self.clinic_search_url, {"city": "Mumbai"})
        self.assertEqual(res_city.status_code, status.HTTP_200_OK)
        self.assertEqual(res_city.data["count"], 1)
        self.assertEqual(res_city.data["results"][0]["city"], "Mumbai")

    def test_clinic_detail_exposes_only_permitted_public_fields(self):
        """Rule 8 & 17: Clinic detail exposes permitted public fields and verified doctors without leaking credentials."""
        detail_url = reverse("api-v1:public:clinic-detail", kwargs={"clinic_id": self.clinic_approved_1.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data["name"], "Apex Heart Institute")
        self.assertEqual(data["city"], "Bengaluru")
        self.assertEqual(data["phone"], "9876543201")
        self.assertEqual(data["timezone"], "Asia/Kolkata")

        # Prohibited fields
        self.assertNotIn("owner", data)
        self.assertNotIn("approved_by", data)
        self.assertNotIn("verification_notes", data)

        # Doctors practicing at this clinic
        doctors = data["doctors"]
        self.assertEqual(len(doctors), 1)
        self.assertEqual(doctors[0]["full_name"], "Dr. Priya Sharma")
        self.assertEqual(doctors[0]["consultation_fee"], "700.00")
        self.assertEqual(doctors[0]["appointment_duration_minutes"], 15)

    def test_clinic_detail_by_slug(self):
        """Clinic detail can be queried by slug as well as UUID."""
        detail_url = reverse("api-v1:public:clinic-detail", kwargs={"clinic_id": "apex-heart-institute"})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Apex Heart Institute")

    # =========================================================================
    # Public Availability Slots Tests
    # =========================================================================

    def test_public_availability_uses_clinic_timezone_and_schedule(self):
        """Rule 16: Public availability returns generated candidate slots for a valid schedule and date."""
        # Create a schedule shift for Doctor A at Clinic 1 on Mondays (Weekday.MONDAY = 0)
        # Shift: 09:00 - 10:00 (15 min slots = 4 slots: 09:00, 09:15, 09:30, 09:45)
        DoctorSchedule.objects.create(
            doctor_clinic=self.assoc_a1,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            slot_duration_minutes=15,
            is_active=True,
        )

        # Choose a target Monday, e.g. 2026-10-19
        target_date = "2026-10-19"
        avail_url = reverse(
            "api-v1:public:doctor-availability",
            kwargs={"clinic_id": self.clinic_approved_1.id, "doctor_id": self.doctor_a.id},
        )
        response = self.client.get(avail_url, {"date": target_date})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertTrue(data["is_eligible"])
        self.assertEqual(data["clinic"]["timezone"], "Asia/Kolkata")
        self.assertEqual(data["total_slots"], 4)
        self.assertEqual(data["available_slots_count"], 4)

        slot_times = [s["start_time"] for s in data["slots"]]
        self.assertEqual(slot_times, ["09:00", "09:15", "09:30", "09:45"])

        # Pricing metadata
        self.assertEqual(data["pricing"]["consultation_fee"], "700.00")
        self.assertEqual(data["pricing"]["follow_up_fee"], "400.00")

    def test_public_availability_for_inactive_association_returns_404(self):
        """Rule 6 & 16: No bookable availability for inactive or non-existent association."""
        avail_url = reverse(
            "api-v1:public:doctor-availability",
            kwargs={"clinic_id": self.clinic_approved_1.id, "doctor_id": self.doctor_f.id},
        )
        response = self.client.get(avail_url, {"date": "2026-10-19"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # =========================================================================
    # Query Performance & N+1 Tests
    # =========================================================================

    def test_doctor_search_does_not_exhibit_n_plus_one_queries(self):
        """Rule 18: Query count does not scale linearly with number of returned doctors."""
        # Warmup and initial count
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(self.doctor_search_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should be a small, bounded number of queries (pagination count + doctors + prefetched clinic associations)
        # Typically <= 6 queries regardless of number of doctors
        self.assertLessEqual(len(ctx.captured_queries), 7)
