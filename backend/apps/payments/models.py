import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentStatus(models.TextChoices):
    """Lifecycle status for an appointment payment."""
    NOT_REQUIRED = "NOT_REQUIRED", _("Not Required")
    PENDING = "PENDING", _("Pending")
    AUTHORIZED = "AUTHORIZED", _("Authorized")
    PAID = "PAID", _("Paid")
    FAILED = "FAILED", _("Failed")
    REFUND_PENDING = "REFUND_PENDING", _("Refund Pending")
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", _("Partially Refunded")
    REFUNDED = "REFUNDED", _("Refunded")


class CommissionStatus(models.TextChoices):
    """Settlement status for internal commission accounting records."""
    PENDING_SETTLEMENT = "PENDING_SETTLEMENT", _("Pending Settlement")
    SETTLED = "SETTLED", _("Settled")
    REFUNDED = "REFUNDED", _("Refunded")
    CANCELLED = "CANCELLED", _("Cancelled")


class WebhookProcessingStatus(models.TextChoices):
    """Processing state machine status for webhook events."""
    RECEIVED = "RECEIVED", _("Received")
    PROCESSED = "PROCESSED", _("Processed")
    FAILED = "FAILED", _("Failed")
    IGNORED = "IGNORED", _("Ignored")


class PaymentAuditAction(models.TextChoices):
    """Financial event types recorded in append-only payment audit trail."""
    ORDER_CREATED = "ORDER_CREATED", _("Payment Order Created")
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED", _("Payment Signature Verified")
    PAYMENT_FAILED = "PAYMENT_FAILED", _("Payment Failed")
    COMMISSION_CALCULATED = "COMMISSION_CALCULATED", _("Platform Commission Calculated")
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED", _("Gateway Webhook Received")
    WEBHOOK_PROCESSED = "WEBHOOK_PROCESSED", _("Gateway Webhook Processed")
    RECONCILIATION_DISCREPANCY = "RECONCILIATION_DISCREPANCY", _("Reconciliation Discrepancy Detected")
    REFUND_REQUESTED = "REFUND_REQUESTED", _("Refund Requested")


