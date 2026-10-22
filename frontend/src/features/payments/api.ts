import { apiClient } from "@/services/api";
import type {
  CreatePaymentOrderPayload,
  PatientPaymentStatus,
  PaymentOrderResponse,
  PaymentVerificationPayload,
} from "./types";

export const paymentsApi = {
  createPaymentOrder: async (
    payload: CreatePaymentOrderPayload,
    idempotencyKey?: string
  ): Promise<PaymentOrderResponse> => {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }
    const response = await apiClient.post<PaymentOrderResponse>(
      "/payments/create-order/",
      {
        ...payload,
        idempotency_key: idempotencyKey || payload.idempotency_key,
      },
      { headers }
    );
    return response.data;
  },

  verifyPayment: async (
    payload: PaymentVerificationPayload
  ): Promise<PatientPaymentStatus> => {
    const response = await apiClient.post<PatientPaymentStatus>(
      "/payments/verify/",
      payload
    );
    return response.data;
  },

  getPaymentStatus: async (
    appointmentId: string
  ): Promise<PatientPaymentStatus> => {
    const response = await apiClient.get<PatientPaymentStatus>(
      `/payments/appointment/${appointmentId}/status/`
    );
    return response.data;
  },
};
