from django.urls import path
from .views import (
    CurrentUserView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    TokenRefreshView,
    VerifyEmailView,
)

app_name = "accounts"

urlpatterns = [
    # Core authentication
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", CurrentUserView.as_view(), name="current-user"),

    # Email verification
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),

    # Password management
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
