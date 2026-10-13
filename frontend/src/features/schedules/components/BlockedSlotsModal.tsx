import React, { useState } from "react";
import {
  AlertCircle,
  Ban,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type { BlockedSlotPayload } from "../types";
import {
  useBlockedSlots,
  useCreateBlockedSlot,
  useDeleteBlockedSlot,
} from "../hooks";

interface BlockedSlotsModalProps {
  isOpen: boolean;
  onClose: () => void;
  doctorClinicId: string;
  doctorName?: string;
  clinicName?: string;
}

export const BlockedSlotsModal: React.FC<BlockedSlotsModalProps> = ({
  isOpen,
  onClose,
  doctorClinicId,
  doctorName,
  clinicName,
}) => {
  const { data: blockedSlots, isLoading, refetch } = useBlockedSlots({
    doctor_clinic_id: doctorClinicId,
  });

  const createMutation = useCreateBlockedSlot();
  const deleteMutation = useDeleteBlockedSlot();

  const [date, setDate] = useState("");
  const [startTime, setStartTime] = useState("10:00");
  const [endTime, setEndTime] = useState("10:15");
  const [reason, setReason] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!date) {
      setErrorMessage("Date is required.");
      return;
    }

    const payload: BlockedSlotPayload = {
      doctor_clinic: doctorClinicId,
      date,
      start_time: startTime,
      end_time: endTime || undefined,
      reason: reason || "Administrative Hold",
    };

    try {
      await createMutation.mutateAsync(payload);
      refetch();
      setDate("");
      setReason("");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setErrorMessage(axiosErr.response?.data?.message || "Failed to block slot. Slot might already be blocked.");
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to unblock this slot?")) {
      await deleteMutation.mutateAsync(id);
      refetch();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-xl border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2 text-foreground">
              <Ban className="h-5 w-5 text-rose-600" />
              Administrative Blocked Slots
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {doctorName ? `${doctorName} • ` : ""}
              {clinicName || "Clinic"}
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

        {/* Create Form */}
        <form onSubmit={handleSubmit} className="rounded-xl border bg-muted/20 p-4 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
            <Plus className="h-3.5 w-3.5 text-primary" />
            Block Individual Time Slot
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Date</Label>
              <Input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="h-8 text-xs"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Start Time</Label>
              <Input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                required
                className="h-8 text-xs"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">End Time</Label>
              <Input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="h-8 text-xs"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Reason for Block</Label>
            <Input
              type="text"
              placeholder="e.g. VIP patient reservation, Equipment sanitization"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
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
              Block Slot
            </Button>
          </div>
        </form>

        {/* Existing Blocked Slots */}
        <div className="space-y-3 pt-1">
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
            Current Blocked Slots ({blockedSlots?.length || 0})
          </h3>

          {isLoading ? (
            <div className="py-6 text-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mx-auto" />
            </div>
          ) : blockedSlots && blockedSlots.length > 0 ? (
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {blockedSlots.map((b) => (
                <div
                  key={b.id}
                  className="flex items-center justify-between p-2.5 rounded-lg border bg-card text-xs hover:border-border/80 transition-all"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px] py-0 h-4.5 border-rose-500/30 text-rose-700 dark:text-rose-300 bg-rose-500/10">
                        {b.date}
                      </Badge>
                      <span className="font-semibold text-foreground">
                        {b.start_time.substring(0, 5)} {b.end_time ? `– ${b.end_time.substring(0, 5)}` : ""}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Reason: {b.reason || "Administrative Hold"}
                    </p>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(b.id)}
                    disabled={deleteMutation.isPending}
                    className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10"
                    title="Unblock Slot"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground border rounded-lg border-dashed text-xs">
              No blocked slots recorded for this affiliation.
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
