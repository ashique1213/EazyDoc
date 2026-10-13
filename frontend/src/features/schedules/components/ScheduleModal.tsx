import React, { useState, useEffect } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  WEEKDAY_LABELS,
  type ConflictDetails,
  type DoctorSchedule,
  type SchedulePayload,
  type WeekdayNumber,
} from "../types";
import { useCheckConflict, useCreateSchedule, useUpdateSchedule } from "../hooks";

interface ScheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  doctorClinicId: string;
  doctorName?: string;
  clinicName?: string;
  scheduleToEdit?: DoctorSchedule | null;
  defaultDay?: WeekdayNumber;
  defaultSlotDuration?: number;
  onSuccess?: () => void;
}

export const ScheduleModal: React.FC<ScheduleModalProps> = ({
  isOpen,
  onClose,
  doctorClinicId,
  doctorName,
  clinicName,
  scheduleToEdit,
  defaultDay = 0,
  defaultSlotDuration = 15,
  onSuccess,
}) => {
  const [dayOfWeek, setDayOfWeek] = useState<WeekdayNumber>(defaultDay);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("13:00");
  const [slotDuration, setSlotDuration] = useState<string>(String(defaultSlotDuration));
  const [bufferMinutes, setBufferMinutes] = useState<number>(0);
  const [effectiveFrom, setEffectiveFrom] = useState<string>("");
  const [effectiveUntil, setEffectiveUntil] = useState<string>("");

  // Conflict pre-validation state
  const [conflictResult, setConflictResult] = useState<{
    checked: boolean;
    hasConflict: boolean;
    details: ConflictDetails | null;
  } | null>(null);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createMutation = useCreateSchedule();
  const updateMutation = useUpdateSchedule(scheduleToEdit?.id || "");
  const conflictMutation = useCheckConflict();

  const isEditing = Boolean(scheduleToEdit);

  useEffect(() => {
    if (scheduleToEdit) {
      setDayOfWeek(scheduleToEdit.day_of_week);
      setStartTime(scheduleToEdit.start_time.substring(0, 5));
      setEndTime(scheduleToEdit.end_time.substring(0, 5));
      setSlotDuration(
        scheduleToEdit.slot_duration_minutes
          ? String(scheduleToEdit.slot_duration_minutes)
          : String(scheduleToEdit.effective_slot_duration || defaultSlotDuration)
      );
      setBufferMinutes(scheduleToEdit.buffer_minutes || 0);
      setEffectiveFrom(scheduleToEdit.effective_from || "");
      setEffectiveUntil(scheduleToEdit.effective_until || "");
    } else {
      setDayOfWeek(defaultDay);
      setStartTime("09:00");
      setEndTime("13:00");
      setSlotDuration(String(defaultSlotDuration));
      setBufferMinutes(0);
      setEffectiveFrom("");
      setEffectiveUntil("");
    }
    setConflictResult(null);
    setErrorMessage(null);
  }, [scheduleToEdit, defaultDay, defaultSlotDuration, isOpen]);

  if (!isOpen) return null;

  const handleValidateConflict = async () => {
    setErrorMessage(null);
    try {
      const res = await conflictMutation.mutateAsync({
        doctor_clinic: doctorClinicId,
        day_of_week: dayOfWeek,
        start_time: startTime,
        end_time: endTime,
        buffer_minutes: bufferMinutes,
        exclude_schedule_id: scheduleToEdit?.id || null,
      });

      setConflictResult({
        checked: true,
        hasConflict: res.has_conflict,
        details: res.conflict,
      });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setErrorMessage(axiosErr.response?.data?.message || "Failed to check schedule conflicts.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (startTime >= endTime) {
      setErrorMessage("Shift start time must be strictly before shift end time.");
      return;
    }

    const durationNum = parseInt(slotDuration, 10);
    if (isNaN(durationNum) || durationNum < 5 || durationNum > 240) {
      setErrorMessage("Slot duration must be between 5 and 240 minutes.");
      return;
    }

    const payload: SchedulePayload = {
      doctor_clinic: doctorClinicId,
      day_of_week: dayOfWeek,
      start_time: startTime,
      end_time: endTime,
      slot_duration_minutes: durationNum,
      buffer_minutes: Number(bufferMinutes) || 0,
      effective_from: effectiveFrom || null,
      effective_until: effectiveUntil || null,
    };

    try {
      if (isEditing) {
        await updateMutation.mutateAsync(payload);
      } else {
        await createMutation.mutateAsync(payload);
      }
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: {
          status?: number;
          data?: {
            message?: string;
            conflict?: ConflictDetails;
            detail?: { message?: string; conflict?: ConflictDetails } | string;
            non_field_errors?: string[];
            end_time?: string[];
          };
        };
      };

      if (axiosErr.response?.status === 409) {
        const conflictData = axiosErr.response.data?.conflict || (
          typeof axiosErr.response.data?.detail === "object"
            ? axiosErr.response.data.detail.conflict
            : null
        );
        const msg = axiosErr.response.data?.message || (
          typeof axiosErr.response.data?.detail === "object"
            ? axiosErr.response.data.detail.message
            : axiosErr.response.data?.detail
        ) || "Schedule timing conflict detected.";

        setConflictResult({
          checked: true,
          hasConflict: true,
          details: conflictData || {
            conflict_type: "CROSS_CLINIC_OVERLAP",
            message: String(msg),
          },
        });
        setErrorMessage(String(msg));
      } else if (axiosErr.response?.data?.end_time) {
        setErrorMessage(axiosErr.response.data.end_time[0]);
      } else if (axiosErr.response?.data?.non_field_errors) {
        setErrorMessage(axiosErr.response.data.non_field_errors[0]);
      } else if (axiosErr.response?.data?.message) {
        setErrorMessage(axiosErr.response.data.message);
      } else {
        setErrorMessage("Failed to save schedule shift. Please try again.");
      }
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending || conflictMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-xl border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2 text-foreground">
              <Clock className="h-5 w-5 text-primary" />
              {isEditing ? "Edit Working Shift" : "Configure Doctor Working Shift"}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {doctorName ? `${doctorName} • ` : ""}
              {clinicName || "Clinic Operating Hours"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Global Error Banner */}
        {errorMessage && (
          <Alert variant="destructive" className="py-2.5">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-xs">{errorMessage}</AlertDescription>
          </Alert>
        )}

        {/* Real-time Conflict Validation Result */}
        {conflictResult && (
          <div>
            {conflictResult.hasConflict ? (
              <Alert className="border-red-500/30 bg-red-500/10 text-red-900 dark:text-red-200 py-2.5">
                <ShieldAlert className="h-4 w-4 text-red-600 dark:text-red-400" />
                <AlertTitle className="text-xs font-semibold">
                  {conflictResult.details?.conflict_type === "TRAVEL_BUFFER_VIOLATION"
                    ? "Cross-Clinic Travel Buffer Required"
                    : "Schedule Conflict Detected"}
                </AlertTitle>
                <AlertDescription className="text-xs mt-1">
                  {conflictResult.details?.message}
                </AlertDescription>
              </Alert>
            ) : (
              <Alert className="border-emerald-500/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200 py-2.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <AlertTitle className="text-xs font-semibold">Timings Available!</AlertTitle>
                <AlertDescription className="text-xs mt-0.5">
                  No overlapping shifts or travel buffer conflicts detected across any affiliated clinics.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Day of Week */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Day of Week</Label>
            <div className="grid grid-cols-7 gap-1.5">
              {([0, 1, 2, 3, 4, 5, 6] as WeekdayNumber[]).map((day) => {
                const isSelected = dayOfWeek === day;
                return (
                  <button
                    key={day}
                    type="button"
                    onClick={() => {
                      setDayOfWeek(day);
                      setConflictResult(null);
                    }}
                    className={`py-2 px-1 rounded-lg text-xs font-semibold text-center transition-all ${
                      isSelected
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {WEEKDAY_LABELS[day].substring(0, 3)}
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Selected: <strong>{WEEKDAY_LABELS[dayOfWeek]}</strong>
            </p>
          </div>

          {/* Start and End Times */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="startTime" className="text-xs font-semibold">
                Shift Start Time
              </Label>
              <Input
                id="startTime"
                type="time"
                value={startTime}
                onChange={(e) => {
                  setStartTime(e.target.value);
                  setConflictResult(null);
                }}
                required
                className="h-9 text-xs"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="endTime" className="text-xs font-semibold">
                Shift End Time
              </Label>
              <Input
                id="endTime"
                type="time"
                value={endTime}
                onChange={(e) => {
                  setEndTime(e.target.value);
                  setConflictResult(null);
                }}
                required
                className="h-9 text-xs"
              />
            </div>
          </div>

          {/* Quick Shifts Helper */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-muted-foreground mr-1">Presets:</span>
            {[
              { label: "Morning (09:00 - 13:00)", s: "09:00", e: "13:00" },
              { label: "Afternoon (14:00 - 17:00)", s: "14:00", e: "17:00" },
              { label: "Evening (17:30 - 20:30)", s: "17:30", e: "20:30" },
            ].map((preset) => (
              <Button
                key={preset.label}
                type="button"
                variant="outline"
                size="sm"
                className="h-6 text-[10px] px-2"
                onClick={() => {
                  setStartTime(preset.s);
                  setEndTime(preset.e);
                  setConflictResult(null);
                }}
              >
                {preset.label}
              </Button>
            ))}
          </div>

          {/* Slot Duration & Travel Buffer */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="space-y-1.5">
              <Label htmlFor="slotDuration" className="text-xs font-semibold">
                Slot Duration (Minutes)
              </Label>
              <Input
                id="slotDuration"
                type="number"
                min={5}
                max={240}
                step={5}
                value={slotDuration}
                onChange={(e) => setSlotDuration(e.target.value)}
                className="h-9 text-xs"
              />
              <p className="text-[10px] text-muted-foreground">Default: 15 mins</p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="bufferMinutes" className="text-xs font-semibold">
                Travel / Buffer (Minutes)
              </Label>
              <Input
                id="bufferMinutes"
                type="number"
                min={0}
                max={120}
                step={5}
                value={bufferMinutes}
                onChange={(e) => {
                  setBufferMinutes(parseInt(e.target.value, 10) || 0);
                  setConflictResult(null);
                }}
                className="h-9 text-xs"
              />
              <p className="text-[10px] text-muted-foreground">Gap before/after clinic</p>
            </div>
          </div>

          {/* Effective Validity Dates */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="space-y-1.5">
              <Label htmlFor="effectiveFrom" className="text-xs font-medium text-muted-foreground">
                Effective From (Optional)
              </Label>
              <Input
                id="effectiveFrom"
                type="date"
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
                className="h-9 text-xs"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="effectiveUntil" className="text-xs font-medium text-muted-foreground">
                Effective Until (Optional)
              </Label>
              <Input
                id="effectiveUntil"
                type="date"
                value={effectiveUntil}
                onChange={(e) => setEffectiveUntil(e.target.value)}
                className="h-9 text-xs"
              />
            </div>
          </div>

          {/* Dry Run Conflict Pre-check Button */}
          <div className="pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleValidateConflict}
              disabled={isPending}
              className="w-full text-xs h-8 gap-1.5"
            >
              {conflictMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5 text-primary" />
              )}
              Pre-check Multi-Clinic Timings & Travel Buffer
            </Button>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isPending}
              className="text-xs h-9"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isPending}
              className="text-xs h-9 gap-1.5 px-4"
            >
              {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isEditing ? "Save Shift Changes" : "Confirm Working Shift"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
