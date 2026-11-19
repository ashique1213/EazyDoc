export type SubscriptionTier = "FREE" | "STARTER" | "PROFESSIONAL" | "ENTERPRISE";
export type BillingInterval = "MONTHLY" | "YEARLY";
export type SubscriptionStatus =
  | "TRIALING"
  | "ACTIVE"
  | "PAST_DUE"
  | "CANCELLED"
  | "EXPIRED"
  | "SUSPENDED"
  | "INCOMPLETE";

export interface SubscriptionPlan {
  id: string;
  name: string;
  code: string;
  tier: SubscriptionTier;
  billing_interval: BillingInterval;
  price: number | string;
  currency: string;
  description: string;
  max_doctors: number | null;
  max_staff: number | null;
  max_appointments_per_month: number | null;
  features: string[];
  feature_flags: Record<string, boolean>;
  trial_days: number;
  is_active: boolean;
  is_public: boolean;
  sort_order: number;
  is_free: boolean;
}

export interface ClinicSubscriptionInfo {
  id: string;
  status: SubscriptionStatus;
  tier: SubscriptionTier;
  plan_name: string;
  plan_code: string;
  price: number;
  billing_interval: BillingInterval;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_start: string | null;
  trial_end: string | null;
  is_in_trial: boolean;
  days_remaining: number;
  cancel_at_period_end: boolean;
  has_used_trial: boolean;
}

export interface UsageQuota {
  current: number;
  limit: number | null;
  is_unlimited: boolean;
  percentage: number;
  can_add?: boolean;
  can_book?: boolean;
  restriction_message: string;
}

export interface ClinicEntitlementsSummary {
  clinic_id: string;
  clinic_name: string;
  subscription: ClinicSubscriptionInfo;
  doctors: UsageQuota;
  staff: UsageQuota;
  appointments: UsageQuota;
  feature_flags: Record<string, boolean>;
  marketing_features: string[];
}

export interface InvoiceLineItem {
  item_id: number;
  description: string;
  quantity: number;
  unit_price: string;
  tax_rate_percent: string;
  tax_amount: string;
  total_amount: string;
}

export interface SubscriptionInvoice {
  id: string;
  invoice_number: string;
  clinic_id: string;
  clinic_name: string;
  plan_name: string;
  subtotal_amount: string | number;
  tax_rate: string | number;
  tax_amount: string | number;
  total_amount: string | number;
  currency: string;
  status: "DRAFT" | "PAID" | "UNPAID" | "VOID";
  billing_period_start: string;
  billing_period_end: string;
  line_items: InvoiceLineItem[];
  billing_details: Record<string, string>;
  paid_at: string | null;
  created_at: string;
}

export interface SubscriptionEvent {
  id: string;
  clinic_id: string;
  event_type: string;
  old_status: string;
  new_status: string;
  old_plan_name: string;
  new_plan_name: string;
  reason: string;
  metadata: Record<string, unknown>;
  triggered_by_name: string;
  created_at: string;
}

export interface CheckoutOrderResponse {
  free_plan_activated: boolean;
  subscription_id?: string;
  payment_id?: string;
  order_id?: string;
  amount?: number;
  amount_display?: string;
  currency?: string;
  key_id?: string;
  clinic_id?: string;
  clinic_name?: string;
  plan_id?: string;
  plan_name?: string;
  billing_interval?: BillingInterval;
  status?: string;
}

export interface VerifyPaymentPayload {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface AdminSubscriptionMetrics {
  mrr: number;
  arr: number;
  total_saas_revenue: number;
  active_paid_subscriptions: number;
  trialing_subscriptions: number;
  past_due_subscriptions: number;
  cancelled_subscriptions: number;
  expired_subscriptions: number;
  total_clinics_enrolled: number;
  churn_rate_percentage: number;
  plan_distribution: {
    plan_id: string;
    plan_name: string;
    tier: SubscriptionTier;
    billing_interval: BillingInterval;
    price: number;
    active_clinics: number;
  }[];
}

export interface AdminOverridePayload {
  status?: SubscriptionStatus;
  plan_id?: string;
  custom_doctor_limit?: number | null;
  custom_staff_limit?: number | null;
  extend_days?: number;
  reason: string;
}
