import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle2, Loader2, Settings, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { DoctorClinic } from "../types";
import { useUpdateClinicDoctorSettings } from "../hooks";

interface ClinicDoctorSettingsModalProps {
  clinicId: string;
  association: DoctorClinic | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const ClinicDoctorSettingsModal: React.FC<ClinicDoctorSettingsModalProps> = ({
  clinicId,
  association,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [consultationFee, setConsultationFee] = useState("0.00");
  const [followUpFee, setFollowUpFee] = useState("0.00");
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const updateMutation = useUpdateClinicDoctorSettings(clinicId);

  useEffect(() => {
    if (association) {
      setConsultationFee(association.consultation_fee || "0.00");
      setFollowUpFee(association.follow_up_fee || "0.00");
      setDurationMinutes(association.appointment_duration_minutes || 15);
      setErrorMsg(null);
    }
  }, [association]);

  if (!isOpen || !association) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const feeNum = parseFloat(consultationFee);
    if (isNaN(feeNum) || feeNum < 0) {
      setErrorMsg("Consultation fee must be a valid non-negative amount.");
      return;
    }

    const followUpNum = parseFloat(followUpFee);
    if (isNaN(followUpNum) || followUpNum < 0) {
      setErrorMsg("Follow-up fee must be a valid non-negative amount.");
      return;
    }

    if (durationMinutes < 5 || durationMinutes > 240) {
      setErrorMsg("Appointment slot duration must be between 5 and 240 minutes.");
      return;
    }

    try {
      await updateMutation.mutateAsync({
        associationId: association.id,
        payload: {
          consultation_fee: consultationFee,
          follow_up_fee: followUpFee,
          appointment_duration_minutes: durationMinutes,
        },
      });
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setErrorMsg(axiosErr.response?.data?.message || "Failed to update doctor settings. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-2xl bg-card border shadow-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b">
          <div className="space-y-0.5">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Settings className="h-4 w-4 text-primary" />
              Configure Doctor Practice Terms
            </h3>
            <p className="text-xs text-muted-foreground">
              {association.doctor.full_name} ({association.doctor.specialization})
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 text-muted-foreground hover:text-foreground rounded-full"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {errorMsg && (
          <Alert variant="destructive" className="py-2.5 px-3 text-xs">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{errorMsg}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="editFee" className="text-xs font-semibold">
              In-Clinic Consultation Fee (₹) <span className="text-destructive">*</span>
            </Label>
            <Input
              id="editFee"
              type="number"
              min="0"
              step="10"
              value={consultationFee}
              onChange={(e) => setConsultationFee(e.target.value)}
              className="h-9 text-xs"
              required
            />
            <p className="text-[11px] text-muted-foreground">
              Independent rate configured exclusively for this clinic facility.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="editFollowUp" className="text-xs font-semibold">
              Follow-up Consultation Fee (₹)
            </Label>
            <Input
              id="editFollowUp"
              type="number"
              min="0"
              step="10"
              value={followUpFee}
              onChange={(e) => setFollowUpFee(e.target.value)}
              className="h-9 text-xs"
            />
            <p className="text-[11px] text-muted-foreground">
              Reduced rate for patient review visits within valid follow-up window.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="editDuration" className="text-xs font-semibold">
              Appointment Slot Duration (Minutes) <span className="text-destructive">*</span>
            </Label>
            <Input
              id="editDuration"
              type="number"
              min="5"
              max="240"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 15)}
              className="h-9 text-xs"
              required
            />
            <p className="text-[11px] text-muted-foreground">
              Standard booking interval for scheduling patient visits (5 to 240 mins).
            </p>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={updateMutation.isPending}
              className="text-xs h-9"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={updateMutation.isPending}
              className="text-xs h-9 gap-1.5"
            >
              {updateMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5" />
              )}
              Save Configuration
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
