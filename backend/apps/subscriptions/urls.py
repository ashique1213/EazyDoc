from django.urls import path
from apps.subscriptions.views import (
    ClinicSubscriptionAuditLogsView,
    ClinicSubscriptionCancelView,
    ClinicSubscriptionCheckoutView,
    ClinicSubscriptionDetailView,
    ClinicSubscriptionInvoiceDetailView,
    ClinicSubscriptionInvoiceDownloadView,
    ClinicSubscriptionInvoicesListView,
    ClinicSubscriptionVerifyPaymentView,
    SubscriptionPlansListView,
)
from apps.subscriptions.webhook_views import RazorpaySubscriptionWebhookView

app_name = "subscriptions"

urlpatterns = [
    # Public plan catalog
    path("plans/", SubscriptionPlansListView.as_view(), name="plan-list"),
    # Clinic-scoped subscription management
    path("clinics/<uuid:clinic_id>/", ClinicSubscriptionDetailView.as_view(), name="clinic-subscription-detail"),
    path("clinics/<uuid:clinic_id>/checkout/", ClinicSubscriptionCheckoutView.as_view(), name="clinic-subscription-checkout"),
    path("clinics/<uuid:clinic_id>/verify/", ClinicSubscriptionVerifyPaymentView.as_view(), name="clinic-subscription-verify"),
    path("clinics/<uuid:clinic_id>/cancel/", ClinicSubscriptionCancelView.as_view(), name="clinic-subscription-cancel"),
    path("clinics/<uuid:clinic_id>/invoices/", ClinicSubscriptionInvoicesListView.as_view(), name="clinic-subscription-invoices"),
    path("clinics/<uuid:clinic_id>/invoices/<uuid:invoice_id>/", ClinicSubscriptionInvoiceDetailView.as_view(), name="clinic-subscription-invoice-detail"),
    path("clinics/<uuid:clinic_id>/invoices/<uuid:invoice_id>/html/", ClinicSubscriptionInvoiceDownloadView.as_view(), name="clinic-subscription-invoice-html"),
    path("clinics/<uuid:clinic_id>/events/", ClinicSubscriptionAuditLogsView.as_view(), name="clinic-subscription-events"),
    # Webhooks
    path("webhooks/razorpay/", RazorpaySubscriptionWebhookView.as_view(), name="razorpay-subscription-webhook"),
]
