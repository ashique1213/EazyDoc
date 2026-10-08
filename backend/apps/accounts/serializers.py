from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserRole, UserStatus
from .services import create_verification_token
from apps.audit_logs.services import log_audit_event


class UserSerializer(serializers.ModelSerializer):
    """Safe, read-only serializer for public user identity representation."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "status",
            "is_verified",
            "created_at",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public registration serializer.
    Strictly forbids self-registration as SUPER_ADMIN or STAFF.
    Enforces password strength and unique email/phone constraints.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    role = serializers.ChoiceField(
        choices=[
            (UserRole.PATIENT, "Patient"),
            (UserRole.CLINIC_OWNER, "Clinic Owner"),
            (UserRole.DOCTOR, "Doctor"),
        ],
        default=UserRole.PATIENT,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
        ]
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
        }

    def validate_email(self, value: str) -> str:
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return normalized_email

    def validate_phone(self, value: str) -> str:
        if value:
            cleaned_phone = value.strip()
            if User.objects.filter(phone=cleaned_phone).exists():
                raise serializers.ValidationError("An account with this phone number already exists.")
            return cleaned_phone
        return value

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate_role(self, value: str) -> str:
        if value in (UserRole.SUPER_ADMIN, UserRole.STAFF):
            raise serializers.ValidationError(
                f"Registration as '{value}' is restricted. Contact platform administrators."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.get("role", UserRole.PATIENT)

        user = User.objects.create_user(
            password=password,
            is_active=True,
            is_verified=False,
            status=UserStatus.ACTIVE,
            **validated_data,
        )

        # Trigger secure email verification token generation
        create_verification_token(user)

        request = self.context.get("request")
        log_audit_event(
            action="ACCOUNT_REGISTERED",
            resource_type="User",
            resource_id=str(user.id),
            actor=user,
            request=request,
            details={"email": user.email, "role": role},
        )

        return user


class LoginSerializer(serializers.Serializer):
    """Validates login credentials and returns authenticated user."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"non_field_errors": ["Invalid email or password."]})

        if not user.check_password(password):
            request = self.context.get("request")
            log_audit_event(
                action="LOGIN_FAILED",
                resource_type="User",
                resource_id=str(user.id),
                request=request,
                details={"reason": "incorrect_password", "email": email},
            )
            raise serializers.ValidationError({"non_field_errors": ["Invalid email or password."]})

        if not user.is_active:
            raise serializers.ValidationError({"non_field_errors": ["Your account is inactive."]})

        if user.status == UserStatus.SUSPENDED:
            raise serializers.ValidationError(
                {"non_field_errors": ["Your account has been suspended. Please contact support."]}
            )

        attrs["user"] = user
        return attrs


class TokenRefreshSerializer(serializers.Serializer):
    """Validates refresh token provided in cookie or payload."""

    refresh = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context.get("request")
        refresh_token = attrs.get("refresh")

        if not refresh_token and request:
            refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            raise serializers.ValidationError({"refresh": ["Refresh token is required."]})

        try:
            token = RefreshToken(refresh_token)
        except TokenError as e:
            raise serializers.ValidationError({"refresh": [f"Invalid or expired refresh token: {str(e)}"]})

        attrs["token_obj"] = token
        attrs["refresh_token_str"] = refresh_token
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    """Input serializer for email verification token."""

    token = serializers.CharField(required=True, min_length=10, max_length=128)


class ResendVerificationSerializer(serializers.Serializer):
    """Input serializer for requesting a new email verification token."""

    email = serializers.EmailField(required=True)


class ForgotPasswordSerializer(serializers.Serializer):
    """Input serializer for password recovery initiation."""

    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Input serializer for completing password reset."""

    token = serializers.CharField(required=True, min_length=10, max_length=128)
    password = serializers.CharField(required=True, write_only=True)

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value
