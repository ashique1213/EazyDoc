from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.subscriptions.models import SubscriptionPlan, SubscriptionTier, BillingInterval


class Command(BaseCommand):
    help = "Seeds initial default subscription plans for EazyDoc SaaS"

    def handle(self, *args, **options):
        plans_data = [
            {
                "name": "Free Community",
                "code": "free-monthly",
                "tier": SubscriptionTier.FREE,
                "billing_interval": BillingInterval.MONTHLY,
                "price": Decimal("0.00"),
                "currency": "INR",
                "description": "Essential practice management for solo practitioners and newly registered clinics.",
                "max_doctors": 1,
                "max_staff": 1,
                "max_appointments_per_month": 50,
                "features": [
                    "1 Doctor Affiliation",
                    "1 Clinic Staff Account",
                    "Up to 50 Appointments / month",
                    "Basic Clinic Dashboard",
                    "Standard In-App Reminders",
                ],
                "feature_flags": {
                    "advanced_analytics": False,
                    "export_reports": False,
                    "export_pdf": False,
                    "priority_support": False,
                },
                "trial_days": 0,
                "sort_order": 1,
            },
            {
                "name": "Starter Plan",
                "code": "starter-monthly",
                "tier": SubscriptionTier.STARTER,
                "billing_interval": BillingInterval.MONTHLY,
                "price": Decimal("1499.00"),
                "currency": "INR",
                "description": "Perfect for growing clinics expanding their doctor team and front desk operations.",
                "max_doctors": 3,
                "max_staff": 3,
                "max_appointments_per_month": 300,
                "features": [
                    "Up to 3 Doctors",
                    "Up to 3 Staff Accounts",
                    "Up to 300 Appointments / month",
                    "Revenue & Appointment Analytics",
                    "CSV Financial & Patient Data Exports",
                    "Email & In-App Notifications",
                    "Standard Support (24h response)",
                ],
                "feature_flags": {
                    "advanced_analytics": True,
                    "export_reports": True,
                    "export_pdf": False,
                    "priority_support": False,
                },
                "trial_days": 14,
                "sort_order": 2,
            },
            {
                "name": "Starter Plan (Annual)",
                "code": "starter-yearly",
                "tier": SubscriptionTier.STARTER,
                "billing_interval": BillingInterval.YEARLY,
                "price": Decimal("14990.00"),
                "currency": "INR",
                "description": "Starter Plan billed annually — get 2 months free.",
                "max_doctors": 3,
                "max_staff": 3,
                "max_appointments_per_month": 300,
                "features": [
                    "Up to 3 Doctors",
                    "Up to 3 Staff Accounts",
                    "Up to 300 Appointments / month",
                    "Revenue & Appointment Analytics",
                    "CSV Financial & Patient Data Exports",
                    "Email & In-App Notifications",
                    "Standard Support (24h response)",
                    "2 Months Free with Annual Billing",
                ],
                "feature_flags": {
                    "advanced_analytics": True,
                    "export_reports": True,
                    "export_pdf": False,
                    "priority_support": False,
                },
                "trial_days": 14,
                "sort_order": 3,
            },
            {
                "name": "Professional Suite",
                "code": "professional-monthly",
                "tier": SubscriptionTier.PROFESSIONAL,
                "billing_interval": BillingInterval.MONTHLY,
                "price": Decimal("3999.00"),
                "currency": "INR",
                "description": "Advanced management for established polyclinics and diagnostic centers.",
                "max_doctors": 10,
                "max_staff": 10,
                "max_appointments_per_month": 1500,
                "features": [
                    "Up to 10 Doctors",
                    "Up to 10 Staff Accounts",
                    "Up to 1,500 Appointments / month",
                    "Full Financial Ledger & Reconciliation",
                    "Advanced Doctor & Time-Slot Heatmaps",
                    "Official PDF & CSV Report Exports",
                    "Automated Multi-Channel Patient Reminders",
                    "Priority Support SLA (4h response)",
                ],
                "feature_flags": {
                    "advanced_analytics": True,
                    "export_reports": True,
                    "export_pdf": True,
                    "priority_support": True,
                },
                "trial_days": 14,
                "sort_order": 4,
            },
            {
                "name": "Professional Suite (Annual)",
                "code": "professional-yearly",
                "tier": SubscriptionTier.PROFESSIONAL,
                "billing_interval": BillingInterval.YEARLY,
                "price": Decimal("39990.00"),
                "currency": "INR",
                "description": "Professional Suite billed annually — get 2 months free.",
                "max_doctors": 10,
                "max_staff": 10,
                "max_appointments_per_month": 1500,
                "features": [
                    "Up to 10 Doctors",
                    "Up to 10 Staff Accounts",
                    "Up to 1,500 Appointments / month",
                    "Full Financial Ledger & Reconciliation",
                    "Advanced Doctor & Time-Slot Heatmaps",
                    "Official PDF & CSV Report Exports",
                    "Automated Multi-Channel Patient Reminders",
                    "Priority Support SLA (4h response)",
                    "2 Months Free with Annual Billing",
                ],
                "feature_flags": {
                    "advanced_analytics": True,
                    "export_reports": True,
                    "export_pdf": True,
                    "priority_support": True,
                },
                "trial_days": 14,
                "sort_order": 5,
            },
            {
                "name": "Enterprise Hospital",
                "code": "enterprise-monthly",
                "tier": SubscriptionTier.ENTERPRISE,
                "billing_interval": BillingInterval.MONTHLY,
                "price": Decimal("9999.00"),
                "currency": "INR",
                "description": "High-throughput infrastructure for hospitals and multi-branch networks.",
                "max_doctors": None,
                "max_staff": None,
                "max_appointments_per_month": None,
                "features": [
                    "Unlimited Doctors",
                    "Unlimited Staff Accounts",
                    "Unlimited Appointments",
                    "Custom BI & Advanced Reporting",
                    "Custom Sub-domain & White-labeling",
                    "Dedicated Account Manager",
                    "99.99% Uptime SLA",
                ],
                "feature_flags": {
                    "advanced_analytics": True,
                    "export_reports": True,
                    "export_pdf": True,
                    "priority_support": True,
                    "dedicated_account_manager": True,
                    "unlimited_capacity": True,
                },
                "trial_days": 14,
                "sort_order": 6,
            },
            {
                "name": "Enterprise Hospital (Annual)",
                "code": "enterprise-yearly",
                "tier": SubscriptionTier.ENTERPRISE,
                "billing_interval": BillingInterval.YEARLY,
                "price": Decimal("99990.00"),
                "currency": "INR",
                "description": "Enterprise Hospital billed annually with 2 months free.",
                "max_doctors": None,
                "max_staff": None,
                "max_appointments_per_month": None,
                "features": [
                    "Unlimited Doctors",
                    "Unlimited Staff Accounts",
                    "Unlimited Appointments",
                    "Custom BI & Advanced Reporting",
                    "Custom Sub-domain & White-labeling",
                    "Dedicated Account Manager",
                    "99.99% Uptime SLA",
                    "2 Months Free with Annual Billing",
                ],
                "feature_flags": {
                    "advanced_analytics": True,
                    "export_reports": True,
                    "export_pdf": True,
                    "priority_support": True,
                    "dedicated_account_manager": True,
                    "unlimited_capacity": True,
                },
                "trial_days": 14,
                "sort_order": 7,
            },
        ]

        created_count = 0
        updated_count = 0
        for plan_info in plans_data:
            code = plan_info.pop("code")
            plan, created = SubscriptionPlan.objects.update_or_create(
                code=code,
                defaults=plan_info,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded subscription plans: {created_count} created, {updated_count} updated."
            )
        )
