export interface DashboardSummaryData {
  clinics: {
    total: number;
    approved: number;
    pending: number;
    rejected: number;
    suspended: number;
  };
  doctors: {
    total: number;
    verified: number;
    pending: number;
    suspended: number;
    rejected: number;
  };
  users: {
    total_patients: number;
    total_users: number;
  };
  appointments: {
    total: number;
    today: number;
    upcoming: number;
    completed: number;
    cancelled: number;
    confirmed: number;
    reschedule_required: number;
  };
  finance: {
    successful_payments: number;
    failed_payments: number;
    gross_volume: string;
    recorded_commission: string;
    calculated_clinic_share: string;
    default_commission_rate: string;
    actual_payouts: string;
    payout_disclaimer: string;
  };
}

export interface AppointmentTrendPoint {
  date: string;
  total: number;
  confirmed: number;
  completed: number;
  cancelled: number;
}

export interface FinancialSummaryData {
  totals: {
    gross_successful_payments: string;
    recorded_commission: string;
    calculated_clinic_share: string;
    failed_payments_volume: string;
    successful_payments_count: number;
    failed_payments_count: number;
    actual_refunds: string;
    actual_payouts: string;
  };
  daily_trend: Array<{
    date: string;
    gross_volume: string;
    commission_recorded: string;
    clinic_share: string;
    successful_count: number;
    failed_count: number;
  }>;
}

export interface AdminUser {
  id: string;
  email: string;
  phone: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  role: "SUPER_ADMIN" | "CLINIC_OWNER" | "STAFF" | "DOCTOR" | "PATIENT";
  status: "ACTIVE" | "INACTIVE" | "SUSPENDED";
  is_active: boolean;
  is_staff: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
  doctor_profile_id: string | null;
  owned_clinics_count: number;
}

export interface AdminAppointment {
  id: string;
  booking_reference: string;
  patient: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    phone: string | null;
  } | null;
  doctor: {
    id: string;
    full_name: string;
    specialization: string;
  } | null;
  clinic: {
    id: string;
    name: string;
    slug: string;
    city: string;
  } | null;
  start_at: string;
  end_at: string;
  status: string;
  payment_status: string;
  consultation_fee: string;
  currency: string;
  patient_note: string;
  cancellation_reason: string;
  cancelled_at: string | null;
  reschedule_required: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminAppointmentHistory {
  id: string;
  event_type: string;
  previous_status: string;
  new_status: string;
  previous_start_at: string | null;
  previous_end_at: string | null;
  new_start_at: string | null;
  new_end_at: string | null;
  actor_email: string;
  actor_role: string;
  reason: string;
  is_exception: boolean;
  created_at: string;
}

export interface AdminPayment {
  id: string;
  gateway_order_id: string;
  gateway_payment_id: string | null;
  gateway_name: string;
  amount: string;
  currency: string;
  status: string;
  failure_code: string;
  failure_description: string;
  paid_at: string | null;
  created_at: string;
  clinic: {
    id: string;
    name: string;
    slug: string;
    city: string;
  } | null;
  patient_email: string;
  patient_name: string;
  booking_reference: string;
  appointment_status: string;
  commission_record: {
    id: string;
    gross_amount: string;
    commission_rate: string;
    commission_amount: string;
    clinic_share: string;
    currency: string;
    status: string;
    settled_at: string | null;
    created_at: string;
  } | null;
}

export interface AdminCommissionRecord {
  id: string;
  payment_id: string;
  appointment_id: string;
  booking_reference: string;
  clinic_id: string;
  clinic_name: string;
  clinic_slug: string;
  gateway_order_id: string;
  gateway_payment_id: string | null;
  gross_amount: string;
  commission_rate: string;
  commission_amount: string;
  clinic_share: string;
  currency: string;
  status: string;
  settled_at: string | null;
  created_at: string;
}

export interface AdminCommissionSettingsData {
  default_rate: string;
  clinic_overrides: Array<{
    clinic_id: string;
    clinic_name: string;
    slug: string;
    city: string;
    status: string;
    commission_rate: string;
    effective_rate: string;
  }>;
  clinics: Array<{
    clinic_id: string;
    clinic_name: string;
    slug: string;
    city: string;
    has_override: boolean;
    override_rate: string | null;
    effective_rate: string;
  }>;
  history: Array<{
    id: string;
    action: string;
    actor_email: string;
    details: Record<string, unknown>;
    created_at: string;
  }>;
}

export interface AdminAuditLog {
  id: number;
  actor_id: string | null;
  actor_email: string;
  actor_name: string;
  actor_role: string;
  clinic_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string | null;
  user_agent: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
