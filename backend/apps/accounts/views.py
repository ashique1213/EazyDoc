from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer as SimpleJWTTokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .authentication import clear_auth_cookies, set_auth_cookies
from .models import User, UserStatus
from .permissions import IsAuthenticatedUser
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from .services import (
    create_verification_token,
    request_password_reset,
    reset_password_with_token,
    verify_email_with_token,
)
from .throttling import (
    EmailVerificationRateThrottle,
    LoginRateThrottle,
    PasswordResetRateThrottle,
    RegisterRateThrottle,
)
from apps.audit_logs.services import log_audit_event


class RegisterView(APIView):
    """Public registration for patients, doctors, and clinic owners."""

    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    @extend_schema(
        summary="Register New User",
        description="Creates a new user account with role PATIENT, DOCTOR, or CLINIC_OWNER. Initiates email verification.",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description="User successfully registered."),
            400: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Account registered successfully. Please check your email to verify your account.",
                "data": {
                    "user": UserSerializer(user).data,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Authenticate user with email and password."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        summary="User Login",
        description="Authenticates credentials and establishes session via JWT tokens and secure HttpOnly cookies.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful."),
            400: OpenApiResponse(description="Validation failed."),
            401: OpenApiResponse(description="Invalid credentials."),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token_str = str(refresh.access_token)
        refresh_token_str = str(refresh)

        # Build response
        response = Response(
            {
                "success": True,
                "message": "Login successful.",
                "data": {
                    "user": UserSerializer(user).data,
                    "tokens": {
                        "access": access_token_str,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )

        # Set secure HttpOnly cookies
        set_auth_cookies(
            response=response,
            access_token=access_token_str,
            refresh_token=refresh_token_str,
        )

        # Audit log login event
        log_audit_event(
            action="LOGIN",
            resource_type="User",
            resource_id=str(user.id),
            actor=user,
            request=request,
            details={"email": user.email, "role": user.role},
        )

        return response


class LogoutView(APIView):
    """Revokes active refresh tokens and clears authentication cookies."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="User Logout",
        description="Blacklists the provided or cookie-stored refresh token and destroys auth cookies.",
        responses={
            200: OpenApiResponse(description="Logged out successfully."),
        },
    )
    def post(self, request):
        refresh_token_str = (
            request.data.get("refresh")
            or request.COOKIES.get("refresh_token")
        )

        if refresh_token_str:
            try:
                token = RefreshToken(refresh_token_str)
                token.blacklist()
            except Exception:
                pass  # If token is already expired or blacklisted, continue clearing cookies

        response = Response(
            {
                "success": True,
                "message": "Logged out successfully.",
            },
            status=status.HTTP_200_OK,
        )

        clear_auth_cookies(response)

        if request.user and request.user.is_authenticated:
            log_audit_event(
                action="LOGOUT",
                resource_type="User",
                resource_id=str(request.user.id),
                actor=request.user,
                request=request,
            )

        return response


class TokenRefreshView(APIView):
    """Rotates refresh token and returns refreshed access token."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh Access Token",
        description="Refreshes access token using the HttpOnly cookie or request body refresh token.",
        responses={
            200: OpenApiResponse(description="Token refreshed."),
            401: OpenApiResponse(description="Invalid or expired refresh token."),
        },
    )
    def post(self, request):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if not data.get("refresh"):
            cookie_refresh = request.COOKIES.get("refresh_token")
            if cookie_refresh:
                data["refresh"] = cookie_refresh

        serializer = SimpleJWTTokenRefreshSerializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response(
                {
                    "success": False,
                    "message": f"Invalid or expired refresh token: {str(e)}",
                    "errors": {"refresh": [str(e)]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token_str = serializer.validated_data.get("access")
        new_refresh_token_str = serializer.validated_data.get("refresh")

        response = Response(
            {
                "success": True,
                "message": "Token refreshed successfully.",
                "data": {
                    "tokens": {
                        "access": access_token_str,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )

        set_auth_cookies(
            response=response,
            access_token=access_token_str,
            refresh_token=new_refresh_token_str,
        )

        return response


class CurrentUserView(APIView):
    """Fetches profile and role information for currently authenticated user."""

    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        summary="Current Authenticated User",
        description="Returns identity and role information for the active session.",
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Unauthenticated."),
        },
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """Verifies user email using the verification token."""

    permission_classes = [AllowAny]
    throttle_classes = [EmailVerificationRateThrottle]

    @extend_schema(
        summary="Verify Email Address",
        description="Validates single-use verification token and activates verified status.",
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully."),
            400: OpenApiResponse(description="Invalid or expired token."),
        },
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data["token"]
        success, message, _ = verify_email_with_token(token_str, request=request)

        if not success:
            return Response(
                {
                    "success": False,
                    "message": message,
                    "errors": {"token": [message]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": message,
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """Resends email verification token to user."""

    permission_classes = [AllowAny]
    throttle_classes = [EmailVerificationRateThrottle]

    @extend_schema(
        summary="Resend Verification Email",
        description="Issues a fresh verification token if user is unverified. Preserves privacy.",
        request=ResendVerificationSerializer,
        responses={
            200: OpenApiResponse(description="Verification email queued."),
        },
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
            if not user.is_verified and user.is_active:
                create_verification_token(user)
        except User.DoesNotExist:
            pass

        return Response(
            {
                "success": True,
                "message": "If an unverified account exists for this email, a verification link has been sent.",
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """Initiates password reset workflow."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(
        summary="Forgot Password",
        description="Requests password reset token. Never leaks whether the target email exists.",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset email queued."),
        },
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        request_password_reset(email, request=request)

        return Response(
            {
                "success": True,
                "message": "If an account exists for this email, a reset link has been sent.",
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """Completes password reset with secure token."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(
        summary="Reset Password",
        description="Resets user password given a valid, unexpired single-use recovery token.",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful."),
            400: OpenApiResponse(description="Invalid token or validation error."),
        },
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data["token"]
        new_password = serializer.validated_data["password"]

        success, message, _ = reset_password_with_token(
            token_str, new_password, request=request
        )

        if not success:
            return Response(
                {
                    "success": False,
                    "message": message,
                    "errors": {"token": [message]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": message,
            },
            status=status.HTTP_200_OK,
        )
