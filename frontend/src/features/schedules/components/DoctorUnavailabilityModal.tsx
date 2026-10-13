import React, { useState } from "react";
import {
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  UserX,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type {
  UnavailabilityPayload,
  UnavailabilityReason,
} from "../types";
import {
  useCreateUnavailability,
  useDeleteUnavailability,
  useDoctorUnavailabilities,
} from "../hooks";

interface DoctorUnavailabilityModalProps {
  isOpen: boolean;
  onClose: () => void;
  doctorId?: string;
  clinicId?: string;
  doctorName?: string;
  isDoctorRole?: boolean;
}

export const DoctorUnavailabilityModal: React.FC<DoctorUnavailabilityModalProps> = ({
  isOpen,
  onClose,
  doctorId,
  clinicId,
  doctorName,
  isDoctorRole = false,
}) => {
  const { data: unavailabilities, isLoading, refetch } = useDoctorUnavailabilities({
    doctor_id: doctorId,
    clinic_id: isDoctorRole ? undefined : clinicId,
  });

  const createMutation = useCreateUnavailability();
  const deleteMutation = useDeleteUnavailability();

  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState("18:00");
  const [reason, setReason] = useState<UnavailabilityReason>("PERSONAL");
  const [notes, setNotes] = useState("");
  const [applyGlobally, setApplyGlobally] = useState(!clinicId || isDoctorRole);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!startDate || !endDate) {
      setErrorMessage("Both start and end dates are required.");
      return;
    }

    const startIso = new Date(`${startDate}T${startTime}:00`).toISOString();
    const endIso = new Date(`${endDate}T${endTime}:00`).toISOString();

    if (new Date(startIso) >= new Date(endIso)) {
      setErrorMessage("End datetime must be strictly after start datetime.");
      return;
    }

    const payload: UnavailabilityPayload = {
      doctor: doctorId,
      clinic: applyGlobally ? null : (clinicId || null),
      start_datetime: startIso,
      end_datetime: endIso,
      reason,
      notes,
    };

    try {
      await createMutation.mutateAsync(payload);
      refetch();
      // Reset form
      setStartDate("");
      setEndDate("");
      setNotes("");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string; end_datetime?: string[] } } };
      if (axiosErr.response?.data?.end_datetime) {
        setErrorMessage(axiosErr.response.data.end_datetime[0]);
      } else if (axiosErr.response?.data?.message) {
        setErrorMessage(axiosErr.response.data.message);
      } else {
        setErrorMessage("Failed to record leave period.");
      }
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to cancel this leave period?")) {
      await deleteMutation.mutateAsync(id);
      refetch();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl rounded-xl border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2 text-foreground">
              <UserX className="h-5 w-5 text-amber-600" />
              Doctor Leaves & Time-Off Management
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {doctorName ? `${doctorName} • ` : ""}
              Record sick leave, vacation, emergency closures, or conferences. Slots during leaves are automatically blocked.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {errorMessage && (
          <Alert variant="destructive" className="py-2.5">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-xs">{errorMessage}</AlertDescription>
          </Alert>
        )}

        {/* Create Leave Form */}
        <form onSubmit={handleSubmit} className="rounded-xl border bg-muted/20 p-4 space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
            <Plus className="h-3.5 w-3.5 text-primary" />
            Record New Leave Period
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Start Datetime */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Start Date & Time</Label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                  className="h-8 text-xs"
                />
                <Input
                  type="time"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  required
                  className="h-8 text-xs"
                />
              </div>
            </div>

            {/* End Datetime */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">End Date & Time</Label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  required
                  className="h-8 text-xs"
                />
                <Input
                  type="time"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  required
                  className="h-8 text-xs"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Reason */}
            <div className="space-y-1.5">
              <Label htmlFor="leaveReason" className="text-xs font-semibold">
                Reason for Leave
              </Label>
              <select
                id="leaveReason"
                value={reason}
                onChange={(e) => setReason(e.target.value as UnavailabilityReason)}
                className="w-full h-8 rounded-md border border-input bg-background px-2.5 py-1 text-xs text-foreground focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="SICK_LEAVE">Sick Leave</option>
                <option value="PERSONAL">Personal Leave / Vacation</option>
                <option value="EMERGENCY">Emergency</option>
                <option value="CONFERENCE">Medical Conference</option>
                <option value="CLINIC_CLOSURE">Clinic Closure / Maintenance</option>
                <option value="OTHER">Other</option>
              </select>
            </div>

            {/* Scope */}
            {isDoctorRole && clinicId && (
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">Affiliation Scope</Label>
                <div className="flex items-center gap-3 pt-1.5">
                  <label className="flex items-center gap-1.5 text-xs text-foreground cursor-pointer">
                    <input
                      type="radio"
                      checked={applyGlobally}
                      onChange={() => setApplyGlobally(true)}
                    />
                    All Affiliated Clinics
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-foreground cursor-pointer">
                    <input
                      type="radio"
                      checked={!applyGlobally}
                      onChange={() => setApplyGlobally(false)}
                    />
                    This Clinic Only
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="leaveNotes" className="text-xs font-medium text-muted-foreground">
              Internal Notes (Optional)
            </Label>
            <Input
              id="leaveNotes"
              type="text"
              placeholder="e.g. Attending Annual Cardiology Summit"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="h-8 text-xs"
            />
          </div>

          <div className="flex justify-end pt-1">
            <Button
              type="submit"
              size="sm"
              disabled={createMutation.isPending}
              className="text-xs h-8 gap-1.5"
            >
              {createMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Save Leave Period
            </Button>
          </div>
        </form>

        {/* Existing Leaves List */}
        <div className="space-y-3 pt-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
            Scheduled Doctor Leaves ({unavailabilities?.length || 0})
          </h3>

          {isLoading ? (
            <div className="py-6 text-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mx-auto" />
            </div>
          ) : unavailabilities && unavailabilities.length > 0 ? (
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {unavailabilities.map((u) => {
                const sDate = new Date(u.start_datetime).toLocaleDateString();
                const sTime = new Date(u.start_datetime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                const eDate = new Date(u.end_datetime).toLocaleDateString();
                const eTime = new Date(u.end_datetime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

                return (
                  <div
                    key={u.id}
                    className="flex items-center justify-between p-3 rounded-lg border bg-card text-xs hover:border-border/80 transition-all"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px] py-0 h-4.5 bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30">
                          {u.reason_display}
                        </Badge>
                        <span className="font-semibold text-foreground">
                          {sDate} {sTime} – {eDate} {eTime}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Scope: {u.clinic_name ? u.clinic_name : "All Affiliated Clinics"}
                        {u.notes ? ` • "${u.notes}"` : ""}
                      </p>
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(u.id)}
                      disabled={deleteMutation.isPending}
                      className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10"
                      title="Cancel Leave"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground border rounded-lg border-dashed text-xs">
              No leave periods recorded for this doctor.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-3 border-t">
          <Button size="sm" variant="outline" onClick={onClose} className="text-xs h-8">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};
