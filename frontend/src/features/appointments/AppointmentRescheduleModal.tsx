import { useState, useEffect } from "react";
import {
  AlertCircle,
  Calendar,
  Clock,
  Loader2,
  X,
  CheckCircle2,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { discoveryApi } from "@/features/discovery/api";
import type { AvailabilitySlot, PublicAvailabilityResponse } from "@/features/discovery/types";
import { useRescheduleAppointment } from "./hooks";
import type { Appointment } from "./types";

interface AppointmentRescheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  appointment: Appointment;
  onSuccess?: () => void;
}

export function AppointmentRescheduleModal({
  isOpen,
  onClose,
  appointment,
  onSuccess,
}: AppointmentRescheduleModalProps) {
  // Tomorrow's date formatted as YYYY-MM-DD
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const initialDateStr = tomorrow.toISOString().split("T")[0];

  const [selectedDate, setSelectedDate] = useState<string>(initialDateStr);
  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | null>(null);
  const [reason, setReason] = useState("");
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [availability, setAvailability] = useState<PublicAvailabilityResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const rescheduleMutation = useRescheduleAppointment();

  // Load available slots whenever selectedDate changes
  useEffect(() => {
    if (!isOpen || !selectedDate) return;

    let isMounted = true;
    setSlotsLoading(true);
    setErrorMessage(null);
    setSelectedSlot(null);

    discoveryApi
      .getDoctorAvailability(appointment.clinic.id, appointment.doctor.id, selectedDate)
      .then((data) => {
        if (isMounted) {
          setAvailability(data);
          setSlotsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setAvailability(null);
          setSlotsLoading(false);
          setErrorMessage(err.message || "Failed to load availability slots for this date.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, selectedDate, appointment.clinic.id, appointment.doctor.id]);

  if (!isOpen) return null;

  const currentStart = new Date(appointment.start_at);
  const currentDateFormatted = currentStart.toLocaleDateString("en-IN", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const currentTimeFormatted = currentStart.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });

  const isEligible = appointment.is_reschedulable ?? true;
  const isException = appointment.reschedule_required || appointment.status === "RESCHEDULE_REQUIRED";

  const handleConfirm = () => {
    if (!selectedSlot) return;

    setErrorMessage(null);
    rescheduleMutation.mutate(
      {
        appointmentId: appointment.id,
        payload: {
          start_at: selectedSlot.start_datetime_utc,
          reason: reason.trim(),
        },
      },
      {
        onSuccess: () => {
          onClose();
          onSuccess?.();
        },
        onError: (err: unknown) => {
          const anyErr = err as {
            response?: { status?: number; data?: { detail?: string; message?: string } };
            message?: string;
          };
          const msg =
            anyErr.response?.data?.detail ||
            anyErr.response?.data?.message ||
            anyErr.message ||
            "Failed to reschedule appointment. The destination slot may no longer be available.";
          setErrorMessage(msg);
          // If conflict (409), reload availability slots so user can pick another
          if (anyErr.response?.status === 409) {
            discoveryApi
              .getDoctorAvailability(appointment.clinic.id, appointment.doctor.id, selectedDate)
              .then((data) => setAvailability(data))
              .catch(() => {});
          }
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border/60 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Calendar className="h-4 w-4" />
              </span>
              <h3 className="text-lg font-bold text-foreground">Reschedule Appointment</h3>
            </div>
            <p className="text-xs text-muted-foreground">
              Select a new date and time slot with Dr. {appointment.doctor.full_name} at {appointment.clinic.name}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={rescheduleMutation.isPending}
            className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Current Slot Summary */}
        <div className="rounded-xl border border-border/60 bg-muted/20 p-4 space-y-2 text-xs">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Current Appointment
          </span>
          <div className="flex flex-wrap items-center gap-4 text-foreground font-semibold pt-1">
            <span className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-primary" /> {currentDateFormatted}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-primary" /> {currentTimeFormatted}
            </span>
            <Badge variant="outline" className="text-[10px]">
              {appointment.clinic.timezone || "Asia/Kolkata"}
            </Badge>
          </div>
        </div>

        {/* Policy / Exception Notice */}
        {isException ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300 space-y-1">
            <div className="flex items-center gap-1.5 font-bold">
              <Sparkles className="h-4 w-4" />
              <span>Priority Exception Rescheduling</span>
            </div>
            <p>
              Due to doctor or clinic unavailability, you can choose any replacement slot free of normal cutoff limits.
            </p>
          </div>
        ) : isEligible ? (
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
            Rescheduling cutoff is <strong>11:59:59 PM</strong> on the day prior to your visit in {appointment.clinic.timezone || "Asia/Kolkata"}.
          </div>
        ) : (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>The rescheduling cutoff has passed for this appointment.</span>
          </div>
        )}

        {/* Error message */}
        {errorMessage && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-bold block">Rescheduling Error</span>
              <span>{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Date Selection */}
        <div className="space-y-2">
          <label htmlFor="reschedule-date" className="text-xs font-bold text-foreground block">
            Select Replacement Date
          </label>
          <input
            id="reschedule-date"
            type="date"
            min={new Date().toISOString().split("T")[0]}
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            disabled={rescheduleMutation.isPending || (!isEligible && !isException)}
            className="w-full rounded-xl border border-input bg-background p-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Available Slots */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-foreground">Available Slots</span>
            {availability && (
              <span className="text-[11px] text-muted-foreground">
                {availability.available_slots_count} slots available
              </span>
            )}
          </div>

          {slotsLoading ? (
            <div className="flex items-center justify-center p-8 text-xs text-muted-foreground gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span>Checking schedule and travel buffers...</span>
            </div>
          ) : !availability || availability.slots.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
              No active doctor shifts found on this date. Please select another date.
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-48 overflow-y-auto p-1">
              {availability.slots.map((slot) => {
                const isSelected = selectedSlot?.start_time === slot.start_time;
                return (
                  <button
                    key={slot.start_time}
                    type="button"
                    disabled={!slot.is_available || rescheduleMutation.isPending}
                    onClick={() => setSelectedSlot(slot)}
                    title={slot.reason || undefined}
                    className={`rounded-xl p-2.5 text-xs font-bold border transition-all text-center ${
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground shadow-sm"
                        : slot.is_available
                        ? "border-border/80 bg-background hover:border-primary/50 text-foreground"
                        : "border-border/40 bg-muted/30 text-muted-foreground/50 cursor-not-allowed line-through"
                    }`}
                  >
                    {slot.start_time}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Slot Summary Preview */}
        {selectedSlot && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-950/20 p-3 text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-emerald-700 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4" />
              <span>Selected Replacement Slot</span>
            </div>
            <p className="text-foreground">
              {new Date(selectedDate).toLocaleDateString("en-IN", {
                weekday: "long",
                month: "short",
                day: "numeric",
              })}{" "}
              at <strong>{selectedSlot.start_time} – {selectedSlot.end_time}</strong>
            </p>
          </div>
        )}

        {/* Reason */}
        <div className="space-y-1.5">
          <label htmlFor="reschedule-reason" className="text-xs font-bold text-foreground">
            Reason for Rescheduling <span className="text-muted-foreground font-normal">(optional)</span>
          </label>
          <input
            id="reschedule-reason"
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={rescheduleMutation.isPending || (!isEligible && !isException)}
            placeholder="e.g. Schedule clash, work meeting, preferred time..."
            className="w-full rounded-xl border border-input bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 border-t border-border/60 pt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={rescheduleMutation.isPending}
          >
            Cancel
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={handleConfirm}
            disabled={!selectedSlot || rescheduleMutation.isPending || (!isEligible && !isException)}
            className="gap-2 font-bold"
          >
            {rescheduleMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Rescheduling...</span>
              </>
            ) : (
              <>
                <span>Confirm Reschedule</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
