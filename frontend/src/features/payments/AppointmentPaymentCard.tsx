import { useState } from "react";
import {
  CreditCard,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useRazorpayCheckout } from "./useRazorpayCheckout";
import type { PatientPaymentStatus } from "./types";

interface AppointmentPaymentCardProps {
  appointmentId: string;
  doctorName: string;
  clinicName: string;
  appointmentDateTime: string;
  consultationFee: string;
  currency?: string;
  initialPaymentStatus?: string;
  patientName?: string;
  patientEmail?: string;
  patientPhone?: string;
  onPaymentSuccess?: (payment: PatientPaymentStatus) => void;
}

export function AppointmentPaymentCard({
  appointmentId,
  doctorName,
  clinicName,
  appointmentDateTime,
  consultationFee,
  initialPaymentStatus = "PENDING",
  patientName,
  patientEmail,
  patientPhone,
  onPaymentSuccess,
}: AppointmentPaymentCardProps) {
  const [currentStatus, setCurrentStatus] = useState<string>(initialPaymentStatus);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const {
    initiateCheckout,
    refreshStatus,
    isInitiating,
    isVerifying,
    isLoading,
    errorMessage,
    clearError,
  } = useRazorpayCheckout({
    onSuccess: (payment) => {
      setCurrentStatus(payment.status);
      if (onPaymentSuccess) {
        onPaymentSuccess(payment);
      }
    },
  });

  const handlePayClick = () => {
    clearError();
    initiateCheckout({
      appointmentId,
      patientName,
      patientEmail,
      patientPhone,
    });
  };

  const handleRefreshClick = async () => {
    setIsRefreshing(true);
    const updated = await refreshStatus(appointmentId);
    if (updated) {
      setCurrentStatus(updated.status);
      if (updated.status === "PAID" && onPaymentSuccess) {
        onPaymentSuccess(updated);
      }
    }
    setIsRefreshing(false);
  };

  const isPaid = currentStatus === "PAID";

  if (isPaid) {
    return (
      <Card className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 shadow-sm">
        <CardContent className="p-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <div>
              <div className="text-sm font-bold text-foreground flex items-center gap-2">
                <span>Consultation Fee Paid</span>
                <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 text-[10px]">
                  Verified
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Payment verified securely by Razorpay. Your appointment is confirmed.
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Amount Paid
            </div>
            <div className="text-lg font-black text-foreground">
              ₹{consultationFee}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-2xl border border-border/80 bg-card shadow-md overflow-hidden">
      <CardHeader className="bg-muted/30 border-b border-border/60 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-primary" />
            <span className="text-sm font-bold text-foreground">Consultation Payment Summary</span>
          </div>
          <Badge variant="outline" className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 border-amber-500/30">
            Payment Pending
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-5 space-y-4">
        {/* Error notification */}
        {errorMessage && (
          <div className="flex items-start gap-2.5 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <div className="flex-1 space-y-1">
              <p className="font-semibold">Payment Notice</p>
              <p>{errorMessage}</p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearError}
              className="h-6 px-2 text-[11px]"
            >
              Dismiss
            </Button>
          </div>
        )}

        {/* Breakdown of Booking Details */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs rounded-xl bg-muted/20 border border-border/50 p-3.5">
          <div className="space-y-0.5">
            <span className="text-muted-foreground">Doctor</span>
            <div className="font-bold text-foreground">{doctorName}</div>
          </div>
          <div className="space-y-0.5">
            <span className="text-muted-foreground">Clinic</span>
            <div className="font-bold text-foreground">{clinicName}</div>
          </div>
          <div className="space-y-0.5 sm:col-span-2">
            <span className="text-muted-foreground">Schedule</span>
            <div className="font-semibold text-foreground">{appointmentDateTime}</div>
          </div>
        </div>

        {/* Pricing Summary Table */}
        <div className="space-y-2 border-t border-border/50 pt-3 text-xs">
          <div className="flex items-center justify-between text-muted-foreground">
            <span>Doctor Consultation Fee</span>
            <span className="font-medium text-foreground">₹{consultationFee}</span>
          </div>
          <div className="flex items-center justify-between text-sm font-bold pt-1 border-t border-border/40">
            <span className="text-foreground">Total Payable Amount</span>
            <span className="text-lg font-black text-emerald-600 dark:text-emerald-400">
              ₹{consultationFee}
            </span>
          </div>
        </div>

        {/* Trust & Gateway Security Badge */}
        <div className="flex items-center justify-between text-[11px] text-muted-foreground bg-emerald-500/5 rounded-lg px-3 py-2 border border-emerald-500/15">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />
            <span>Secured by Razorpay • UPI, Cards & NetBanking</span>
          </div>
          <Lock className="h-3 w-3 opacity-60" />
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <Button
            type="button"
            className="w-full sm:flex-1 gap-2 font-bold bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={handlePayClick}
            disabled={isLoading}
          >
            {isVerifying ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Verifying Payment Signature...</span>
              </>
            ) : isInitiating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Opening Razorpay Checkout...</span>
              </>
            ) : (
              <>
                <CreditCard className="h-4 w-4" />
                <span>Pay ₹{consultationFee} Now</span>
              </>
            )}
          </Button>

          <Button
            type="button"
            variant="outline"
            size="default"
            className="w-full sm:w-auto gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            onClick={handleRefreshClick}
            disabled={isLoading || isRefreshing}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>Refresh Status</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
