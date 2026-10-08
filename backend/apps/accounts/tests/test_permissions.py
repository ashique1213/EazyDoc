from django.test import RequestFactory, TestCase
from apps.accounts.models import User, UserRole, UserStatus
from apps.accounts.permissions import (
    IsClinicOwner,
    IsDoctor,
    IsPatient,
    IsStaff,
    IsSuperAdmin,
    IsObjectOwner,
    IsClinicTenantObject,
)


class DummyClinic:
    def __init__(self, owner_id):
        self.id = "clinic-123"
        self.owner_id = owner_id


class DummyRecord:
    def __init__(self, user, clinic=None):
        self.user = user
        self.clinic = clinic


class PermissionsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.super_admin = User.objects.create_user(
            email="admin@eazydoc.com",
            password="Password123!",
            role=UserRole.SUPER_ADMIN,
        )
        self.clinic_owner = User.objects.create_user(
            email="owner@eazydoc.com",
            password="Password123!",
            role=UserRole.CLINIC_OWNER,
        )
        self.doctor = User.objects.create_user(
            email="doctor@eazydoc.com",
            password="Password123!",
            role=UserRole.DOCTOR,
        )
        self.staff = User.objects.create_user(
            email="staff@eazydoc.com",
            password="Password123!",
            role=UserRole.STAFF,
        )
        self.patient = User.objects.create_user(
            email="patient@eazydoc.com",
            password="Password123!",
            role=UserRole.PATIENT,
        )

    def test_super_admin_permission(self):
        perm = IsSuperAdmin()
        request = self.factory.get("/")

        request.user = self.super_admin
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.clinic_owner
        self.assertFalse(perm.has_permission(request, None))

    def test_clinic_owner_permission(self):
        perm = IsClinicOwner()
        request = self.factory.get("/")

        request.user = self.clinic_owner
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.doctor
        self.assertFalse(perm.has_permission(request, None))

    def test_doctor_permission(self):
        perm = IsDoctor()
        request = self.factory.get("/")

        request.user = self.doctor
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.patient
        self.assertFalse(perm.has_permission(request, None))

    def test_staff_permission(self):
        perm = IsStaff()
        request = self.factory.get("/")

        request.user = self.staff
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.doctor
        self.assertFalse(perm.has_permission(request, None))

    def test_patient_permission(self):
        perm = IsPatient()
        request = self.factory.get("/")

        request.user = self.patient
        self.assertTrue(perm.has_permission(request, None))

        request.user = self.clinic_owner
        self.assertFalse(perm.has_permission(request, None))

    def test_unauthenticated_user_rejected_by_all_role_permissions(self):
        request = self.factory.get("/")
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()

        self.assertFalse(IsSuperAdmin().has_permission(request, None))
        self.assertFalse(IsClinicOwner().has_permission(request, None))
        self.assertFalse(IsDoctor().has_permission(request, None))
        self.assertFalse(IsStaff().has_permission(request, None))
        self.assertFalse(IsPatient().has_permission(request, None))

    def test_object_owner_permission(self):
        perm = IsObjectOwner()
        record_patient = DummyRecord(user=self.patient)
        request = self.factory.get("/")

        # Owner has permission
        request.user = self.patient
        self.assertTrue(perm.has_object_permission(request, None, record_patient))

        # Different user denied
        request.user = self.doctor
        self.assertFalse(perm.has_object_permission(request, None, record_patient))

        # Super admin allowed
        request.user = self.super_admin
        self.assertTrue(perm.has_object_permission(request, None, record_patient))

    def test_clinic_tenant_object_permission(self):
        perm = IsClinicTenantObject()
        clinic = DummyClinic(owner_id=self.clinic_owner.id)
        record = DummyRecord(user=self.patient, clinic=clinic)

        request = self.factory.get("/")

        # Clinic owner of this clinic allowed
        request.user = self.clinic_owner
        self.assertTrue(perm.has_object_permission(request, None, record))

        # Another clinic owner not allowed
        other_owner = User.objects.create_user(
            email="otherowner@eazydoc.com",
            password="Password123!",
            role=UserRole.CLINIC_OWNER,
        )
        request.user = other_owner
        self.assertFalse(perm.has_object_permission(request, None, record))
