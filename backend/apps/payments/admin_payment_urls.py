from django.urls import path
from .admin_views import AdminPaymentListView

app_name = "admin-payments"

urlpatterns = [
    path("", AdminPaymentListView.as_view(), name="payment-list"),
]
