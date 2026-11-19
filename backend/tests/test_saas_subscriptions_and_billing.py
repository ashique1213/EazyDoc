import hashlib
import hmac
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus, ClinicStaff
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.subscriptions.models import (
    BillingInterval,
    ClinicSubscription,
    InvoiceStatus,
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionInvoice,
    SubscriptionPayment,
    SubscriptionPaymentStatus,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
)
from apps.subscriptions.services.analytics import SubscriptionAnalyticsService
from apps.subscriptions.services.billing import SubscriptionBillingService
from apps.subscriptions.services.entitlements import EntitlementService
from apps.subscriptions.services.invoices import InvoiceService
from apps.subscriptions.services.lifecycle import SubscriptionLifecycleService
from apps.subscriptions.tasks import (
    check_expiring_trials_task,
    check_subscription_renewals_and_expiry_task,
)

User = get_user_model()


class SaaSPlanAndLifecycleTests(TestCase):
    """Unit and service tests for plan creation, lifecycle state transitions, and audit trail."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@testclinic.com",
            password="SecurePassword123!",
            role=UserRole.CLINIC_OWNER,
            first_name="Dr. Owner",
            last_name="Surgeon",
        )
        self.clinic = Clinic.objects.create(
            name="Apollo Polyclinic",
            slug="apollo-polyclinic",
            owner=self.owner,
            email="contact@apollo.com",
            phone="9876543210",
            address_line_1="100 Medical Enclave",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            status=ClinicStatus.APPROVED,
        )

        self.free_plan = SubscriptionPlan.objects.create(
            name="Free Community",
            code="free-monthly",
            tier=SubscriptionTier.FREE,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("0.00"),
            max_doctors=1,
            max_staff=1,
            max_appointments_per_month=50,
            features=["1 Doctor", "Basic Dashboard"],
            feature_flags={"advanced_analytics": False, "export_reports": False},
            trial_days=0,
            is_active=True,
        )

        self.starter_plan = SubscriptionPlan.objects.create(
            name="Starter Plan",
            code="starter-monthly",
            tier=SubscriptionTier.STARTER,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("1499.00"),
            max_doctors=3,
            max_staff=3,
            max_appointments_per_month=300,
            features=["Up to 3 Doctors", "CSV Reports"],
            feature_flags={"advanced_analytics": True, "export_reports": True, "export_pdf": False},
            trial_days=14,
            is_active=True,
        )

        self.pro_plan = SubscriptionPlan.objects.create(
            name="Professional Suite",
            code="professional-monthly",
            tier=SubscriptionTier.PROFESSIONAL,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("3999.00"),
            max_doctors=10,
            max_staff=10,
            max_appointments_per_month=1500,
            features=["Up to 10 Doctors", "Full Ledger", "PDF Reports"],
            feature_flags={"advanced_analytics": True, "export_reports": True, "export_pdf": True},
            trial_days=14,
            is_active=True,
        )

        self.enterprise_plan = SubscriptionPlan.objects.create(
            name="Enterprise Hospital",
            code="enterprise-monthly",
            tier=SubscriptionTier.ENTERPRISE,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("9999.00"),
            max_doctors=None,
            max_staff=None,
            max_appointments_per_month=None,
            features=["Unlimited Doctors", "Custom SLA"],
            feature_flags={"advanced_analytics": True, "export_reports": True, "export_pdf": True, "unlimited_capacity": True},
            trial_days=14,
            is_active=True,
        )

    def test_trial_initialization_on_new_clinic(self):
        """A new clinic starts in 14-day TRIALING status on Starter tier."""
        sub = SubscriptionLifecycleService.initialize_clinic_subscription(self.clinic)

        self.assertEqual(sub.status, SubscriptionStatus.TRIALING)
        self.assertTrue(sub.is_in_trial)
        self.assertTrue(sub.has_used_trial)
        self.assertIsNotNone(sub.trial_end)
        self.assertEqual(sub.plan.tier, SubscriptionTier.STARTER)

        # Audit event recorded
        event = SubscriptionEvent.objects.filter(clinic=self.clinic, event_type=SubscriptionEventType.TRIAL_STARTED).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.new_status, SubscriptionStatus.TRIALING)

    def test_activate_subscription_sets_period_boundaries(self):
        """Activating a paid subscription sets ACTIVE status and 30-day period."""
        sub = SubscriptionLifecycleService.initialize_clinic_subscription(self.clinic)
        activated_sub = SubscriptionLifecycleService.activate_subscription(
            subscription=sub,
            new_plan=self.pro_plan,
            billing_interval=BillingInterval.MONTHLY,
            reason="Card payment verified",
        )

        self.assertEqual(activated_sub.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(activated_sub.plan, self.pro_plan)
        self.assertFalse(activated_sub.cancel_at_period_end)
        self.assertIsNotNone(activated_sub.current_period_end)
        diff_days = (activated_sub.current_period_end - activated_sub.current_period_start).days
        self.assertIn(diff_days, [29, 30, 31])

    def test_mark_past_due_and_grace_period(self):
        """Failed renewal triggers PAST_DUE status with 5-day grace period."""
        sub = SubscriptionLifecycleService.initialize_clinic_subscription(self.clinic)
        SubscriptionLifecycleService.activate_subscription(sub, self.pro_plan, BillingInterval.MONTHLY)

        past_due_sub = SubscriptionLifecycleService.mark_past_due(sub, reason="Insufficient funds", grace_period_days=5)

        self.assertEqual(past_due_sub.status, SubscriptionStatus.PAST_DUE)
        self.assertIsNotNone(past_due_sub.grace_period_ends_at)
        self.assertTrue(past_due_sub.is_usable)  # Remains usable during grace period!

    def test_request_cancellation_preserves_access_until_period_end(self):
        """Cancellation keeps subscription active until period ends without deleting resources."""
        sub = SubscriptionLifecycleService.initialize_clinic_subscription(self.clinic)
        SubscriptionLifecycleService.activate_subscription(sub, self.pro_plan, BillingInterval.MONTHLY)

        cancelled_sub = SubscriptionLifecycleService.request_cancellation(sub, reason="Relocating clinic")

        self.assertTrue(cancelled_sub.cancel_at_period_end)
        self.assertEqual(cancelled_sub.status, SubscriptionStatus.CANCELLED)
        self.assertEqual(cancelled_sub.cancellation_reason, "Relocating clinic")
        self.assertTrue(cancelled_sub.is_usable)  # Operational access remains active!

    def test_expire_subscription_falls_back_to_free_tier_non_destructively(self):
        """Expiring subscription gracefully reverts to Free plan; zero clinic records deleted."""
        sub = SubscriptionLifecycleService.initialize_clinic_subscription(self.clinic)
        SubscriptionLifecycleService.activate_subscription(sub, self.pro_plan, BillingInterval.MONTHLY)

        expired_sub = SubscriptionLifecycleService.expire_subscription(sub, fallback_to_free=True)

        self.assertEqual(expired_sub.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(expired_sub.plan.tier, SubscriptionTier.FREE)


class EntitlementAndQuotaEnforcementTests(TestCase):
    """Tests checking doctor limits, staff limits, and feature flags."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner_quota@test.com",
            password="SecurePassword123!",
            role=UserRole.CLINIC_OWNER,
        )
        self.clinic = Clinic.objects.create(
            name="Apex Health Center",
            slug="apex-health-center",
            owner=self.owner,
            email="contact@apex.com",
            phone="9876543211",
            address_line_1="200 Main Street",
            city="Chennai",
            state="Tamil Nadu",
            pincode="600001",
            status=ClinicStatus.APPROVED,
        )

        self.starter_plan = SubscriptionPlan.objects.create(
            name="Starter Plan",
            code="starter-monthly",
            tier=SubscriptionTier.STARTER,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("1499.00"),
            max_doctors=2,  # Limit to 2 doctors
            max_staff=2,    # Limit to 2 staff
            max_appointments_per_month=100,
            feature_flags={"advanced_analytics": True, "export_reports": True, "export_pdf": False},
            is_active=True,
        )

        self.subscription = ClinicSubscription.objects.create(
            clinic=self.clinic,
            plan=self.starter_plan,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

    def _create_verified_doctor(self, email: str, license_number: str) -> Doctor:
        user = User.objects.create_user(
            email=email,
            password="SecurePassword123!",
            role=UserRole.DOCTOR,
            first_name="Dr.",
            last_name="Specialist",
        )
        return Doctor.objects.create(
            user=user,
            full_name=f"{user.first_name} {user.last_name}",
            registration_number=license_number,
            registration_council="Karnataka Medical Council",
            specialization="General Medicine",
            qualifications="MBBS, MD",
            years_of_experience=8,
            verification_status=DoctorVerificationStatus.VERIFIED,
            is_verified=True,
        )

    def test_doctor_limit_enforcement(self):
        """Allows affiliating up to max_doctors; blocks adding beyond the limit."""
        doc1 = self._create_verified_doctor("doc1@test.com", "LIC-0001")
        doc2 = self._create_verified_doctor("doc2@test.com", "LIC-0002")
        doc3 = self._create_verified_doctor("doc3@test.com", "LIC-0003")

        # Initially 0 doctors
        can_add, _ = EntitlementService.can_add_doctor(self.clinic)
        self.assertTrue(can_add)

        # Associate Doctor 1
        DoctorClinic.objects.create(doctor=doc1, clinic=self.clinic, status=DoctorClinicStatus.ACTIVE)
        can_add, _ = EntitlementService.can_add_doctor(self.clinic)
        self.assertTrue(can_add)

        # Associate Doctor 2 (Limit reached: 2 / 2)
        DoctorClinic.objects.create(doctor=doc2, clinic=self.clinic, status=DoctorClinicStatus.INVITED)
        can_add, err = EntitlementService.can_add_doctor(self.clinic)
        self.assertFalse(can_add)
        self.assertIn("limit of 2 reached", err)

        # Removed doctor frees up quota
        assoc1 = DoctorClinic.objects.get(doctor=doc1, clinic=self.clinic)
        assoc1.status = DoctorClinicStatus.REMOVED
        assoc1.save()

        can_add_now, _ = EntitlementService.can_add_doctor(self.clinic)
        self.assertTrue(can_add_now)

    def test_custom_limit_override(self):
        """Super Admin custom_doctor_limit overrides plan max_doctors."""
        self.subscription.custom_doctor_limit = 5
        self.subscription.save()

        doc1 = self._create_verified_doctor("doc_ov1@test.com", "LIC-OV01")
        doc2 = self._create_verified_doctor("doc_ov2@test.com", "LIC-OV02")
        DoctorClinic.objects.create(doctor=doc1, clinic=self.clinic, status=DoctorClinicStatus.ACTIVE)
        DoctorClinic.objects.create(doctor=doc2, clinic=self.clinic, status=DoctorClinicStatus.ACTIVE)

        # With plan max=2, but override=5, clinic can still add more doctors
        can_add, _ = EntitlementService.can_add_doctor(self.clinic)
        self.assertTrue(can_add)

    def test_staff_limit_enforcement(self):
        """Allows creating staff up to max_staff, then blocks further additions."""
        staff_user1 = User.objects.create_user(email="staff1@test.com", password="P1", role=UserRole.STAFF)
        staff_user2 = User.objects.create_user(email="staff2@test.com", password="P2", role=UserRole.STAFF)

        ClinicStaff.objects.create(clinic=self.clinic, user=staff_user1, is_active=True)
        can_add, _ = EntitlementService.can_add_staff(self.clinic)
        self.assertTrue(can_add)

        ClinicStaff.objects.create(clinic=self.clinic, user=staff_user2, is_active=True)
        can_add, err = EntitlementService.can_add_staff(self.clinic)
        self.assertFalse(can_add)
        self.assertIn("Staff seat limit of 2 reached", err)

    def test_feature_flag_entitlements(self):
        """Verifies boolean feature entitlement flags against active plan."""
        self.assertTrue(EntitlementService.has_feature(self.clinic, "advanced_analytics"))
        self.assertTrue(EntitlementService.has_feature(self.clinic, "export_reports"))
        self.assertFalse(EntitlementService.has_feature(self.clinic, "export_pdf"))


class BillingInvoicingAndWebhooksTests(TestCase):
    """Tests checkout order creation, signature verification, invoice generation, and webhooks."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="billing_owner@test.com",
            password="SecurePassword123!",
            role=UserRole.CLINIC_OWNER,
            first_name="Priya",
            last_name="Sharma",
        )
        self.clinic = Clinic.objects.create(
            name="Care Clinic",
            slug="care-clinic",
            owner=self.owner,
            email="contact@care.com",
            phone="9123456789",
            address_line_1="50 Outer Ring Road",
            city="Hyderabad",
            state="Telangana",
            pincode="500081",
            status=ClinicStatus.APPROVED,
        )
        self.pro_plan = SubscriptionPlan.objects.create(
            name="Professional Suite",
            code="professional-monthly",
            tier=SubscriptionTier.PROFESSIONAL,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("3999.00"),
            currency="INR",
            max_doctors=10,
            max_staff=10,
            is_active=True,
        )

    def test_create_checkout_order_creates_pending_payment(self):
        """Creates an isolated SubscriptionPayment record in PENDING state."""
        order_data = SubscriptionBillingService.create_checkout_order(
            clinic=self.clinic,
            plan=self.pro_plan,
            billing_interval=BillingInterval.MONTHLY,
            idempotency_key="idemp_checkout_123",
        )

        self.assertFalse(order_data["free_plan_activated"])
        self.assertIn("order_id", order_data)
        self.assertEqual(order_data["amount"], 399900)  # Paise
        self.assertEqual(order_data["amount_display"], "3999.00")

        payment = SubscriptionPayment.objects.get(razorpay_order_id=order_data["order_id"])
        self.assertEqual(payment.status, SubscriptionPaymentStatus.PENDING)
        self.assertEqual(payment.amount, Decimal("3999.00"))

    def test_verify_checkout_payment_activates_and_generates_invoice(self):
        """Validates payment signature, activates subscription, and generates tax invoice."""
        order_data = SubscriptionBillingService.create_checkout_order(
            clinic=self.clinic,
            plan=self.pro_plan,
            billing_interval=BillingInterval.MONTHLY,
        )
        order_id = order_data["order_id"]
        payment_id = "pay_test_abc123"

        # Generate HMAC-SHA256 signature using settings.RAZORPAY_KEY_SECRET
        message = f"{order_id}|{payment_id}".encode("utf-8")
        secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
        signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

        payment, invoice = SubscriptionBillingService.verify_checkout_payment(
            clinic=self.clinic,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
            user=self.owner,
        )

        self.assertEqual(payment.status, SubscriptionPaymentStatus.SUCCESS)
        self.assertEqual(payment.subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(payment.subscription.plan, self.pro_plan)

        # Verify Invoice
        self.assertIsNotNone(invoice)
        self.assertTrue(invoice.invoice_number.startswith("INV-"))
        self.assertEqual(invoice.status, InvoiceStatus.PAID)
        self.assertEqual(invoice.total_amount, Decimal("3999.00"))
        # 18% GST breakdown
        self.assertEqual(invoice.tax_rate, Decimal("18.00"))
        self.assertAlmostEqual(float(invoice.subtotal_amount + invoice.tax_amount), 3999.0, places=2)

    def test_invoice_html_rendering(self):
        """Renders standalone printable HTML invoice containing GST breakdown and branding."""
        sub = SubscriptionLifecycleService.initialize_clinic_subscription(self.clinic)
        payment = SubscriptionPayment.objects.create(
            subscription=sub,
            clinic=self.clinic,
            plan=self.pro_plan,
            amount=Decimal("3999.00"),
            currency="INR",
            status=SubscriptionPaymentStatus.SUCCESS,
            billing_interval=BillingInterval.MONTHLY,
            razorpay_order_id="order_test_render_01",
            razorpay_payment_id="pay_test_render_01",
            paid_at=timezone.now(),
        )
        invoice = InvoiceService.generate_invoice_for_payment(payment, sub)
        html = InvoiceService.render_invoice_html(invoice)

        self.assertIn("TAX INVOICE", html)
        self.assertIn(invoice.invoice_number, html)
        self.assertIn("Care Clinic", html)
        self.assertIn("Health Technologies", html)
        self.assertIn("Eazy<span>Doc</span>", html)
        self.assertIn("CGST (9.00%)", html)
        self.assertIn("SGST (9.00%)", html)

    def test_webhook_event_processing(self):
        """Webhook payment.captured idempotently activates subscription."""
        order_data = SubscriptionBillingService.create_checkout_order(
            clinic=self.clinic,
            plan=self.pro_plan,
            billing_interval=BillingInterval.MONTHLY,
        )
        order_id = order_data["order_id"]

        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook_test_01",
                        "order_id": order_id,
                        "amount": 399900,
                        "status": "captured",
                    }
                }
            },
        }

        success, msg = SubscriptionBillingService.process_webhook_event(webhook_payload)
        self.assertTrue(success)

        payment = SubscriptionPayment.objects.get(razorpay_order_id=order_id)
        self.assertEqual(payment.status, SubscriptionPaymentStatus.SUCCESS)
        self.assertEqual(payment.subscription.status, SubscriptionStatus.ACTIVE)


class CeleryTaskAutomationTests(TestCase):
    """Tests periodic Celery tasks for trial expiration, renewal reminders, and grace period handling."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="celery_owner@test.com",
            password="SecurePassword123!",
            role=UserRole.CLINIC_OWNER,
        )
        self.clinic = Clinic.objects.create(
            name="Beacon Hospital",
            slug="beacon-hospital",
            owner=self.owner,
            email="contact@beacon.com",
            phone="9000000001",
            address_line_1="1 Central Way",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            status=ClinicStatus.APPROVED,
        )
        self.free_plan = SubscriptionPlan.objects.create(
            name="Free Community",
            code="free-monthly",
            tier=SubscriptionTier.FREE,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("0.00"),
            is_active=True,
        )
        self.pro_plan = SubscriptionPlan.objects.create(
            name="Professional Suite",
            code="professional-monthly",
            tier=SubscriptionTier.PROFESSIONAL,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("3999.00"),
            is_active=True,
        )

    def test_expiring_trials_task_sends_warning_and_expires_elapsed(self):
        """Task warns for trials ending in 2 days and expires past trials."""
        now = timezone.now()

        # Clinic A: Trial ending in 2 days
        sub_warn = ClinicSubscription.objects.create(
            clinic=self.clinic,
            plan=self.pro_plan,
            status=SubscriptionStatus.TRIALING,
            billing_interval=BillingInterval.MONTHLY,
            trial_start=now - timedelta(days=12),
            trial_end=now + timedelta(days=2),
        )

        res = check_expiring_trials_task()
        self.assertGreaterEqual(res["warnings_sent"], 1)

        # Now set trial_end in the past
        sub_warn.trial_end = now - timedelta(hours=1)
        sub_warn.save()

        res2 = check_expiring_trials_task()
        self.assertGreaterEqual(res2["trials_expired"], 1)

        sub_warn.refresh_from_db()
        self.assertEqual(sub_warn.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(sub_warn.plan, self.free_plan)  # Reverted to free tier!

    def test_subscription_renewals_and_expiry_task(self):
        """Expires past-due subscriptions when grace period concludes."""
        now = timezone.now()
        sub = ClinicSubscription.objects.create(
            clinic=self.clinic,
            plan=self.pro_plan,
            status=SubscriptionStatus.PAST_DUE,
            billing_interval=BillingInterval.MONTHLY,
            past_due_since=now - timedelta(days=6),
            grace_period_ends_at=now - timedelta(hours=2),  # Grace period elapsed
        )

        res = check_subscription_renewals_and_expiry_task()
        self.assertGreaterEqual(res["past_due_expired"], 1)

        sub.refresh_from_db()
        self.assertEqual(sub.plan, self.free_plan)


class SubscriptionAPITests(TestCase):
    """DRF Endpoint tests for catalog, clinic subscription, checkout, invoices, and Super Admin."""

    def setUp(self):
        self.client = APIClient()

        self.owner = User.objects.create_user(
            email="api_owner@test.com",
            password="SecurePassword123!",
            role=UserRole.CLINIC_OWNER,
        )
        self.admin = User.objects.create_user(
            email="superadmin@test.com",
            password="SecurePassword123!",
            role=UserRole.SUPER_ADMIN,
        )
        self.other_user = User.objects.create_user(
            email="intruder@test.com",
            password="SecurePassword123!",
            role=UserRole.CLINIC_OWNER,
        )

        self.clinic = Clinic.objects.create(
            name="Metro Health",
            slug="metro-health",
            owner=self.owner,
            email="contact@metro.com",
            phone="9000000002",
            address_line_1="10 Metro Blvd",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            status=ClinicStatus.APPROVED,
        )

        self.pro_plan = SubscriptionPlan.objects.create(
            name="Professional Suite",
            code="professional-monthly",
            tier=SubscriptionTier.PROFESSIONAL,
            billing_interval=BillingInterval.MONTHLY,
            price=Decimal("3999.00"),
            currency="INR",
            max_doctors=10,
            max_staff=10,
            is_active=True,
            is_public=True,
        )

    def test_public_plan_catalog_endpoint(self):
        """GET /api/v1/subscriptions/plans/ returns active public plans."""
        res = self.client.get("/api/v1/subscriptions/plans/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        self.assertGreaterEqual(len(res.data["data"]), 1)

    def test_clinic_subscription_detail_permissions(self):
        """Owner can view clinic subscription; intruder is blocked."""
        self.client.force_authenticate(user=self.owner)
        res = self.client.get(f"/api/v1/subscriptions/clinics/{self.clinic.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("doctors", res.data["data"])
        self.assertIn("subscription", res.data["data"])

        # Intruder blocked
        self.client.force_authenticate(user=self.other_user)
        res_intruder = self.client.get(f"/api/v1/subscriptions/clinics/{self.clinic.id}/")
        self.assertEqual(res_intruder.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_metrics_and_override(self):
        """Super Admin can access MRR metrics and execute quota overrides."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/admin/subscriptions/metrics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("mrr", res.data["data"])
        self.assertIn("arr", res.data["data"])

        # Execute override
        override_res = self.client.post(
            f"/api/v1/admin/subscriptions/clinics/{self.clinic.id}/override/",
            data={
                "custom_doctor_limit": 25,
                "custom_staff_limit": 15,
                "reason": "Institutional trial grant",
            },
            format="json",
        )
        self.assertEqual(override_res.status_code, status.HTTP_200_OK)

        sub = ClinicSubscription.objects.get(clinic=self.clinic)
        self.assertEqual(sub.custom_doctor_limit, 25)
        self.assertEqual(sub.custom_staff_limit, 15)
