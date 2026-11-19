import { useState } from "react";
import { AlertTriangle, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CancelSubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
  periodEndDate?: string | null;
}

export function CancelSubscriptionModal({
  isOpen,
  onClose,
  onConfirm,
  periodEndDate,
}: CancelSubscriptionModalProps) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleCancel = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(reason);
      onClose();
    } catch {
      // Handled in caller
    } finally {
      setIsSubmitting(false);
    }
  };

  const formattedPeriodEnd = periodEndDate
    ? new Date(periodEndDate).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "the end of your current cycle";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl border bg-card p-6 shadow-xl animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between pb-3 border-b">
          <div className="flex items-center space-x-2 text-destructive">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-bold text-lg text-foreground">Cancel Subscription</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3.5 text-xs text-emerald-800 flex items-start space-x-2">
            <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
            <div>
              <strong className="block font-semibold">Your Data is Safe and Preserved</strong>
              We will never delete your affiliated doctors, historical appointments, patient files, or financial records upon cancellation.
            </div>
          </div>

          <p className="text-sm text-muted-foreground">
            You will retain full operational access to all features until{" "}
            <span className="font-semibold text-foreground">{formattedPeriodEnd}</span>.
            After that date, your facility will gracefully shift to the Free Community plan.
          </p>

          <div className="space-y-1.5 pt-2">
            <label className="text-xs font-semibold text-foreground">
              Please share why you are cancelling (Optional):
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Consolidating branch locations, temporary pause..."
              className="w-full rounded-lg border bg-background p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[80px]"
            />
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end space-x-3 pt-3 border-t">
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Keep Subscription
          </Button>
          <Button variant="destructive" onClick={handleCancel} disabled={isSubmitting}>
            {isSubmitting ? "Cancelling..." : "Confirm Cancellation"}
          </Button>
        </div>
      </div>
    </div>
  );
}
