export type DateRangePeriod =
  | "today"
  | "yesterday"
  | "last_7_days"
  | "last_30_days"
  | "last_90_days"
  | "this_month"
  | "previous_month"
  | "this_year"
  | "custom";

export interface AnalyticsFilterParams {
  period?: DateRangePeriod;
  date_from?: string;
  date_to?: string;
  clinic_id?: string;
  doctor_id?: string;
  status?: string;
  refresh?: boolean;
}

export interface PeriodInfo {
  name: string;
  start_date: string;
  end_date: string;
  days_count: number;
  timezone?: string;
}

export interface AdminOverviewData {
  period: PeriodInfo;
  users: {
    total_users: number;
    total_patients: number;
  };
  clinics: {
    total: number;
    approved: number;
    active: number;
    pending: number;
    rejected: number;
    suspended: number;
  };
  doctors: {
    total: number;
    verified: number;
    pending: number;
    rejected: number;
    suspended: number;
  };
  appointments: {
    total: number;
    completed: number;
    confirmed: number;
    cancelled: number;
    no_show: number;
    pending: number;
    reschedule_required: number;
    today: number;
    upcoming: number;
    completion_rate: number;
    cancellation_rate: number;
  };
  finance: {
    gross_collected: string;
    platform_commission: string;
    clinic_payable: string;
    failed_volume: string;
    refund_volume: string;
    successful_payments_count: number;
    failed_payments_count: number;
    pending_payments_count: number;
    refunded_payments_count: number;
    conversion_rate: number;
    accounting_invariant_valid: boolean;
    actual_payouts_disbursed: string;
    payout_notice: string;
  };
}

export interface DailyRevenuePoint {
  date: string;
  gross_revenue: string;
  platform_commission: string;
  clinic_share: string;
  successful_payments?: number;
  failed_payments?: number;
  paid_appointments?: number;
}

export interface MonthlyRevenuePoint {
  month: string;
  gross_revenue: string;
  platform_commission: string;
  clinic_share: string;
  successful_payments: number;
}

export interface PaymentStatusPoint {
  status: string;
  count: number;
  percentage: number;
}

export interface ClinicRevenueBreakdownItem {
  clinic_id: string;
  clinic_name: string;
  gross_revenue: string;
  platform_commission: string;
  clinic_share: string;
  settled_appointments: number;
}

export interface RevenueAnalyticsData {
  totals: {
    gross_revenue: string;
    platform_commission: string;
    clinic_share: string;
    failed_volume: string;
    refund_volume: string;
    average_commission_rate: number;
    successful_payments_count: number;
    failed_payments_count: number;
    pending_payments_count: number;
    refunded_payments_count: number;
  };
  daily_trend: DailyRevenuePoint[];
  monthly_trend: MonthlyRevenuePoint[];
  payment_status_distribution: PaymentStatusPoint[];
  clinic_revenue_breakdown: ClinicRevenueBreakdownItem[];
}

export interface DailyAppointmentPoint {
  date: string;
  total: number;
  completed: number;
  confirmed: number;
  cancelled: number;
  no_show: number;
}

export interface PeakDayPoint {
  day: string;
  day_index: number;
  count: number;
  percentage: number;
}

export interface PeakHourPoint {
  hour: number;
  label: string;
  count: number;
  percentage: number;
}

export interface AppointmentAnalyticsData {
  totals: {
    total_bookings: number;
    completed: number;
    confirmed: number;
    cancelled: number;
    no_show: number;
    pending: number;
    rescheduled: number;
    completion_rate: number;
    cancellation_rate: number;
    reschedule_rate: number;
    no_show_rate: number;
  };
  status_distribution: Array<{
    status: string;
    count: number;
    percentage: number;
  }>;
  daily_trend: DailyAppointmentPoint[];
  peak_days: PeakDayPoint[];
  peak_hours: PeakHourPoint[];
}

export interface ClinicPerformanceItem {
  clinic_id: string;
  name: string;
  slug: string;
  status: string;
  is_active: boolean;
  city: string;
  state: string;
  total_doctors: number;
  active_doctors: number;
  total_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
  completion_rate: number;
  gross_volume: string;
  platform_commission: string;
  clinic_share: string;
  avg_consultation_value: string;
  commission_rate_override: string | null;
}

export interface DoctorAffiliation {
  clinic_id: string;
  clinic_name: string;
  consultation_fee: string;
  is_active: boolean;
}

export interface DoctorPerformanceItem {
  doctor_id: string;
  name: string;
  email: string;
  specialization: string;
  verification_status: string;
  affiliations: DoctorAffiliation[];
  total_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
  completion_rate: number;
  avg_appointments_per_day: number;
  gross_revenue: string;
  platform_commission: string;
  clinic_share: string;
}

export interface ReconciliationDiscrepancy {
  type: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  payment_id: string | null;
  appointment_id: string | null;
  clinic_name: string;
  amount: string;
  description: string;
}

export interface FinancialReconciliationData {
  period: {
    start_date: string;
    end_date: string;
  };
  health_status: "HEALTHY" | "DISCREPANCIES_DETECTED";
  total_reconciled_transactions: number;
  discrepancy_count: number;
  total_discrepancy_value: string;
  discrepancies: ReconciliationDiscrepancy[];
}

export interface ClinicOverviewData {
  clinic: {
    id: string;
    name: string;
    timezone: string;
    commission_rate: string;
  };
  period: PeriodInfo;
  appointments: {
    total: number;
    completed: number;
    confirmed: number;
    cancelled: number;
    no_show: number;
    pending: number;
    reschedule_required: number;
    today: number;
    upcoming: number;
    completion_rate: number;
    cancellation_rate: number;
  };
  finance: {
    gross_revenue: string;
    platform_commission_deducted: string;
    clinic_payable_share: string;
    refund_volume: string;
    successful_payments_count: number;
    failed_payments_count: number;
    payout_status: string;
    payout_notice: string;
  };
  doctors: {
    total: number;
    active: number;
  };
}

export interface ClinicRevenueData {
  totals: {
    gross_revenue: string;
    platform_commission_deducted: string;
    clinic_share: string;
    paid_count: number;
    failed_count: number;
    refunded_count: number;
  };
  daily_trend: Array<{
    date: string;
    gross_revenue: string;
    platform_commission: string;
    clinic_share: string;
    paid_appointments: number;
  }>;
  doctor_breakdown: Array<{
    doctor_id: string;
    doctor_name: string;
    specialization: string;
    gross_revenue: string;
    platform_commission: string;
    clinic_share: string;
    appointments_count: number;
  }>;
}

export interface ClinicAppointmentData {
  totals: {
    total_bookings: number;
    completed: number;
    confirmed: number;
    cancelled: number;
    no_show: number;
    pending: number;
    completion_rate: number;
    cancellation_rate: number;
  };
  daily_trend: Array<{
    date: string;
    total: number;
    completed: number;
    confirmed: number;
    cancelled: number;
  }>;
  peak_hours: PeakHourPoint[];
  cancellation_summary: Array<{
    reason: string;
    count: number;
    percentage: number;
  }>;
}

export interface ClinicDoctorPerformanceItem {
  doctor_id: string;
  name: string;
  email: string;
  specialization: string;
  consultation_fee: string;
  is_active_at_clinic: boolean;
  total_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
  completion_rate: number;
  gross_revenue: string;
  platform_commission: string;
  clinic_share: string;
}
