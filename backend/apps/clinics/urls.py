from django.urls import path
from .views import (
    ClinicDetailView,
    ClinicDoctorInvitationView,
    ClinicDoctorListView,
    ClinicDoctorRemoveView,
    ClinicDoctorSettingsUpdateView,
    ClinicListCreateView,
    ClinicSubmitView,
    MyClinicsListView,
)
from .dashboard_views import (
    ClinicDashboardFinancialSummaryView,
    ClinicDashboardSummaryView,
    ClinicDashboardTrendsView,
)
from .management_views import (
    ClinicCalendarView,
    ClinicClosureDetailView,
    ClinicClosureListCreateView,
    ClinicClosurePreviewView,
    ClinicManagementProfileView,
)
from .staff_views import (
    ClinicStaffDetailView,
    ClinicStaffListCreateView,
)
from .finance_views import (
    ClinicFinancePaymentsListView,
    ClinicFinanceSummaryView,
)
from apps.appointments.views import (
    ClinicAppointmentCancelView,
    ClinicAppointmentCompleteView,
    ClinicAppointmentConfirmView,
    ClinicAppointmentDetailView,
    ClinicAppointmentNoShowView,
    ClinicAppointmentReportUnavailabilityView,
    ClinicAppointmentRescheduleView,
    ClinicAppointmentsListView,
)

app_name = "clinics"

urlpatterns = [
    path("", ClinicListCreateView.as_view(), name="clinic-list-create"),
    path("my-clinics/", MyClinicsListView.as_view(), name="my-clinics"),
    path("<uuid:pk>/", ClinicDetailView.as_view(), name="clinic-detail"),
    path("<uuid:pk>/submit/", ClinicSubmitView.as_view(), name="clinic-submit"),

    # Clinic Operations Management
    path("<uuid:clinic_id>/management/", ClinicManagementProfileView.as_view(), name="clinic-management"),
    path("<uuid:clinic_id>/dashboard/summary/", ClinicDashboardSummaryView.as_view(), name="clinic-dashboard-summary"),
    path("<uuid:clinic_id>/dashboard/appointment-trends/", ClinicDashboardTrendsView.as_view(), name="clinic-dashboard-trends"),
    path("<uuid:clinic_id>/dashboard/financial-summary/", ClinicDashboardFinancialSummaryView.as_view(), name="clinic-dashboard-financial-summary"),

    # Doctor Associations
    path("<uuid:clinic_id>/doctors/", ClinicDoctorListView.as_view(), name="clinic-doctor-list"),
    path("<uuid:clinic_id>/doctor-invitations/", ClinicDoctorInvitationView.as_view(), name="clinic-doctor-invitations"),
    path("<uuid:clinic_id>/doctors/<uuid:association_id>/settings/", ClinicDoctorSettingsUpdateView.as_view(), name="clinic-doctor-settings"),
    path("<uuid:clinic_id>/doctors/<uuid:association_id>/remove/", ClinicDoctorRemoveView.as_view(), name="clinic-doctor-remove"),

    # Staff Management
    path("<uuid:clinic_id>/staff/", ClinicStaffListCreateView.as_view(), name="clinic-staff-list-create"),
    path("<uuid:clinic_id>/staff/<uuid:staff_id>/", ClinicStaffDetailView.as_view(), name="clinic-staff-detail"),

    # Financial Operations
    path("<uuid:clinic_id>/finance/summary/", ClinicFinanceSummaryView.as_view(), name="clinic-finance-summary"),
    path("<uuid:clinic_id>/finance/payments/", ClinicFinancePaymentsListView.as_view(), name="clinic-finance-payments"),

    # Closures & Calendar
    path("<uuid:clinic_id>/closures/", ClinicClosureListCreateView.as_view(), name="clinic-closures-list-create"),
    path("<uuid:clinic_id>/closures/preview/", ClinicClosurePreviewView.as_view(), name="clinic-closures-preview"),
    path("<uuid:clinic_id>/closures/<uuid:closure_id>/", ClinicClosureDetailView.as_view(), name="clinic-closure-detail"),
    path("<uuid:clinic_id>/calendar/", ClinicCalendarView.as_view(), name="clinic-calendar"),

    # Clinic Appointments
    path("<uuid:clinic_id>/appointments/", ClinicAppointmentsListView.as_view(), name="clinic-appointments"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/", ClinicAppointmentDetailView.as_view(), name="clinic-appointment-detail"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/confirm/", ClinicAppointmentConfirmView.as_view(), name="clinic-appointment-confirm"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/complete/", ClinicAppointmentCompleteView.as_view(), name="clinic-appointment-complete"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/no-show/", ClinicAppointmentNoShowView.as_view(), name="clinic-appointment-no-show"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/cancel/", ClinicAppointmentCancelView.as_view(), name="clinic-appointment-cancel"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/reschedule/", ClinicAppointmentRescheduleView.as_view(), name="clinic-appointment-reschedule"),
    path("<uuid:clinic_id>/appointments/<uuid:appointment_id>/report-unavailability/", ClinicAppointmentReportUnavailabilityView.as_view(), name="clinic-appointment-report-unavailability"),
]


