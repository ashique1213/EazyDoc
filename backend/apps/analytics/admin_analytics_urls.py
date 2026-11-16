from django.urls import path
from .views import (
    AdminAnalyticsAppointmentsView,
    AdminAnalyticsClinicsView,
    AdminAnalyticsDoctorsView,
    AdminAnalyticsExportView,
    AdminAnalyticsOverviewView,
    AdminAnalyticsReconciliationView,
    AdminAnalyticsRevenueView,
)

app_name = "admin-analytics"

urlpatterns = [
    path("overview/", AdminAnalyticsOverviewView.as_view(), name="overview"),
    path("revenue/", AdminAnalyticsRevenueView.as_view(), name="revenue"),
    path("appointments/", AdminAnalyticsAppointmentsView.as_view(), name="appointments"),
    path("clinics/", AdminAnalyticsClinicsView.as_view(), name="clinics"),
    path("doctors/", AdminAnalyticsDoctorsView.as_view(), name="doctors"),
    path("reconciliation/", AdminAnalyticsReconciliationView.as_view(), name="reconciliation"),
    path("reports/export/", AdminAnalyticsExportView.as_view(), name="export"),
]
