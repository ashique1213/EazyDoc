import React, { useState } from "react";
import { AlertCircle, AlertTriangle, Loader2, UserMinus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { DoctorClinic } from "../types";
import { useRemoveClinicDoctor } from "../hooks";

interface RemoveDoctorModalProps {
  clinicId: string;
  association: DoctorClinic | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const RemoveDoctorModal: React.FC<RemoveDoctorModalProps> = ({
  clinicId,
  association,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const removeMutation = useRemoveClinicDoctor(clinicId);

  if (!isOpen || !association) return null;

  const handleConfirm = async () => {
    setErrorMsg(null);
    try {
      await removeMutation.mutateAsync(association.id);
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setErrorMsg(axiosErr.response?.data?.message || "Failed to remove doctor association.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-2xl bg-card border shadow-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b">
          <div className="flex items-center gap-2.5 text-destructive">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">
                Remove Doctor from Clinic
              </h3>
              <p className="text-xs text-muted-foreground">Confirm association termination</p>
            </div>
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

        <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
          <p>
            Are you sure you want to remove{" "}
            <span className="font-semibold text-foreground">
              {association.doctor.full_name}
            </span>{" "}
            ({association.doctor.specialization}) from this clinic?
          </p>
          <div className="rounded-xl border bg-muted/40 p-3 space-y-1.5 text-[11px]">
            <p className="font-medium text-foreground">Multi-tenant Protection Notice:</p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>The doctor's global medical profile and verification remain active.</li>
              <li>Associations with other independent clinics are unaffected.</li>
              <li>You may safely re-invite this doctor in the future if needed.</li>
            </ul>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={removeMutation.isPending}
            className="text-xs h-9"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleConfirm}
            disabled={removeMutation.isPending}
            className="text-xs h-9 gap-1.5"
          >
            {removeMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <UserMinus className="h-3.5 w-3.5" />
            )}
            Confirm Removal
          </Button>
        </div>
      </div>
    </div>
  );
};
