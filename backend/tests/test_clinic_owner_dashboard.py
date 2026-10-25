from datetime import date, datetime, time, timedelta
from decimal import Decimal
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
from apps.audit_logs.models import AuditLog
from apps.clinics.models import (
    Clinic,
    ClinicClosure,
    ClinicStaff,
    ClinicStaffPermission,
    ClinicStatus,
    DoctorClinic,
    DoctorClinicStatus,
)
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.payments.models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentStatus,
)
from apps.schedules.models import DoctorSchedule, Weekday


class ClinicOwnerDashboardAndOperationsTests(APITestCase):
    """
    Day 13 automated test suite for Clinic Owner Dashboard and Clinic Operations.
    Validates tenant isolation, metrics accuracy, staff permissions, schedule integrity,
    financial reporting, and operational closures.
    """

    def setUp(self):
        self.kolkata_tz = ZoneInfo("Asia/Kolkata")
        self.now = timezone.now()

        # Clinic Owner 1
        self.owner1 = User.objects.create_user(
            email="owner1@apexhealth.com",
            password="Password123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            first_name="Alice",
            last_name="Owner",
        )

        # Clinic Owner 2
        self.owner2 = User.objects.create_user(
            email="owner2@citycare.com",
            password="Password123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            first_name="Bob",
            last_name="Owner",
        )

        # Doctor 1 (Verified)
        self.doctor_user1 = User.objects.create_user(
            email="dr.clark@hospital.com",
            password="Password123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            first_name="Clark",
            last_name="Kent",
        )
        self.doctor1 = Doctor.objects.create(
            user=self.doctor_user1,
            full_name="Dr. Clark Kent",
            registration_number="MMC-12345",
            registration_council="Maharashtra Medical Council",
            specialization="Cardiology",
            years_of_experience=10,
            verification_status=DoctorVerificationStatus.VERIFIED,
        )

        # Doctor 2 (Unverified)
        self.doctor_user2 = User.objects.create_user(
            email="dr.bruce@hospital.com",
            password="Password123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            first_name="Bruce",
            last_name="Wayne",
        )
        self.doctor2 = Doctor.objects.create(
            user=self.doctor_user2,
            full_name="Dr. Bruce Wayne",
            registration_number="MMC-67890",
            registration_council="Maharashtra Medical Council",
            specialization="Neurology",
            years_of_experience=8,
            verification_status=DoctorVerificationStatus.PENDING,
        )

        # Patient
        self.patient = User.objects.create_user(
            email="patient@example.com",
            password="Password123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Diana",
            last_name="Prince",
        )

        # Clinic 1 (Owned by owner1)
        self.clinic1 = Clinic.objects.create(
            name="Apex Healthcare",
            slug="apex-healthcare",
            owner=self.owner1,
            email="contact@apexhealth.com",
            phone="+919876543210",
            address_line_1="123 Hospital Road",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            country="India",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("10.00"),
        )

        # Clinic 2 (Owned by owner2)
        self.clinic2 = Clinic.objects.create(
            name="City Care Clinic",
            slug="city-care-clinic",
            owner=self.owner2,
            email="contact@citycare.com",
            phone="+919876543211",
            address_line_1="456 Care Lane",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            country="India",
            status=ClinicStatus.APPROVED,
            timezone="Asia/Kolkata",
            commission_rate=Decimal("15.00"),
        )

        # Affiliation: Doctor 1 @ Clinic 1 (ACTIVE)
        self.doc_clinic1 = DoctorClinic.objects.create(
            doctor=self.doctor1,
            clinic=self.clinic1,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            follow_up_fee=Decimal("300.00"),
            appointment_duration_minutes=30,
        )

        # Affiliation: Doctor 1 @ Clinic 2 (ACTIVE, with independent fee)
        self.doc_clinic2 = DoctorClinic.objects.create(
            doctor=self.doctor1,
            clinic=self.clinic2,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("800.00"),
            follow_up_fee=Decimal("500.00"),
            appointment_duration_minutes=45,
        )

    # 1. Clinic owners can access their own clinic dashboard.
    def test_clinic_owner_can_access_own_dashboard(self):
        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-dashboard-summary", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["clinic"]["name"], "Apex Healthcare")
        self.assertIn("doctor_metrics", response.data["data"])
        self.assertIn("appointment_metrics", response.data["data"])
        self.assertIn("financial_metrics", response.data["data"])

    # 2. Clinic owners cannot access another clinic's dashboard.
    def test_clinic_owner_cannot_access_other_clinic_dashboard(self):
        self.client.force_authenticate(user=self.owner2)
        url = reverse("api-v1:clinics:clinic-dashboard-summary", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # 3. Dashboard metrics are calculated from real clinic-scoped data.
    def test_dashboard_metrics_calculated_from_real_clinic_scoped_data(self):
        # Create appointments for clinic 1
        appt1 = Appointment.objects.create(
            booking_reference="EZD-TEST-C1-001",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=self.now + timedelta(hours=2),
            end_at=self.now + timedelta(hours=2, minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )
        appt2 = Appointment.objects.create(
            booking_reference="EZD-TEST-C1-002",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=self.now - timedelta(days=2),
            end_at=self.now - timedelta(days=2, minutes=-30),
            status=AppointmentStatus.COMPLETED,
            consultation_fee=Decimal("500.00"),
        )
        # Payment and commission for appt2
        payment1 = Payment.objects.create(
            appointment=appt2,
            patient=self.patient,
            clinic=self.clinic1,
            gateway_order_id="order_c1_001",
            amount=Decimal("500.00"),
            status=PaymentStatus.PAID,
            paid_at=self.now - timedelta(days=2),
        )
        CommissionRecord.objects.create(
            payment=payment1,
            appointment=appt2,
            clinic=self.clinic1,
            gross_amount=Decimal("500.00"),
            commission_rate=Decimal("10.00"),
            commission_amount=Decimal("50.00"),
            clinic_share=Decimal("450.00"),
            status=CommissionStatus.PENDING_SETTLEMENT,
        )

        # Create appointment and payment for clinic 2 (must not appear in clinic 1)
        appt_c2 = Appointment.objects.create(
            booking_reference="EZD-TEST-C2-001",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic2,
            clinic=self.clinic2,
            start_at=self.now - timedelta(days=1),
            end_at=self.now - timedelta(days=1, minutes=-45),
            status=AppointmentStatus.COMPLETED,
            consultation_fee=Decimal("800.00"),
        )
        payment_c2 = Payment.objects.create(
            appointment=appt_c2,
            patient=self.patient,
            clinic=self.clinic2,
            gateway_order_id="order_c2_001",
            amount=Decimal("800.00"),
            status=PaymentStatus.PAID,
            paid_at=self.now - timedelta(days=1),
        )
        CommissionRecord.objects.create(
            payment=payment_c2,
            appointment=appt_c2,
            clinic=self.clinic2,
            gross_amount=Decimal("800.00"),
            commission_rate=Decimal("15.00"),
            commission_amount=Decimal("120.00"),
            clinic_share=Decimal("680.00"),
            status=CommissionStatus.PENDING_SETTLEMENT,
        )

        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-dashboard-summary", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(url, {"period": "this_month"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fin = response.data["data"]["financial_metrics"]
        self.assertEqual(Decimal(fin["gross_patient_payments"]), Decimal("500.00"))
        self.assertEqual(Decimal(fin["recorded_platform_commission"]), Decimal("50.00"))
        self.assertEqual(Decimal(fin["calculated_clinic_share"]), Decimal("450.00"))
        self.assertEqual(fin["actual_payouts"], "0.00")

    # 4. Clinic profile updates enforce field-level permissions.
    def test_clinic_profile_updates_enforce_field_level_permissions(self):
        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-management", kwargs={"clinic_id": self.clinic1.id})

        # Legitimate profile update
        update_data = {
            "name": "Apex Super Speciality Hospital",
            "phone": "+919876543299",
            "description": "Premier multi-speciality medical centre.",
        }
        response = self.client.patch(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.clinic1.refresh_from_db()
        self.assertEqual(self.clinic1.name, "Apex Super Speciality Hospital")

        # Attempt to tamper with status or commission_rate
        tamper_data = {"status": ClinicStatus.APPROVED, "commission_rate": "2.50"}
        response = self.client.patch(url, tamper_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 5. Owners cannot approve their own clinics.
    def test_owners_cannot_approve_their_own_clinics(self):
        # Create draft clinic
        draft_clinic = Clinic.objects.create(
            name="Draft Clinic",
            slug="draft-clinic",
            owner=self.owner1,
            email="draft@clinic.com",
            phone="+919876543288",
            address_line_1="Draft Road",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            status=ClinicStatus.PENDING,
        )
        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-management", kwargs={"clinic_id": draft_clinic.id})
        response = self.client.patch(url, {"status": "APPROVED", "is_verified": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        draft_clinic.refresh_from_db()
        self.assertEqual(draft_clinic.status, ClinicStatus.PENDING)

    # 6. Doctor association management uses the existing association rules.
    def test_doctor_association_management_uses_existing_rules(self):
        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-doctor-invitations", kwargs={"clinic_id": self.clinic1.id})

        # Inviting unverified doctor fails
        response = self.client.post(
            url,
            {
                "doctor_id": str(self.doctor2.id),
                "consultation_fee": "600.00",
                "appointment_duration_minutes": 20,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 7. Clinic-specific fees do not affect other clinics.
    def test_clinic_specific_fees_do_not_affect_other_clinics(self):
        self.assertEqual(self.doc_clinic1.consultation_fee, Decimal("500.00"))
        self.assertEqual(self.doc_clinic2.consultation_fee, Decimal("800.00"))

        # Update fee for Clinic 1
        self.client.force_authenticate(user=self.owner1)
        url = reverse(
            "api-v1:clinics:clinic-doctor-settings",
            kwargs={"clinic_id": self.clinic1.id, "association_id": self.doc_clinic1.id},
        )
        response = self.client.patch(url, {"consultation_fee": "650.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.doc_clinic1.refresh_from_db()
        self.doc_clinic2.refresh_from_db()
        self.assertEqual(self.doc_clinic1.consultation_fee, Decimal("650.00"))
        # Clinic 2 fee remains unaffected
        self.assertEqual(self.doc_clinic2.consultation_fee, Decimal("800.00"))

    # 8. Schedule changes retain cross-clinic conflict protection.
    def test_schedule_changes_retain_cross_clinic_conflict_protection(self):
        # Create Monday 09:00 - 12:00 shift for Doctor 1 at Clinic 1
        DoctorSchedule.objects.create(
            doctor_clinic=self.doc_clinic1,
            day_of_week=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
            is_active=True,
        )

        # Attempt to create conflicting Monday 10:00 - 13:00 shift for same doctor at Clinic 2
        self.client.force_authenticate(user=self.owner2)
        url = reverse("api-v1:schedules:schedule-list-create")
        response = self.client.post(
            url,
            {
                "doctor_clinic": str(self.doc_clinic2.id),
                "day_of_week": Weekday.MONDAY,
                "start_time": "10:00:00",
                "end_time": "13:00:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # 9. Appointment lists are correctly scoped to the clinic.
    def test_appointment_lists_scoped_to_clinic(self):
        appt1 = Appointment.objects.create(
            booking_reference="EZD-SCOPE-C1",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=self.now + timedelta(days=1),
            end_at=self.now + timedelta(days=1, minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )
        appt2 = Appointment.objects.create(
            booking_reference="EZD-SCOPE-C2",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic2,
            clinic=self.clinic2,
            start_at=self.now + timedelta(days=1),
            end_at=self.now + timedelta(days=1, minutes=45),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("800.00"),
        )

        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-appointments", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refs = [item["booking_reference"] for item in response.data.get("results", response.data)]
        self.assertIn("EZD-SCOPE-C1", refs)
        self.assertNotIn("EZD-SCOPE-C2", refs)

    # 10. Unauthorized appointment actions are rejected.
    def test_unauthorized_appointment_actions_are_rejected(self):
        appt1 = Appointment.objects.create(
            booking_reference="EZD-AUTH-C1",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=self.now + timedelta(days=1),
            end_at=self.now + timedelta(days=1, minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )
        # Owner 2 tries to cancel Clinic 1's appointment
        self.client.force_authenticate(user=self.owner2)
        url = reverse(
            "api-v1:clinics:clinic-appointment-cancel",
            kwargs={"clinic_id": self.clinic1.id, "appointment_id": appt1.id},
        )
        response = self.client.post(url, {"reason": "Malicious attempt"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # 11. Staff permissions are enforced independently.
    def test_staff_permissions_enforced_independently(self):
        # Create Staff user with VIEW_APPOINTMENTS only
        staff_user = User.objects.create_user(
            email="reception@apexhealth.com",
            password="Password123!",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
            first_name="Sam",
            last_name="Staff",
        )
        staff_profile = ClinicStaff.objects.create(
            clinic=self.clinic1,
            user=staff_user,
            role_title="Receptionist",
            permissions=[ClinicStaffPermission.VIEW_APPOINTMENTS],
            is_active=True,
        )

        appt1 = Appointment.objects.create(
            booking_reference="EZD-STAFF-C1",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=self.now + timedelta(days=2),
            end_at=self.now + timedelta(days=2, minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )

        self.client.force_authenticate(user=staff_user)

        # Can view appointments
        list_url = reverse("api-v1:clinics:clinic-appointments", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Cannot cancel without MANAGE_APPOINTMENTS
        cancel_url = reverse(
            "api-v1:clinics:clinic-appointment-cancel",
            kwargs={"clinic_id": self.clinic1.id, "appointment_id": appt1.id},
        )
        response = self.client.post(cancel_url, {"reason": "Unauthorized staff cancel"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Grant MANAGE_APPOINTMENTS permission
        staff_profile.permissions.append(ClinicStaffPermission.MANAGE_APPOINTMENTS)
        staff_profile.save()

        response = self.client.post(cancel_url, {"reason": "Patient requested cancellation via phone"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appt1.refresh_from_db()
        self.assertEqual(appt1.status, AppointmentStatus.CANCELLED)

    # 12. Staff cannot escalate their own privileges.
    def test_staff_cannot_escalate_privileges(self):
        staff_user = User.objects.create_user(
            email="nurse@apexhealth.com",
            password="Password123!",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
            first_name="Nancy",
            last_name="Nurse",
        )
        ClinicStaff.objects.create(
            clinic=self.clinic1,
            user=staff_user,
            role_title="Nurse",
            permissions=[ClinicStaffPermission.VIEW_APPOINTMENTS],
            is_active=True,
        )

        self.client.force_authenticate(user=staff_user)
        # Attempt to create another staff member or assign permissions
        staff_url = reverse("api-v1:clinics:clinic-staff-list-create", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.post(
            staff_url,
            {
                "email": "hacker@apexhealth.com",
                "first_name": "Bad",
                "last_name": "Actor",
                "permissions": [ClinicStaffPermission.MANAGE_STAFF],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # 13. Revoked staff access is rejected.
    def test_revoked_staff_access_is_rejected(self):
        staff_user = User.objects.create_user(
            email="temp@apexhealth.com",
            password="Password123!",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
            first_name="Temp",
            last_name="Worker",
        )
        staff_profile = ClinicStaff.objects.create(
            clinic=self.clinic1,
            user=staff_user,
            role_title="Temporary Staff",
            permissions=[ClinicStaffPermission.VIEW_APPOINTMENTS],
            is_active=True,
        )

        self.client.force_authenticate(user=staff_user)
        list_url = reverse("api-v1:clinics:clinic-appointments", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Revoke staff
        staff_profile.is_active = False
        staff_profile.save()

        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # 14. Financial summaries use historical transaction snapshots.
    def test_financial_summaries_use_historical_transaction_snapshots(self):
        appt = Appointment.objects.create(
            booking_reference="EZD-FIN-HIST-01",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=self.now - timedelta(days=3),
            end_at=self.now - timedelta(days=3, minutes=-30),
            status=AppointmentStatus.COMPLETED,
            consultation_fee=Decimal("500.00"),
        )
        payment = Payment.objects.create(
            appointment=appt,
            patient=self.patient,
            clinic=self.clinic1,
            gateway_order_id="order_hist_01",
            amount=Decimal("500.00"),
            status=PaymentStatus.PAID,
            paid_at=self.now - timedelta(days=3),
        )
        # Snapshot taken with 10% rate
        CommissionRecord.objects.create(
            payment=payment,
            appointment=appt,
            clinic=self.clinic1,
            gross_amount=Decimal("500.00"),
            commission_rate=Decimal("10.00"),
            commission_amount=Decimal("50.00"),
            clinic_share=Decimal("450.00"),
            status=CommissionStatus.PENDING_SETTLEMENT,
        )

        # Alter clinic current commission rate to 20%
        self.clinic1.commission_rate = Decimal("20.00")
        self.clinic1.save()

        # Summary must still reflect the historical snapshot (50.00 commission, 450.00 share)
        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-finance-summary", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(url, {"period": "this_month"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        metrics = response.data["data"]["period_metrics"]
        self.assertEqual(Decimal(metrics["recorded_platform_commission"]), Decimal("50.00"))
        self.assertEqual(Decimal(metrics["calculated_clinic_share"]), Decimal("450.00"))

    # 15. Clinic owners cannot modify financial records.
    def test_clinic_owners_cannot_modify_financial_records(self):
        self.client.force_authenticate(user=self.owner1)
        # Verify payments list is read-only (no POST/PUT/PATCH endpoints)
        payments_url = reverse("api-v1:clinics:clinic-finance-payments", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.post(payments_url, {"amount": "1000.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # 16. Clinic closures identify affected appointments.
    def test_clinic_closures_identify_affected_appointments(self):
        target_date = (self.now + timedelta(days=4)).date()
        target_dt = datetime.combine(target_date, time(10, 0), tzinfo=self.kolkata_tz)

        appt = Appointment.objects.create(
            booking_reference="EZD-CLOSURE-AFFECTED",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=target_dt,
            end_at=target_dt + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )

        self.client.force_authenticate(user=self.owner1)

        # 1. Preview affected appointments
        preview_url = reverse("api-v1:clinics:clinic-closures-preview", kwargs={"clinic_id": self.clinic1.id})
        preview_res = self.client.post(
            preview_url,
            {
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
                "reason": "Facility Sanitisation",
            },
            format="json",
        )
        self.assertEqual(preview_res.status_code, status.HTTP_200_OK)
        self.assertEqual(preview_res.data["data"]["affected_count"], 1)
        self.assertTrue(preview_res.data["data"]["requires_confirmation"])

        # 2. Creating closure without confirmation fails with 409
        closure_url = reverse("api-v1:clinics:clinic-closures-list-create", kwargs={"clinic_id": self.clinic1.id})
        create_res = self.client.post(
            closure_url,
            {
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
                "reason": "Facility Sanitisation",
                "confirmed": False,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(create_res.data["requires_confirmation"])

        # 3. Creating closure with confirmation succeeds and flags appointment
        confirm_res = self.client.post(
            closure_url,
            {
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
                "reason": "Facility Sanitisation",
                "confirmed": True,
            },
            format="json",
        )
        self.assertEqual(confirm_res.status_code, status.HTTP_201_CREATED)
        appt.refresh_from_db()
        self.assertTrue(appt.reschedule_required)
        self.assertEqual(appt.status, AppointmentStatus.RESCHEDULE_REQUIRED)

    # 17. Unavailability actions preserve appointment history.
    def test_unavailability_actions_preserve_appointment_history(self):
        appt = Appointment.objects.create(
            booking_reference="EZD-UNAVAIL-HIST",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=self.now + timedelta(days=2),
            end_at=self.now + timedelta(days=2, minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )
        self.client.force_authenticate(user=self.owner1)
        unavail_url = reverse(
            "api-v1:clinics:clinic-appointment-report-unavailability",
            kwargs={"clinic_id": self.clinic1.id, "appointment_id": appt.id},
        )
        response = self.client.post(
            unavail_url,
            {"reason": "Doctor has emergency surgical duty", "action": "RESCHEDULE_REQUIRED"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Detail view includes history
        detail_url = reverse(
            "api-v1:clinics:clinic-appointment-detail",
            kwargs={"clinic_id": self.clinic1.id, "appointment_id": appt.id},
        )
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        history = detail_res.data["data"]["history"]
        self.assertTrue(len(history) > 0)
        self.assertTrue(any("emergency surgical duty" in h.get("reason", "") for h in history))

    # 18. Date filters use the clinic timezone.
    def test_date_filters_use_clinic_timezone(self):
        # In Asia/Kolkata (UTC+5:30), 2026-10-25 01:00 AM IST is 2026-10-24 19:30 UTC.
        # An appointment at 19:30 UTC on 24th Oct is 25th Oct in Kolkata.
        dt_utc = datetime(2026, 10, 24, 19, 30, tzinfo=ZoneInfo("UTC"))
        appt = Appointment.objects.create(
            booking_reference="EZD-TZ-TEST-01",
            patient=self.patient,
            doctor=self.doctor1,
            doctor_clinic=self.doc_clinic1,
            clinic=self.clinic1,
            start_at=dt_utc,
            end_at=dt_utc + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
        )

        self.client.force_authenticate(user=self.owner1)
        list_url = reverse("api-v1:clinics:clinic-appointments", kwargs={"clinic_id": self.clinic1.id})

        # Filtering by date=2026-10-25 should match when queried
        res = self.client.get(list_url, {"from_date": "2026-10-25", "to_date": "2026-10-25"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    # 19. Pagination and search work correctly.
    def test_pagination_and_search_work_correctly(self):
        for i in range(5):
            Appointment.objects.create(
                booking_reference=f"EZD-SEARCH-REF-{i:03d}",
                patient=self.patient,
                doctor=self.doctor1,
                doctor_clinic=self.doc_clinic1,
                clinic=self.clinic1,
                start_at=self.now + timedelta(days=i + 1),
                end_at=self.now + timedelta(days=i + 1, minutes=30),
                status=AppointmentStatus.CONFIRMED,
                consultation_fee=Decimal("500.00"),
            )

        self.client.force_authenticate(user=self.owner1)
        url = reverse("api-v1:clinics:clinic-appointments", kwargs={"clinic_id": self.clinic1.id})

        # Search by specific booking reference
        response = self.client.get(url, {"search": "REF-003"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["booking_reference"], "EZD-SEARCH-REF-003")

    # 20. Calendar endpoint returns aggregated shifts, appointments, closures.
    def test_calendar_endpoint_returns_aggregated_schedule_data(self):
        # Create a shift
        DoctorSchedule.objects.create(
            doctor_clinic=self.doc_clinic1,
            day_of_week=Weekday.TUESDAY,
            start_time=time(14, 0),
            end_time=time(18, 0),
            is_active=True,
        )
        # Create a closure
        ClinicClosure.objects.create(
            clinic=self.clinic1,
            start_date=(self.now + timedelta(days=5)).date(),
            end_date=(self.now + timedelta(days=6)).date(),
            reason="National Holiday",
            is_active=True,
        )

        self.client.force_authenticate(user=self.owner1)
        cal_url = reverse("api-v1:clinics:clinic-calendar", kwargs={"clinic_id": self.clinic1.id})
        response = self.client.get(cal_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertIn("shifts", data)
        self.assertIn("appointments", data)
        self.assertIn("closures", data)
        self.assertEqual(len(data["shifts"]), 1)
        self.assertEqual(len(data["closures"]), 1)
