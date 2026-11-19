import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SubscriptionTier(models.TextChoices):
    """SaaS plan product tiers."""
    FREE = "FREE", _("Free")
    STARTER = "STARTER", _("Starter")
    PROFESSIONAL = "PROFESSIONAL", _("Professional")
    ENTERPRISE = "ENTERPRISE", _("Enterprise")


class BillingInterval(models.TextChoices):
    """Recurring billing cadence intervals."""
    MONTHLY = "MONTHLY", _("Monthly")
    YEARLY = "YEARLY", _("Yearly")


class SubscriptionStatus(models.TextChoices):
    """
    Finite state machine statuses for a clinic's SaaS subscription.
    Transitions:
      TRIALING -> ACTIVE (Payment success)
      TRIALING -> EXPIRED (Trial elapsed without payment)
      ACTIVE -> PAST_DUE (Renewal charge failed, enters grace period)
      ACTIVE -> CANCELLED (Owner requests cancel at period end)
      PAST_DUE -> ACTIVE (Retry payment succeeds)
      PAST_DUE -> EXPIRED (Grace period expires without payment)
      CANCELLED -> EXPIRED (Current billing cycle completes)
      ACTIVE / PAST_DUE / TRIALING -> SUSPENDED (Administrative action)
      SUSPENDED -> ACTIVE (Administrative reinstatement)
      INCOMPLETE -> ACTIVE (Checkout completed and verified)
    """
    TRIALING = "TRIALING", _("Trialing")
    ACTIVE = "ACTIVE", _("Active")
    PAST_DUE = "PAST_DUE", _("Past Due")
    CANCELLED = "CANCELLED", _("Cancelled")
    EXPIRED = "EXPIRED", _("Expired")
    SUSPENDED = "SUSPENDED", _("Suspended")
    INCOMPLETE = "INCOMPLETE", _("Incomplete")


class SubscriptionPaymentStatus(models.TextChoices):
    """Gateway transaction statuses for SaaS billing charges."""
    PENDING = "PENDING", _("Pending")
    SUCCESS = "SUCCESS", _("Success")
    FAILED = "FAILED", _("Failed")
    REFUNDED = "REFUNDED", _("Refunded")


class InvoiceStatus(models.TextChoices):
    """Legal accounting statuses for billing invoices."""
    DRAFT = "DRAFT", _("Draft")
    PAID = "PAID", _("Paid")
    UNPAID = "UNPAID", _("Unpaid")
    VOID = "VOID", _("Void")


class SubscriptionEventType(models.TextChoices):
    """Categorized audit actions recorded in immutable subscription event ledger."""
    TRIAL_STARTED = "TRIAL_STARTED", _("Trial Started")
    TRIAL_EXPIRING_SOON = "TRIAL_EXPIRING_SOON", _("Trial Expiring Soon")
    TRIAL_EXPIRED = "TRIAL_EXPIRED", _("Trial Expired")
    PLAN_UPGRADED = "PLAN_UPGRADED", _("Plan Upgraded")
    PLAN_DOWNGRADED = "PLAN_DOWNGRADED", _("Plan Downgraded")
    PAYMENT_INITIATED = "PAYMENT_INITIATED", _("Payment Initiated")
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS", _("Payment Succeeded")
    PAYMENT_FAILED = "PAYMENT_FAILED", _("Payment Failed")
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED", _("Cancellation Requested")
    CANCELLED = "CANCELLED", _("Cancelled")
    RENEWED = "RENEWED", _("Renewed")
    PAST_DUE_ENTERED = "PAST_DUE_ENTERED", _("Past Due Entered")
    EXPIRED = "EXPIRED", _("Subscription Expired")
    SUSPENDED = "SUSPENDED", _("Subscription Suspended")
    REINSTATED = "REINSTATED", _("Subscription Reinstated")
    LIMIT_OVERRIDE = "LIMIT_OVERRIDE", _("Limit Overridden by Admin")


