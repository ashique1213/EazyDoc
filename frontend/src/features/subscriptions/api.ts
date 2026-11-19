import { apiClient } from "@/services/api";
import type {
  AdminOverridePayload,
  AdminSubscriptionMetrics,
  CheckoutOrderResponse,
  ClinicEntitlementsSummary,
  SubscriptionEvent,
  SubscriptionInvoice,
  SubscriptionPlan,
  VerifyPaymentPayload,
} from "./types";

export const subscriptionsApi = {
  // Public / Clinic Catalog
  getPlans: async (): Promise<SubscriptionPlan[]> => {
    const res = await apiClient.get<{ success: boolean; data: SubscriptionPlan[] }>(
      "/subscriptions/plans/"
    );
    return res.data.data;
  },

  // Clinic Subscriptions
  getClinicSubscription: async (clinicId: string): Promise<ClinicEntitlementsSummary> => {
    const res = await apiClient.get<{ success: boolean; data: ClinicEntitlementsSummary }>(
      `/subscriptions/clinics/${clinicId}/`
    );
    return res.data.data;
  },

  createCheckoutOrder: async (
    clinicId: string,
    payload: { plan_id: string; billing_interval: string; idempotency_key?: string }
  ): Promise<CheckoutOrderResponse> => {
    const res = await apiClient.post<{ success: boolean; message: string; data: CheckoutOrderResponse }>(
      `/subscriptions/clinics/${clinicId}/checkout/`,
      payload
    );
    return res.data.data;
  },

  verifyPayment: async (
    clinicId: string,
    payload: VerifyPaymentPayload
  ): Promise<{ payment_id: string; invoice_id: string; invoice_number: string; plan_name: string; status: string }> => {
    const res = await apiClient.post<{
      success: boolean;
      message: string;
      data: { payment_id: string; invoice_id: string; invoice_number: string; plan_name: string; status: string };
    }>(`/subscriptions/clinics/${clinicId}/verify/`, payload);
    return res.data.data;
  },

  cancelSubscription: async (clinicId: string, reason: string): Promise<void> => {
    await apiClient.post(`/subscriptions/clinics/${clinicId}/cancel/`, { reason });
  },

  getClinicInvoices: async (clinicId: string): Promise<SubscriptionInvoice[]> => {
    const res = await apiClient.get<{ success: boolean; data: SubscriptionInvoice[] }>(
      `/subscriptions/clinics/${clinicId}/invoices/`
    );
    return res.data.data;
  },

  getClinicInvoiceDetail: async (clinicId: string, invoiceId: string): Promise<SubscriptionInvoice> => {
    const res = await apiClient.get<{ success: boolean; data: SubscriptionInvoice }>(
      `/subscriptions/clinics/${clinicId}/invoices/${invoiceId}/`
    );
    return res.data.data;
  },

  getClinicEvents: async (clinicId: string): Promise<SubscriptionEvent[]> => {
    const res = await apiClient.get<{ success: boolean; data: SubscriptionEvent[] }>(
      `/subscriptions/clinics/${clinicId}/events/`
    );
    return res.data.data;
  },

  // Super Admin Endpoints
  getAdminMetrics: async (): Promise<AdminSubscriptionMetrics> => {
    const res = await apiClient.get<{ success: boolean; data: AdminSubscriptionMetrics }>(
      "/admin/subscriptions/metrics/"
    );
    return res.data.data;
  },

  getAdminPlans: async (): Promise<SubscriptionPlan[]> => {
    const res = await apiClient.get<{ success: boolean; data: SubscriptionPlan[] }>(
      "/admin/subscriptions/plans/"
    );
    return res.data.data;
  },

  createAdminPlan: async (payload: Partial<SubscriptionPlan>): Promise<SubscriptionPlan> => {
    const res = await apiClient.post<{ success: boolean; data: SubscriptionPlan }>(
      "/admin/subscriptions/plans/",
      payload
    );
    return res.data.data;
  },

  updateAdminPlan: async (planId: string, payload: Partial<SubscriptionPlan>): Promise<SubscriptionPlan> => {
    const res = await apiClient.patch<{ success: boolean; data: SubscriptionPlan }>(
      `/admin/subscriptions/plans/${planId}/`,
      payload
    );
    return res.data.data;
  },

  getAdminClinicSubscriptions: async (params?: {
    status?: string;
    tier?: string;
    search?: string;
  }): Promise<ClinicEntitlementsSummary[]> => {
    const res = await apiClient.get<{ success: boolean; data: ClinicEntitlementsSummary[] }>(
      "/admin/subscriptions/clinics/",
      { params }
    );
    return res.data.data;
  },

  overrideClinicSubscription: async (clinicId: string, payload: AdminOverridePayload): Promise<void> => {
    await apiClient.post(`/admin/subscriptions/clinics/${clinicId}/override/`, payload);
  },

  getAdminEvents: async (limit = 50): Promise<SubscriptionEvent[]> => {
    const res = await apiClient.get<{ success: boolean; data: SubscriptionEvent[] }>(
      "/admin/subscriptions/events/",
      { params: { limit } }
    );
    return res.data.data;
  },
};
