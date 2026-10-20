import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Calendar,
  Clock,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCancelAppointment } from "./hooks";
import type { Appointment } from "./types";

interface AppointmentCancelDialogProps {
  isOpen: boolean;
  onClose: () => void;
  appointment: Appointment;
  onSuccess?: () => void;
}

export function AppointmentCancelDialog({
  isOpen,
  onClose,
  appointment,
  onSuccess,
}: AppointmentCancelDialogProps) {
  const [reason, setReason] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cancelMutation = useCancelAppointment();

  if (!isOpen) return null;

  const startDate = new Date(appointment.start_at);
  const dateFormatted = startDate.toLocaleDateString("en-IN", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const timeFormatted = startDate.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });

  const isEligible = appointment.is_cancellable ?? true;
  const isException = appointment.reschedule_required || appointment.status === "RESCHEDULE_REQUIRED";

  const handleConfirm = () => {
    setErrorMessage(null);
    cancelMutation.mutate(
      {
        appointmentId: appointment.id,
        payload: { reason: reason.trim() },
      },
      {
        onSuccess: () => {
          onClose();
          onSuccess?.();
        },
        onError: (err: unknown) => {
          const anyErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string };
          const msg =
            anyErr.response?.data?.detail ||
            anyErr.response?.data?.message ||
            anyErr.message ||
            "Failed to cancel appointment. The policy cutoff may have passed.";
          setErrorMessage(msg);
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border/60 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
                <AlertTriangle className="h-4 w-4" />
              </span>
              <h3 className="text-lg font-bold text-foreground">Cancel Appointment</h3>
            </div>
            <p className="text-xs text-muted-foreground">
              Booking Ref: <strong className="font-mono text-foreground">{appointment.booking_reference}</strong>
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={cancelMutation.isPending}
            className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Appointment Summary Box */}
        <div className="rounded-xl border border-border/60 bg-muted/20 p-4 space-y-2 text-xs">
          <div className="flex justify-between items-center text-foreground font-semibold">
            <span>{appointment.doctor.full_name}</span>
            <span className="text-muted-foreground">{appointment.clinic.name}</span>
          </div>
          <div className="flex items-center gap-4 text-muted-foreground pt-1">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 text-primary" /> {dateFormatted}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-primary" /> {timeFormatted}
            </span>
          </div>
        </div>

        {/* Policy notice */}
        {isException ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300 space-y-1">
            <div className="flex items-center gap-1.5 font-bold">
              <AlertCircle className="h-4 w-4" />
              <span>Authorized Exception Active</span>
            </div>
            <p>
              The doctor or clinic reported an unavailability for this shift. You may cancel or reschedule free of cutoff restrictions.
            </p>
          </div>
        ) : isEligible ? (
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground space-y-1">
            <span className="font-bold text-foreground block">Cancellation Policy:</span>
            <p>
              Cancellation is permitted until <strong>11:59:59 PM</strong> on the day before your appointment in the clinic's local timezone (
              {appointment.clinic.timezone || "Asia/Kolkata"}). Once the appointment date arrives, patient-initiated cancellation is closed.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive space-y-1">
            <div className="flex items-center gap-1.5 font-bold">
              <AlertCircle className="h-4 w-4" />
              <span>Policy Cutoff Exceeded</span>
            </div>
            <p>
              The cancellation deadline for this appointment (11:59:59 PM on the day prior in {appointment.clinic.timezone || "Asia/Kolkata"}) has passed. Please contact the clinic directly for assistance.
            </p>
          </div>
        )}

        {/* Error message */}
        {errorMessage && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Cancellation Reason */}
        <div className="space-y-1.5">
          <label htmlFor="cancel-reason" className="text-xs font-bold text-foreground">
            Reason for Cancellation <span className="text-muted-foreground font-normal">(optional)</span>
          </label>
          <textarea
            id="cancel-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={cancelMutation.isPending || (!isEligible && !isException)}
            placeholder="Please let us know why you are cancelling..."
            className="w-full rounded-xl border border-input bg-background p-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 border-t border-border/60 pt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={cancelMutation.isPending}
          >
            Keep Appointment
          </Button>

          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleConfirm}
            disabled={cancelMutation.isPending || (!isEligible && !isException)}
            className="gap-2 font-bold"
          >
            {cancelMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Cancelling...</span>
              </>
            ) : (
              <span>Confirm Cancellation</span>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
