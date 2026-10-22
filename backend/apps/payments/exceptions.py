from rest_framework import status
from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _


class PaymentException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A payment processing error occurred.")
    default_code = "payment_error"


class PaymentOrderException(PaymentException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Unable to create payment order.")
    default_code = "payment_order_error"


class PaymentVerificationException(PaymentException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Payment verification failed.")
    default_code = "payment_verification_failed"


class PaymentSignatureException(PaymentException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Invalid payment signature.")
    default_code = "invalid_signature"


class ReservationExpiredException(PaymentException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("Appointment reservation has expired. Please select a new slot.")
    default_code = "reservation_expired"


class PaymentConflictException(PaymentException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("Payment conflict detected.")
    default_code = "payment_conflict"


class WebhookVerificationException(PaymentException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Invalid webhook signature.")
    default_code = "invalid_webhook_signature"


class CommissionCalculationException(PaymentException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("Failed to calculate platform commission.")
    default_code = "commission_calculation_error"
