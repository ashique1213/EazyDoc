export type ClinicStaffPermission =
  | "VIEW_APPOINTMENTS"
  | "MANAGE_APPOINTMENTS"
  | "VIEW_DOCTORS"
  | "MANAGE_DOCTOR_ASSOCIATIONS"
  | "MANAGE_SCHEDULES"
  | "VIEW_FINANCIAL_SUMMARY"
  | "MANAGE_CLINIC_PROFILE"
  | "MANAGE_STAFF";

export interface ClinicStaffMember {
  id: string;
  clinic_id: string;
  clinic_name: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    full_name: string;
    role: string;
    status: string;
    is_active: boolean;
  };
  role_title: string;
  permissions: ClinicStaffPermission[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicStaffCreatePayload {
  email: string;
  first_name: string;
  last_name: string;
  role_title?: string;
  permissions: ClinicStaffPermission[];
  password?: string;
}

export interface ClinicStaffUpdatePayload {
  role_title?: string;
  permissions?: ClinicStaffPermission[];
  is_active?: boolean;
}

export interface ClinicClosure {
  id: string;
  clinic_id: string;
  start_date: string;
  end_date: string;
  reason: string;
  notes: string;
  is_active: boolean;
  created_by: string | null;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface ClinicClosureCreatePayload {
  start_date: string;
  end_date: string;
  reason: string;
  notes?: string;
  confirmed?: boolean;
}

export interface AffectedAppointmentPreview {
  id: string;
  booking_reference: string;
  doctor_name: string;
  patient_name: string;
  start_at: string;
  status: string;
}

export interface ClinicClosurePreviewResponse {
  start_date: string;
  end_date: string;
  affected_count: number;
  requires_confirmation: boolean;
  affected_appointments: AffectedAppointmentPreview[];
}

export interface ClinicDashboardSummary {
  clinic: {
    id: string;
    name: string;
    slug: string;
    status: string;
    timezone: string;
  };
  period_info: {
    period: string;
    from_date: string;
    to_date: string;
    timezone: string;
  };
  doctor_metrics: {
    total_active_doctors: number;
    pending_doctor_invitations: number;
  };
  appointment_metrics: {
    today_appointments: number;
    upcoming_appointments: number;
    completed_appointments: number;
    cancelled_appointments: number;
    appointments_requiring_attention: number;
    total_appointments_in_period: number;
    cancellation_rate_percentage: number;
  };
  financial_metrics: {
    currency: string;
    gross_patient_payments: string;
    recorded_platform_commission: string;
    calculated_clinic_share: string;
    actual_payouts: string;
    payout_status_notice: string;
  };
}

export interface ClinicTrendPoint {
  date: string;
  total: number;
  confirmed: number;
  completed: number;
  cancelled: number;
  no_show: number;
}

export interface ClinicTrendsResponse {
  timezone: string;
  trends: ClinicTrendPoint[];
}

export interface CalendarShift {
  id: string;
  doctor_id: string;
  doctor_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
}

export interface CalendarAppointment {
  id: string;
  booking_reference: string;
  doctor_id: string;
  doctor_name: string;
  patient_name: string;
  start_at: string;
  end_at: string;
  status: string;
  payment_status: string;
  reschedule_required: boolean;
}

export interface CalendarUnavailability {
  id: string;
  doctor_id: string;
  doctor_name: string;
  start_datetime: string;
  end_datetime: string;
  reason: string;
  notes: string;
}

export interface CalendarBlockedSlot {
  id: string;
  doctor_id: string;
  doctor_name: string;
  date: string;
  start_time: string;
  end_time: string;
  reason: string;
}

export interface CalendarClosure {
  id: string;
  start_date: string;
  end_date: string;
  reason: string;
  notes: string;
}

export interface ClinicCalendarData {
  clinic: {
    id: string;
    name: string;
    timezone: string;
  };
  range: {
    start_date: string;
    end_date: string;
  };
  shifts: CalendarShift[];
  appointments: CalendarAppointment[];
  unavailabilities: CalendarUnavailability[];
  blocked_slots: CalendarBlockedSlot[];
  closures: CalendarClosure[];
}

export interface ClinicFinanceSummary {
  clinic: {
    id: string;
    name: string;
    timezone: string;
  };
  period_info: {
    period: string;
    from_date: string;
    to_date: string;
  };
  period_metrics: {
    gross_payments: string;
    successful_payments_count: number;
    recorded_platform_commission: string;
    calculated_clinic_share: string;
    failed_payments_count: number;
    refunded_total: string;
    refunded_count: number;
    actual_payouts: string;
    payout_notice: string;
  };
  all_time_metrics: {
    all_time_gross: string;
    all_time_commission: string;
    all_time_clinic_share: string;
  };
}

export interface ClinicPaymentTransaction {
  id: string;
  amount: string;
  currency: string;
  status: string;
  gateway_name: string;
  gateway_order_id: string;
  gateway_payment_id: string;
  created_at: string;
  paid_at: string | null;
  booking_reference: string;
  doctor_name: string;
  patient: {
    id: string;
    name: string;
    email: string;
  };
  commission_snapshot: {
    commission_rate: string | null;
    commission_amount: string | null;
    clinic_share: string | null;
    status: string | null;
  } | null;
}

export interface PaginatedPaymentsResponse {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
  results: ClinicPaymentTransaction[];
}

export interface AppointmentHistoryItem {
  id: string;
  event_type: string;
  created_at: string;
  actor_email?: string;
  actor?: { first_name?: string; last_name?: string; email?: string };
  actor_role?: string;
  reason?: string;
}