class Payment(models.Model):
    """
    Core financial transaction entity representing a payment attempt or completed payment
    for a patient appointment via Razorpay.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("appointment"),
        db_index=True,
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("patient"),
        db_index=True,
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("clinic"),
        db_index=True,
    )
    gateway_name = models.CharField(
        _("gateway name"),
        max_length=50,
        default="RAZORPAY",
        help_text=_("Payment gateway provider identifier."),
    )
    gateway_order_id = models.CharField(
        _("gateway order id"),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_("Unique gateway order reference (e.g. order_Kxyz123)."),
    )
    gateway_payment_id = models.CharField(
        _("gateway payment id"),
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text=_("Unique gateway payment identifier (e.g. pay_Kxyz123)."),
    )
    gateway_signature = models.CharField(
        _("gateway signature"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("HMAC-SHA256 signature provided by Razorpay Checkout."),
    )
    amount = models.DecimalField(
        _("payment amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total amount in project currency (INR)."),
    )
    currency = models.CharField(
        _("currency"),
        max_length=10,
        default="INR",
        help_text=_("Currency code (ISO 4217)."),
    )
    status = models.CharField(
        _("payment status"),
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    failure_code = models.CharField(
        _("failure code"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("Provider-supplied error code if payment failed."),
    )
    failure_description = models.TextField(
        _("failure description"),
        blank=True,
        default="",
        help_text=_("Sanitized error explanation safe for storage and audit."),
    )
    idempotency_key = models.CharField(
        _("idempotency key"),
        max_length=128,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Client request token preventing duplicate order generation."),
    )
    paid_at = models.DateTimeField(
        _("paid timestamp"),
        null=True,
        blank=True,
        help_text=_("Timestamp when payment was successfully captured or verified."),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Sanitized operational attributes (notes, receipts, timestamps)."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "payments_payment"
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=Decimal("0.00")),
                name="non_negative_payment_amount",
            ),
        ]
        indexes = [
            models.Index(fields=["appointment", "status"]),
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Payment[{self.gateway_order_id}] - {self.currency} {self.amount} ({self.status})"

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount < Decimal("0.00"):
            raise ValidationError({"amount": _("Payment amount cannot be negative.")})


class CommissionRecord(models.Model):
    """
    Dedicated internal financial transaction record capturing platform commission
    and clinic share for an eligible payment.
    Enforces the accounting invariant: gross_amount = commission_amount + clinic_share.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="commission_record",
        verbose_name=_("payment reference"),
        db_index=True,
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="commission_records",
        verbose_name=_("appointment reference"),
        db_index=True,
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.PROTECT,
        related_name="commission_records",
        verbose_name=_("clinic reference"),
        db_index=True,
    )
    gross_amount = models.DecimalField(
        _("gross payment amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total consultation amount charged to the patient."),
    )
    commission_rate = models.DecimalField(
        _("commission rate snapshot"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Percentage rate snapshot applied at settlement time."),
    )
    commission_amount = models.DecimalField(
        _("platform commission amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Retained platform commission amount."),
    )
    clinic_share = models.DecimalField(
        _("calculated clinic share"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Net allocation earmarked for the clinic."),
    )
    currency = models.CharField(
        _("currency"),
        max_length=10,
        default="INR",
    )
    status = models.CharField(
        _("financial record status"),
        max_length=30,
        choices=CommissionStatus.choices,
        default=CommissionStatus.PENDING_SETTLEMENT,
        db_index=True,
    )
    settled_at = models.DateTimeField(
        _("settled timestamp"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "payments_commission_record"
        verbose_name = _("commission record")
        verbose_name_plural = _("commission records")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(gross_amount__gte=Decimal("0.00")),
                name="non_negative_gross_amount",
            ),
            models.CheckConstraint(
                condition=models.Q(commission_amount__gte=Decimal("0.00")),
                name="non_negative_commission_amount",
            ),
            models.CheckConstraint(
                condition=models.Q(clinic_share__gte=Decimal("0.00")),
                name="non_negative_clinic_share",
            ),
        ]
        indexes = [
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["appointment", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Commission[{self.clinic.name}] Gross: {self.gross_amount} (Comm: {self.commission_amount}, Clinic: {self.clinic_share})"

    def clean(self):
        super().clean()
        if self.gross_amount is not None and self.commission_amount is not None and self.clinic_share is not None:
            if (self.commission_amount + self.clinic_share) != self.gross_amount:
                raise ValidationError(
                    _("Accounting invariant violated: gross amount (%(gross)s) must equal commission (%(comm)s) + clinic share (%(share)s).")
                    % {"gross": self.gross_amount, "comm": self.commission_amount, "share": self.clinic_share}
                )


class PaymentWebhookEvent(models.Model):
    """
    Audit and idempotency record capturing incoming webhook events from Razorpay.
    Prevents duplicate processing and out-of-order race conditions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(
        _("gateway event id"),
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Unique event ID provided by Razorpay (e.g. event_Kxyz123)."),
    )
    event_type = models.CharField(
        _("event type"),
        max_length=100,
        db_index=True,
        help_text=_("e.g. payment.captured, payment.failed, order.paid."),
    )
    gateway_name = models.CharField(
        _("gateway name"),
        max_length=50,
        default="RAZORPAY",
    )
    status = models.CharField(
        _("processing status"),
        max_length=30,
        choices=WebhookProcessingStatus.choices,
        default=WebhookProcessingStatus.RECEIVED,
        db_index=True,
    )
    payload = models.JSONField(
        _("sanitized payload"),
        default=dict,
        blank=True,
        help_text=_("Sanitized webhook payload containing no card or sensitive credentials."),
    )
    received_at = models.DateTimeField(_("received at"), auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(_("processed at"), null=True, blank=True)
    error_message = models.TextField(
        _("error message"),
        blank=True,
        default="",
        help_text=_("Details of processing error if event handling failed."),
    )

    class Meta:
        db_table = "payments_webhook_event"
        verbose_name = _("payment webhook event")
        verbose_name_plural = _("payment webhook events")
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["event_type", "status"]),
            models.Index(fields=["received_at"]),
        ]

    def __str__(self) -> str:
        return f"WebhookEvent[{self.event_id or self.id}] - {self.event_type} ({self.status})"


class PaymentAuditLog(models.Model):
    """
    Append-only audit trail capturing all financial state transitions, signature checks,
    commission recognitions, and gateway errors.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("payment"),
        db_index=True,
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_audit_logs",
        verbose_name=_("appointment"),
        db_index=True,
    )
    event_type = models.CharField(
        _("event type"),
        max_length=100,
        choices=PaymentAuditAction.choices,
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("actor"),
    )
    ip_address = models.GenericIPAddressField(_("ip address"), null=True, blank=True)
    data = models.JSONField(_("event payload details"), default=dict, blank=True)
    created_at = models.DateTimeField(_("timestamp"), auto_now_add=True, db_index=True)

    class Meta:
        db_table = "payments_audit_log"
        verbose_name = _("payment audit log")
        verbose_name_plural = _("payment audit logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["payment", "created_at"]),
            models.Index(fields=["appointment", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"PaymentAudit[{self.created_at}] {self.event_type} - {self.payment_id or 'N/A'}"


class PlatformSetting(models.Model):
    """
    Platform-wide administrative configuration parameters.
    Allows runtime modification of default commission rates and platform policies.
    """
    key = models.CharField(_("setting key"), max_length=100, unique=True, db_index=True)
    value = models.JSONField(_("setting value"), default=dict)
    description = models.CharField(_("description"), max_length=255, blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("updated by"),
    )
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "payments_platform_setting"
        verbose_name = _("platform setting")
        verbose_name_plural = _("platform settings")

    def __str__(self) -> str:
        return f"{self.key}: {self.value}"

    @classmethod
    def get_default_commission_rate(cls) -> Decimal:
        try:
            setting = cls.objects.filter(key="default_commission_rate").first()
            if setting and isinstance(setting.value, dict) and "rate" in setting.value:
                return Decimal(str(setting.value["rate"]))
        except Exception:
            pass
        return getattr(settings, "PLATFORM_DEFAULT_COMMISSION_RATE", Decimal("5.00"))

    @classmethod
    def set_default_commission_rate(cls, rate: Decimal, user=None) -> "PlatformSetting":
        setting, _ = cls.objects.get_or_create(
            key="default_commission_rate",
            defaults={"description": "Platform default commission rate percentage"},
        )
        setting.value = {"rate": str(rate)}
        setting.updated_by = user
        setting.save()
        return setting
