export type PaymentStatus =
  | "NOT_REQUIRED"
  | "PENDING"
  | "AUTHORIZED"
  | "PAID"
  | "FAILED"
  | "REFUND_PENDING"
  | "PARTIALLY_REFUNDED"
  | "REFUNDED";

export interface CreatePaymentOrderPayload {
  appointment_id: string;
  idempotency_key?: string;
}

export interface PaymentOrderResponse {
  order_id: string;
  amount: string;
  amount_paise: number;
  currency: string;
  key_id: string;
  appointment_id: string;
  booking_reference: string;
  doctor_name: string;
  clinic_name: string;
}

export interface PaymentVerificationPayload {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface PatientPaymentStatus {
  id: string;
  appointment_id: string;
  booking_reference: string;
  appointment_status: string;
  amount: string;
  currency: string;
  status: PaymentStatus;
  gateway_order_id: string;
  gateway_payment_id: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface RazorpaySuccessResponse {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

export interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  handler: (response: RazorpaySuccessResponse) => void;
  prefill?: {
    name?: string;
    email?: string;
    contact?: string;
  };
  notes?: Record<string, string>;
  theme?: {
    color?: string;
  };
  modal?: {
    ondismiss?: () => void;
    escape?: boolean;
    backdropclose?: boolean;
  };
}

export interface RazorpayInstance {
  open: () => void;
  on: (event: string, callback: (response: unknown) => void) => void;
}

declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => RazorpayInstance;
  }
}
