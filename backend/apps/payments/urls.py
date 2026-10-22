from django.urls import path
from .views import (
    AdminClinicCommissionUpdateView,
    AppointmentPaymentStatusView,
    ClinicFinancialRecordsListView,
    CreatePaymentOrderView,
    RazorpayWebhookView,
    VerifyPaymentView,
)

app_name = "payments"

urlpatterns = [
    path("create-order/", CreatePaymentOrderView.as_view(), name="create-order"),
    path("verify/", VerifyPaymentView.as_view(), name="verify"),
    path("appointment/<uuid:appointment_id>/status/", AppointmentPaymentStatusView.as_view(), name="appointment-status"),
    path("webhook/razorpay/", RazorpayWebhookView.as_view(), name="webhook-razorpay"),
    path("clinics/<uuid:clinic_id>/financial-records/", ClinicFinancialRecordsListView.as_view(), name="clinic-financial-records"),
    path("admin/clinics/<uuid:clinic_id>/commission-rate/", AdminClinicCommissionUpdateView.as_view(), name="admin-clinic-commission"),
]
