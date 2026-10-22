import { useState, useCallback } from "react";
import { paymentsApi } from "./api";
import type { PatientPaymentStatus } from "./types";

const RAZORPAY_SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";

const loadRazorpayScript = (): Promise<boolean> => {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = RAZORPAY_SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

interface UseRazorpayCheckoutOptions {
  onSuccess?: (payment: PatientPaymentStatus) => void;
  onError?: (errorMessage: string) => void;
}

export function useRazorpayCheckout({ onSuccess, onError }: UseRazorpayCheckoutOptions = {}) {
  const [isInitiating, setIsInitiating] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<PatientPaymentStatus | null>(null);

  const initiateCheckout = useCallback(
    async (params: {
      appointmentId: string;
      patientName?: string;
      patientEmail?: string;
      patientPhone?: string;
    }) => {
      setIsInitiating(true);
      setErrorMessage(null);

      try {
        const isLoaded = await loadRazorpayScript();
        if (!isLoaded) {
          throw new Error("Unable to load Razorpay payment gateway. Please check your internet connection.");
        }

        const idempotencyKey = crypto.randomUUID();
        const orderData = await paymentsApi.createPaymentOrder(
          { appointment_id: params.appointmentId },
          idempotencyKey
        );

        const options = {
          key: orderData.key_id,
          amount: orderData.amount_paise,
          currency: orderData.currency,
          name: "EazyDoc Health",
          description: `Consultation with Dr. ${orderData.doctor_name}`,
          order_id: orderData.order_id,
          prefill: {
            name: params.patientName || "",
            email: params.patientEmail || "",
            contact: params.patientPhone || "",
          },
          theme: {
            color: "#059669", // Tailwind emerald-600
          },
          handler: async (response: {
            razorpay_payment_id: string;
            razorpay_order_id: string;
            razorpay_signature: string;
          }) => {
            setIsVerifying(true);
            try {
              // Crucial: Backend must verify cryptographic signature before treating payment as successful
              const verifiedPayment = await paymentsApi.verifyPayment({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              });

              setPaymentStatus(verifiedPayment);
              setIsVerifying(false);
              if (onSuccess) {
                onSuccess(verifiedPayment);
              }
            } catch (err: unknown) {
              setIsVerifying(false);
              const axiosErr = err as {
                response?: { data?: { detail?: string; message?: string } };
                message?: string;
              };
              const msg =
                axiosErr?.response?.data?.detail ||
                axiosErr?.response?.data?.message ||
                axiosErr?.message ||
                "Payment verification failed. Please contact support or check your payment status.";
              setErrorMessage(msg);
              if (onError) onError(msg);
            }
          },
          modal: {
            ondismiss: () => {
              setIsInitiating(false);
              // Notice: Do NOT automatically mark payment failed when modal is dismissed
            },
          },
        };

        const razorpayInstance = new window.Razorpay(options);
        razorpayInstance.open();
        setIsInitiating(false);
      } catch (err: unknown) {
        setIsInitiating(false);
        const axiosErr = err as {
          response?: { data?: { detail?: string; message?: string } };
          message?: string;
        };
        const msg =
          axiosErr?.response?.data?.detail ||
          axiosErr?.response?.data?.message ||
          axiosErr?.message ||
          "Failed to initiate payment. Please try again.";
        setErrorMessage(msg);
        if (onError) onError(msg);
      }
    },
    [onSuccess, onError]
  );

  const refreshStatus = useCallback(async (appointmentId: string) => {
    try {
      const statusData = await paymentsApi.getPaymentStatus(appointmentId);
      setPaymentStatus(statusData);
      return statusData;
    } catch {
      return null;
    }
  }, []);

  return {
    initiateCheckout,
    refreshStatus,
    isInitiating,
    isVerifying,
    isLoading: isInitiating || isVerifying,
    errorMessage,
    paymentStatus,
    clearError: () => setErrorMessage(null),
  };
}
