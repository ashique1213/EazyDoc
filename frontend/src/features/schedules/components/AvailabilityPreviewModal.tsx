import React, { useState } from "react";
import {
  Calendar,
  CheckCircle2,
  Clock,
  Globe2,
  Loader2,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAvailabilitySlots } from "../hooks";

interface AvailabilityPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  doctorClinicId: string;
  doctorName?: string;
  clinicName?: string;
}

export const AvailabilityPreviewModal: React.FC<AvailabilityPreviewModalProps> = ({
  isOpen,
  onClose,
  doctorClinicId,
  doctorName,
  clinicName,
}) => {
  // Default to today in YYYY-MM-DD
  const todayStr = new Date().toISOString().split("T")[0];
  const [selectedDate, setSelectedDate] = useState<string>(todayStr);

  const { data, isLoading } = useAvailabilitySlots(
    doctorClinicId,
    selectedDate,
    isOpen
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl rounded-xl border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2 text-foreground">
              <Sparkles className="h-5 w-5 text-primary" />
              Bookable Availability Slot Engine
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Real-time slot generation combining recurring shifts, doctor leaves, and administrative blocked slots.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Doctor & Clinic Context Info */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-muted/30 p-3 rounded-lg border text-xs">
          <div>
            <span className="text-muted-foreground">Practitioner: </span>
            <strong className="text-foreground">{doctorName || data?.doctor.full_name || "Doctor"}</strong>
            {data?.doctor.specialization && (
              <span className="text-muted-foreground"> ({data.doctor.specialization})</span>
            )}
          </div>
          <div>
            <span className="text-muted-foreground">Clinic: </span>
            <strong className="text-foreground">{clinicName || data?.clinic.name || "Clinic"}</strong>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            <Globe2 className="h-3.5 w-3.5" />
            <span>Timezone: </span>
            <strong className="text-foreground">{data?.clinic.timezone || "Asia/Kolkata"}</strong>
          </div>
        </div>

        {/* Date Selector & Stats */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="space-y-1.5 w-full sm:w-56">
            <Label htmlFor="previewDate" className="text-xs font-semibold flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-primary" />
              Select Date to Inspect
            </Label>
            <Input
              id="previewDate"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="h-9 text-xs"
            />
          </div>

          {data && data.is_eligible && (
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-muted/40 border px-3 py-1.5 text-center">
                <span className="text-[10px] text-muted-foreground block uppercase font-medium">Total Slots</span>
                <span className="text-sm font-bold text-foreground">{data.total_slots}</span>
              </div>
              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 text-center">
                <span className="text-[10px] text-emerald-800 dark:text-emerald-300 block uppercase font-medium">Available</span>
                <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400">
                  {data.available_slots_count}
                </span>
              </div>
              <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 text-center">
                <span className="text-[10px] text-amber-800 dark:text-amber-300 block uppercase font-medium">Unavailable</span>
                <span className="text-sm font-bold text-amber-700 dark:text-amber-400">
                  {data.total_slots - data.available_slots_count}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Eligibility Warning */}
        {data && !data.is_eligible && (
          <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300 py-3">
            <ShieldAlert className="h-4 w-4 text-amber-600" />
            <AlertTitle className="text-xs font-semibold">Availability Inactive</AlertTitle>
            <AlertDescription className="text-xs mt-1">
              {data.eligibility_error || "This doctor or clinic is not active for booking."}
            </AlertDescription>
          </Alert>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground space-y-2">
            <Loader2 className="h-7 w-7 animate-spin text-primary" />
            <p className="text-xs">Computing discrete availability slots...</p>
          </div>
        )}

        {/* Slots Content */}
        {!isLoading && data && data.is_eligible && (
          <div className="space-y-3">
            {/* Legend */}
            <div className="flex items-center gap-4 text-[11px] text-muted-foreground border-b pb-2">
              <span className="font-semibold text-foreground">Legend:</span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                Bookable Slot
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                Doctor On Leave / Time Off
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
                Administrative Hold
              </span>
            </div>

            {data.slots.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-72 overflow-y-auto pr-1">
                {data.slots.map((slot, index) => {
                  const isAvail = slot.is_available;
                  const isLeave = slot.reason?.includes("Doctor unavailable");

                  return (
                    <div
                      key={index}
                      className={`rounded-lg border p-2.5 text-xs transition-all flex flex-col justify-between ${
                        isAvail
                          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-950 dark:text-emerald-100 hover:border-emerald-500"
                          : isLeave
                          ? "bg-amber-500/10 border-amber-500/30 text-amber-950 dark:text-amber-100"
                          : "bg-rose-500/10 border-rose-500/30 text-rose-950 dark:text-rose-100"
                      }`}
                      title={slot.reason || "Available Slot"}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold">
                          {slot.start_time} – {slot.end_time}
                        </span>
                        {isAvail ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                        ) : (
                          <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </div>

                      {slot.reason && (
                        <p className="text-[10px] mt-1 font-medium truncate opacity-90">
                          {slot.reason}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-12 text-center text-muted-foreground border rounded-lg border-dashed space-y-1">
                <Clock className="h-6 w-6 mx-auto stroke-1" />
                <p className="text-xs font-medium text-foreground">No Shifts Scheduled for this Day</p>
                <p className="text-[11px]">
                  {data.day_name} ({selectedDate}) has no active recurring shifts configured for this doctor.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t">
          <span className="text-[11px] text-muted-foreground">
            Slots generated in clinic operating timezone: <strong>{data?.clinic.timezone || "Asia/Kolkata"}</strong>
          </span>
          <Button size="sm" variant="outline" onClick={onClose} className="text-xs h-8">
            Close Inspector
          </Button>
        </div>
      </div>
    </div>
  );
};