class SubscriptionPlan(models.Model):
    """
    Configurable SaaS tier catalog defining quotas, pricing, and capabilities.
    Pricing and quotas are managed in DB, never hardcoded.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("plan name"), max_length=100)
    code = models.SlugField(_("plan code"), max_length=100, unique=True, db_index=True)
    tier = models.CharField(
        _("tier"),
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
        db_index=True,
    )
    billing_interval = models.CharField(
        _("billing interval"),
        max_length=20,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
        db_index=True,
    )
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Price per billing interval in project currency (INR)."),
    )
    currency = models.CharField(_("currency"), max_length=10, default="INR")
    description = models.TextField(_("description"), blank=True, default="")
    
    # Entitlement Limits (null represents unlimited)
    max_doctors = models.PositiveIntegerField(
        _("maximum doctors"),
        null=True,
        blank=True,
        help_text=_("Maximum affiliated doctors permitted. Null means unlimited."),
    )
    max_staff = models.PositiveIntegerField(
        _("maximum staff members"),
        null=True,
        blank=True,
        help_text=_("Maximum staff accounts permitted. Null means unlimited."),
    )
    max_appointments_per_month = models.PositiveIntegerField(
        _("maximum monthly appointments"),
        null=True,
        blank=True,
        help_text=_("Monthly booking limit. Null means unlimited."),
    )
    
    # Feature capabilities list & structured flags
    features = models.JSONField(
        _("feature list"),
        default=list,
        help_text=_("Human-readable feature points for marketing and display."),
    )
    feature_flags = models.JSONField(
        _("feature flags"),
        default=dict,
        help_text=_("Machine-readable boolean flags (e.g. {'advanced_analytics': true, 'export_reports': true})."),
    )
    trial_days = models.PositiveIntegerField(
        _("trial days"),
        default=14,
        help_text=_("Default trial duration when starting this plan."),
    )
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)
    is_public = models.BooleanField(_("is public / selectable"), default=True, db_index=True)
    sort_order = models.PositiveIntegerField(_("display sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("subscription plan")
        verbose_name_plural = _("subscription plans")
        ordering = ["sort_order", "price"]
        indexes = [
            models.Index(fields=["tier", "billing_interval", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.tier} - {self.billing_interval}) - ₹{self.price}"

    @property
    def is_free(self) -> bool:
        return self.price == Decimal("0.00") or self.tier == SubscriptionTier.FREE

    def clean(self):
        super().clean()
        if self.price < Decimal("0.00"):
            raise ValidationError({"price": _("Price cannot be negative.")})


class ClinicSubscription(models.Model):
    """
    Active SaaS subscription binding a Clinic entity to a SubscriptionPlan.
    Maintains billing periods, trial lifecycle, and entitlement overrides.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.OneToOneField(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name=_("clinic"),
        db_index=True,
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="clinic_subscriptions",
        verbose_name=_("current plan"),
        db_index=True,
    )
    status = models.CharField(
        _("subscription status"),
        max_length=30,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIALING,
        db_index=True,
    )
    billing_interval = models.CharField(
        _("billing interval"),
        max_length=20,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
    )
    current_period_start = models.DateTimeField(_("current period start"), default=timezone.now)
    current_period_end = models.DateTimeField(_("current period end"), null=True, blank=True, db_index=True)
    
    # Free trial lifecycle & abuse prevention
    trial_start = models.DateTimeField(_("trial start"), null=True, blank=True)
    trial_end = models.DateTimeField(_("trial end"), null=True, blank=True, db_index=True)
    has_used_trial = models.BooleanField(
        _("has used free trial"),
        default=False,
        db_index=True,
        help_text=_("Ensures each clinic can only consume one free trial."),
    )
    
    # Cancellation & grace period tracking
    cancel_at_period_end = models.BooleanField(
        _("cancel at period end"),
        default=False,
        help_text=_("If true, subscription remains active until period end, then expires."),
    )
    cancelled_at = models.DateTimeField(_("cancelled timestamp"), null=True, blank=True)
    cancellation_reason = models.TextField(_("cancellation reason"), blank=True, default="")
    past_due_since = models.DateTimeField(_("past due timestamp"), null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(_("grace period ends at"), null=True, blank=True)
    
    # External gateway references
    razorpay_customer_id = models.CharField(_("Razorpay customer ID"), max_length=100, blank=True, default="")
    razorpay_subscription_id = models.CharField(_("Razorpay subscription ID"), max_length=100, blank=True, default="")
    
    # Custom administrative entitlement overrides
    custom_doctor_limit = models.PositiveIntegerField(
        _("custom doctor limit override"),
        null=True,
        blank=True,
        help_text=_("If set, overrides plan max_doctors limit."),
    )
    custom_staff_limit = models.PositiveIntegerField(
        _("custom staff limit override"),
        null=True,
        blank=True,
        help_text=_("If set, overrides plan max_staff limit."),
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("clinic subscription")
        verbose_name_plural = _("clinic subscriptions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "current_period_end"]),
            models.Index(fields=["status", "trial_end"]),
        ]

    def __str__(self) -> str:
        return f"{self.clinic.name} — {self.plan.name} ({self.status})"

    @property
    def is_in_trial(self) -> bool:
        if self.status == SubscriptionStatus.TRIALING:
            if self.trial_end and timezone.now() > self.trial_end:
                return False
            return True
        return False

    @property
    def is_usable(self) -> bool:
        """Indicates if the clinic currently retains normal operational access."""
        if self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.CANCELLED]:
            return True
        if self.status == SubscriptionStatus.PAST_DUE:
            if self.grace_period_ends_at and timezone.now() <= self.grace_period_ends_at:
                return True
            return False
        return False

    @property
    def effective_max_doctors(self) -> int | None:
        if self.custom_doctor_limit is not None:
            return self.custom_doctor_limit
        return self.plan.max_doctors

    @property
    def effective_max_staff(self) -> int | None:
        if self.custom_staff_limit is not None:
            return self.custom_staff_limit
        return self.plan.max_staff

    @property
    def days_remaining_in_trial(self) -> int:
        if not self.is_in_trial or not self.trial_end:
            return 0
        diff = self.trial_end - timezone.now()
        return max(0, diff.days)


class SubscriptionPayment(models.Model):
    """
    Dedicated financial charge ledger for clinic SaaS subscriptions.
    Completely isolated from patient appointment consultation transactions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        ClinicSubscription,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("subscription"),
        db_index=True,
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="subscription_payments",
        verbose_name=_("clinic"),
        db_index=True,
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("purchased plan"),
    )
    amount = models.DecimalField(
        _("payment amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total charged amount in INR."),
    )
    currency = models.CharField(_("currency"), max_length=10, default="INR")
    status = models.CharField(
        _("payment status"),
        max_length=30,
        choices=SubscriptionPaymentStatus.choices,
        default=SubscriptionPaymentStatus.PENDING,
        db_index=True,
    )
    billing_interval = models.CharField(
        _("billing interval"),
        max_length=20,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
    )
    razorpay_order_id = models.CharField(
        _("Razorpay order ID"),
        max_length=100,
        unique=True,
        db_index=True,
    )
    razorpay_payment_id = models.CharField(
        _("Razorpay payment ID"),
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    razorpay_signature = models.CharField(
        _("Razorpay signature"),
        max_length=255,
        null=True,
        blank=True,
    )
    idempotency_key = models.CharField(
        _("idempotency key"),
        max_length=128,
        null=True,
        blank=True,
        db_index=True,
    )
    error_code = models.CharField(_("gateway error code"), max_length=100, blank=True, default="")
    error_description = models.TextField(_("gateway error description"), blank=True, default="")
    paid_at = models.DateTimeField(_("paid timestamp"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("subscription payment")
        verbose_name_plural = _("subscription payments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["clinic", "status"]),
        ]

    def __str__(self) -> str:
        return f"Payment {self.razorpay_order_id} - ₹{self.amount} ({self.status})"


class SubscriptionInvoice(models.Model):
    """
    Immutable legal financial invoice generated for every completed subscription charge.
    Captures snapshot of clinic details, GST taxes, line items, and period boundaries.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(
        _("invoice number"),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Human-readable sequential invoice ID (e.g. INV-202611-0001)."),
    )
    subscription = models.ForeignKey(
        ClinicSubscription,
        on_delete=models.CASCADE,
        related_name="invoices",
        verbose_name=_("subscription"),
        db_index=True,
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="subscription_invoices",
        verbose_name=_("clinic"),
        db_index=True,
    )
    payment = models.OneToOneField(
        SubscriptionPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice",
        verbose_name=_("payment transaction"),
    )
    plan_name = models.CharField(_("plan name snapshot"), max_length=100)
    subtotal_amount = models.DecimalField(_("subtotal amount"), max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(
        _("tax rate percentage"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("18.00"),
        help_text=_("Applicable GST percentage (e.g. 18.00)."),
    )
    tax_amount = models.DecimalField(_("tax amount"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(_("total amount"), max_digits=10, decimal_places=2)
    currency = models.CharField(_("currency"), max_length=10, default="INR")
    status = models.CharField(
        _("invoice status"),
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PAID,
        db_index=True,
    )
    billing_period_start = models.DateTimeField(_("billing period start"))
    billing_period_end = models.DateTimeField(_("billing period end"))
    
    # Immutable audit snapshots
    line_items = models.JSONField(
        _("line items"),
        default=list,
        help_text=_("List of line items with description, unit price, quantity, tax, total."),
    )
    billing_details = models.JSONField(
        _("billing details snapshot"),
        default=dict,
        help_text=_("Snapshot of clinic name, address, GSTIN, email at invoice time."),
    )
    paid_at = models.DateTimeField(_("paid timestamp"), null=True, blank=True)
    pdf_file = models.FileField(
        _("invoice PDF file"),
        upload_to="invoices/saas/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("subscription invoice")
        verbose_name_plural = _("subscription invoices")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number} — {self.clinic.name} — ₹{self.total_amount}"


class SubscriptionEvent(models.Model):
    """
    Append-only audit trail logging every subscription lifecycle mutation,
    payment, upgrade, downgrade, cancellation, and administrative override.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        ClinicSubscription,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("subscription"),
        db_index=True,
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="subscription_events",
        verbose_name=_("clinic"),
        db_index=True,
    )
    event_type = models.CharField(
        _("event type"),
        max_length=50,
        choices=SubscriptionEventType.choices,
        db_index=True,
    )
    old_status = models.CharField(_("previous status"), max_length=30, blank=True, default="")
    new_status = models.CharField(_("new status"), max_length=30, blank=True, default="")
    old_plan_name = models.CharField(_("previous plan"), max_length=100, blank=True, default="")
    new_plan_name = models.CharField(_("new plan"), max_length=100, blank=True, default="")
    reason = models.TextField(_("reason or notes"), blank=True, default="")
    metadata = models.JSONField(_("event metadata"), default=dict, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_events_triggered",
        verbose_name=_("triggered by"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("subscription event")
        verbose_name_plural = _("subscription events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "event_type", "created_at"]),
            models.Index(fields=["subscription", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.clinic.name} - {self.event_type}"
