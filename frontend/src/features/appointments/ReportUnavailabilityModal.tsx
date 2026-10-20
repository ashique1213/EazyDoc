import { useState } from "react";
import { AlertCircle, AlertTriangle, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDoctorReportUnavailability, useClinicReportUnavailability } from "./hooks";
import type { Appointment } from "./types";

interface ReportUnavailabilityModalProps {
  isOpen: boolean;
  onClose: () => void;
  appointment: Appointment;
  clinicScope?: boolean;
  onSuccess?: () => void;
}

export function ReportUnavailabilityModal({
  isOpen,
  onClose,
  appointment,
  clinicScope = false,
  onSuccess,
}: ReportUnavailabilityModalProps) {
  const [reason, setReason] = useState("");
  const [action, setAction] = useState<"RESCHEDULE_REQUIRED" | "CANCEL">("RESCHEDULE_REQUIRED");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const doctorReportMutation = useDoctorReportUnavailability();
  const clinicReportMutation = useClinicReportUnavailability();

  if (!isOpen) return null;

  const isPending = doctorReportMutation.isPending || clinicReportMutation.isPending;

  const handleConfirm = () => {
    if (!reason.trim()) {
      setErrorMessage("Please enter a documented reason for this unavailability report.");
      return;
    }

    setErrorMessage(null);

    const payload = {
      reason: reason.trim(),
      action,
    };

    const handleSuccess = () => {
      onClose();
      onSuccess?.();
    };

    const handleError = (err: unknown) => {
      const anyErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string };
      setErrorMessage(
        anyErr.response?.data?.detail ||
        anyErr.response?.data?.message ||
        anyErr.message ||
        "Failed to report unavailability."
      );
    };

    if (clinicScope) {
      clinicReportMutation.mutate(
        {
          clinicId: appointment.clinic.id,
          appointmentId: appointment.id,
          payload,
        },
        { onSuccess: handleSuccess, onError: handleError }
      );
    } else {
      doctorReportMutation.mutate(
        {
          appointmentId: appointment.id,
          payload,
        },
        { onSuccess: handleSuccess, onError: handleError }
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-6">
        <div className="flex items-start justify-between border-b border-border/60 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600">
                <AlertTriangle className="h-4 w-4" />
              </span>
              <h3 className="text-lg font-bold text-foreground">Report Unavailability</h3>
            </div>
            <p className="text-xs text-muted-foreground">
              Doctor / Clinic exception management for booking:{" "}
              <strong className="font-mono text-foreground">{appointment.booking_reference}</strong>
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isPending}
            className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="rounded-xl border border-amber-500/20 bg-amber-50/50 dark:bg-amber-950/20 p-3 text-xs text-muted-foreground space-y-1">
          <span className="font-bold text-foreground block">Authorized Exception Workflow:</span>
          <p>
            Reporting unavailability flags this appointment for patient resolution, allowing the patient to pick another slot or cancel even if the standard cutoff has passed.
          </p>
        </div>

        {errorMessage && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="space-y-2">
          <label className="text-xs font-bold text-foreground block">Action</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setAction("RESCHEDULE_REQUIRED")}
              className={`rounded-xl p-3 text-xs font-bold border text-left transition-all ${
                action === "RESCHEDULE_REQUIRED"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-background text-foreground"
              }`}
            >
              <div>Flag for Rescheduling</div>
              <p className="text-[10px] text-muted-foreground font-normal mt-0.5">
                Patient can choose a replacement slot
              </p>
            </button>

            <button
              type="button"
              onClick={() => setAction("CANCEL")}
              className={`rounded-xl p-3 text-xs font-bold border text-left transition-all ${
                action === "CANCEL"
                  ? "border-destructive bg-destructive/10 text-destructive"
                  : "border-border bg-background text-foreground"
              }`}
            >
              <div>Cancel Directly</div>
              <p className="text-[10px] text-muted-foreground font-normal mt-0.5">
                Immediately cancel this consultation
              </p>
            </button>
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="unavail-reason" className="text-xs font-bold text-foreground">
            Documented Reason <span className="text-destructive">*</span>
          </label>
          <textarea
            id="unavail-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={isPending}
            placeholder="e.g. Doctor acute illness, sudden emergency, clinic unexpected closure..."
            className="w-full rounded-xl border border-input bg-background p-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-border/60 pt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={isPending}
          >
            Dismiss
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={handleConfirm}
            disabled={isPending || !reason.trim()}
            className="gap-2 font-bold"
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Recording...</span>
              </>
            ) : (
              <span>Confirm & Record</span>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
