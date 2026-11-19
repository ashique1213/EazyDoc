"""
Subscriptions application configuration.
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.subscriptions"
    verbose_name = _("SaaS Subscriptions & Billing")

    def ready(self):
        # Import signal handlers or tasks if any
        pass
