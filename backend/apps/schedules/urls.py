from django.urls import path
from .views import (
    AvailabilitySlotsView,
    BlockedSlotDetailView,
    BlockedSlotListCreateView,
    DoctorMasterScheduleView,
    DoctorUnavailabilityDetailView,
    DoctorUnavailabilityListCreateView,
    ScheduleConflictCheckView,
    ScheduleDetailView,
    ScheduleListCreateView,
)

app_name = "schedules"

urlpatterns = [
    # Recurring Schedules
    path("", ScheduleListCreateView.as_view(), name="schedule-list-create"),
    path("<uuid:pk>/", ScheduleDetailView.as_view(), name="schedule-detail"),
    path("check-conflict/", ScheduleConflictCheckView.as_view(), name="schedule-check-conflict"),
    # Doctor Leaves / Unavailability
    path("unavailability/", DoctorUnavailabilityListCreateView.as_view(), name="unavailability-list-create"),
    path("unavailability/<uuid:pk>/", DoctorUnavailabilityDetailView.as_view(), name="unavailability-detail"),
    # Blocked Slots
    path("blocked-slots/", BlockedSlotListCreateView.as_view(), name="blocked-slots-list-create"),
    path("blocked-slots/<uuid:pk>/", BlockedSlotDetailView.as_view(), name="blocked-slot-detail"),
    # Real-Time Availability Slot Engine
    path("availability/", AvailabilitySlotsView.as_view(), name="availability-slots"),
    # Doctor Multi-Clinic Master Schedule
    path("master-schedule/", DoctorMasterScheduleView.as_view(), name="doctor-master-schedule"),
]
