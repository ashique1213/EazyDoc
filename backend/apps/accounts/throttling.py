from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """Throttles login attempts to prevent credential brute-forcing."""
    scope = "auth_login"


class RegisterRateThrottle(ScopedRateThrottle):
    """Throttles registration requests to prevent bot account creation."""
    scope = "auth_register"


class PasswordResetRateThrottle(ScopedRateThrottle):
    """Throttles password reset requests to protect against email enumeration & spam."""
    scope = "auth_password_reset"


class EmailVerificationRateThrottle(ScopedRateThrottle):
    """Throttles verification requests to mitigate OTP/token probing."""
    scope = "auth_verification"
