from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole, UserStatus
from apps.audit_logs.services import log_audit_event
from apps.clinics.models import Clinic, ClinicStaff
from apps.clinics.permissions import check_clinic_access
from apps.clinics.management_serializers import (
    ClinicStaffCreateSerializer,
    ClinicStaffSerializer,
    ClinicStaffUpdateSerializer,
)


class ClinicStaffListCreateView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/staff/
    POST /api/v1/clinics/{clinic_id}/staff/
    Lists and invites/creates clinic staff members.
    Only the clinic owner (or Super Admin) can manage staff members and assign permissions.
    """

    @extend_schema(
        summary="List Clinic Staff Members",
        description="Returns all active and inactive staff members associated with the clinic.",
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic):
            raise PermissionDenied("You do not have permission to view staff for this clinic.")

        staff_qs = ClinicStaff.objects.filter(clinic_id=clinic.id).select_related("user").order_by("-created_at")
        serializer = ClinicStaffSerializer(staff_qs, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Invite / Create Clinic Staff Member",
        description="Creates or associates a STAFF user with explicit permissions. Restricted to clinic owner.",
        request=ClinicStaffCreateSerializer,
    )
    def post(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)

        # Strictly clinic owner or super admin can grant staff permissions (Rule 9)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            raise PermissionDenied("Only the clinic owner can invite or grant permissions to staff members.")

        serializer = ClinicStaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        first_name = serializer.validated_data["first_name"]
        last_name = serializer.validated_data["last_name"]
        role_title = serializer.validated_data.get("role_title", "Clinic Staff")
        permissions = serializer.validated_data.get("permissions", [])
        password = serializer.validated_data.get("password")

        with transaction.atomic():
            user = User.objects.filter(email=email).first()
            if user:
                if user.role != UserRole.STAFF:
                    raise ValidationError(
                        {"email": f"User already exists with role '{user.get_role_display()}'. Only accounts with role 'STAFF' can be associated."}
                    )
                if hasattr(user, "staff_profile"):
                    if user.staff_profile.clinic_id == clinic.id:
                        raise ValidationError({"email": "This user is already a registered staff member of this clinic."})
                    else:
                        raise ValidationError({"email": "This staff user is already affiliated with another clinic facility."})
            else:
                user = User.objects.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=UserRole.STAFF,
                    status=UserStatus.ACTIVE,
                    is_active=True,
                    is_verified=True,
                )
                if password:
                    user.set_password(password)
                else:
                    user.set_unusable_password()
                user.save()

            staff_member = ClinicStaff.objects.create(
                clinic=clinic,
                user=user,
                role_title=role_title,
                permissions=permissions,
                is_active=True,
            )

            log_audit_event(
                action="CLINIC_STAFF_CREATED",
                resource_type="ClinicStaff",
                resource_id=str(staff_member.id),
                clinic_id=str(clinic.id),
                actor=request.user,
                request=request,
                details={
                    "staff_user_id": str(user.id),
                    "staff_email": user.email,
                    "role_title": role_title,
                    "granted_permissions": permissions,
                },
            )

        return Response(
            {
                "success": True,
                "message": f"Staff member '{user.email}' added successfully.",
                "data": ClinicStaffSerializer(staff_member).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ClinicStaffDetailView(APIView):
    """
    PATCH /api/v1/clinics/{clinic_id}/staff/{staff_id}/
    DELETE /api/v1/clinics/{clinic_id}/staff/{staff_id}/
    Update staff permissions or revoke staff association.
    Strictly restricted to clinic owner or Super Admin.
    """

    @extend_schema(
        summary="Update Staff Permissions & Status",
        description="Updates role title, granular permissions, or active status. Restricted to clinic owner.",
        request=ClinicStaffUpdateSerializer,
    )
    def patch(self, request, clinic_id, staff_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            raise PermissionDenied("Only the clinic owner can modify staff permissions.")

        staff_member = get_object_or_404(ClinicStaff, id=staff_id, clinic_id=clinic.id)
        serializer = ClinicStaffUpdateSerializer(staff_member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_staff = serializer.save()

        log_audit_event(
            action="CLINIC_STAFF_UPDATED",
            resource_type="ClinicStaff",
            resource_id=str(updated_staff.id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={
                "staff_user_id": str(updated_staff.user_id),
                "role_title": updated_staff.role_title,
                "permissions": updated_staff.permissions,
                "is_active": updated_staff.is_active,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Staff member updated successfully.",
                "data": ClinicStaffSerializer(updated_staff).data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Revoke Staff Member",
        description="Permanently revokes staff affiliation from this clinic. Takes effect immediately.",
    )
    def delete(self, request, clinic_id, staff_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if request.user.role != UserRole.SUPER_ADMIN and clinic.owner_id != request.user.id:
            raise PermissionDenied("Only the clinic owner can revoke staff membership.")

        staff_member = get_object_or_404(ClinicStaff, id=staff_id, clinic_id=clinic.id)
        staff_user_id = str(staff_member.user_id)
        staff_email = staff_member.user.email

        staff_member.delete()

        log_audit_event(
            action="CLINIC_STAFF_REVOKED",
            resource_type="ClinicStaff",
            resource_id=str(staff_id),
            clinic_id=str(clinic.id),
            actor=request.user,
            request=request,
            details={
                "revoked_user_id": staff_user_id,
                "revoked_email": staff_email,
            },
        )

        return Response(
            {"success": True, "message": f"Staff access for '{staff_email}' revoked successfully."},
            status=status.HTTP_200_OK,
        )
