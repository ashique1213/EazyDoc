from typing import Optional, Tuple
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.tokens import Token

from .models import User, UserStatus


class CookieJWTAuthentication(JWTAuthentication):
    """
    Dual-transport JWT Authentication:
    1. Checks standard `Authorization: Bearer <token>` header first.
    2. Falls back to secure HttpOnly `access_token` cookie for web clients.
    3. Enforces real-time account status checks (rejects INACTIVE and SUSPENDED accounts).
    """

    def authenticate(self, request: Request) -> Optional[Tuple[User, Token]]:
        # 1. Check HTTP Authorization header
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        # 2. Check HttpOnly cookie
        cookie_name = getattr(settings, "JWT_AUTH_COOKIE", "access_token")
        raw_cookie_token = request.COOKIES.get(cookie_name)
        if raw_cookie_token:
            validated_token = self.get_validated_token(raw_cookie_token)
            return self.get_user(validated_token), validated_token

        return None

    def get_user(self, validated_token: Token) -> User:
        user = super().get_user(validated_token)

        # Real-time lifecycle and status enforcement
        if not user.is_active:
            raise AuthenticationFailed(_("User account is inactive."), code="user_inactive")

        if user.status == UserStatus.SUSPENDED:
            raise AuthenticationFailed(
                _("User account has been suspended. Please contact platform support."),
                code="user_suspended",
            )
        elif user.status == UserStatus.INACTIVE:
            raise AuthenticationFailed(_("User account is inactive."), code="user_inactive")

        return user


def set_auth_cookies(
    response,
    access_token: str,
    refresh_token: Optional[str] = None,
) -> None:
    """
    Sets secure HttpOnly cookies for JWT authentication.
    Access token: short-lived (15 mins), scoped to root.
    Refresh token: long-lived (7 days), scoped strictly to /api/v1/auth/.
    """
    secure = getattr(settings, "JWT_AUTH_COOKIE_SECURE", not settings.DEBUG)
    samesite = getattr(settings, "JWT_AUTH_COOKIE_SAME_SITE", "Lax")
    access_cookie_name = getattr(settings, "JWT_AUTH_COOKIE", "access_token")
    refresh_cookie_name = getattr(settings, "JWT_AUTH_REFRESH_COOKIE", "refresh_token")
    refresh_path = getattr(settings, "JWT_AUTH_REFRESH_COOKIE_PATH", "/api/v1/auth/")

    # Access Token Cookie (15 mins = 900 seconds)
    access_lifetime = getattr(
        settings, "SIMPLE_JWT", {}
    ).get("ACCESS_TOKEN_LIFETIME")
    access_max_age = int(access_lifetime.total_seconds()) if access_lifetime else 900

    response.set_cookie(
        key=access_cookie_name,
        value=str(access_token),
        max_age=access_max_age,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
    )

    # Refresh Token Cookie (7 days = 604800 seconds)
    if refresh_token:
        refresh_lifetime = getattr(
            settings, "SIMPLE_JWT", {}
        ).get("REFRESH_TOKEN_LIFETIME")
        refresh_max_age = int(refresh_lifetime.total_seconds()) if refresh_lifetime else 604800

        response.set_cookie(
            key=refresh_cookie_name,
            value=str(refresh_token),
            max_age=refresh_max_age,
            httponly=True,
            secure=secure,
            samesite=samesite,
            path=refresh_path,
        )


def clear_auth_cookies(response) -> None:
    """Clears all JWT auth cookies on logout."""
    access_cookie_name = getattr(settings, "JWT_AUTH_COOKIE", "access_token")
    refresh_cookie_name = getattr(settings, "JWT_AUTH_REFRESH_COOKIE", "refresh_token")
    refresh_path = getattr(settings, "JWT_AUTH_REFRESH_COOKIE_PATH", "/api/v1/auth/")

    response.delete_cookie(key=access_cookie_name, path="/")
    response.delete_cookie(key=refresh_cookie_name, path=refresh_path)


try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class CookieJWTScheme(OpenApiAuthenticationExtension):
        target_class = "apps.accounts.authentication.CookieJWTAuthentication"
        name = "CookieJWTAuth"

        def get_security_definition(self, auto_schema):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Dual-transport JWT authentication via Authorization Bearer header or HttpOnly access_token cookie.",
            }
except ImportError:
    pass

