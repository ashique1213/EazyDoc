import React, { useState } from "react";
import axios from "axios";
import { AlertCircle, CheckCircle2, Loader2, ShieldAlert, X, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { Doctor } from "../types";
import {
  useAdminVerifyDoctor,
  useAdminRejectDoctor,
  useAdminSuspendDoctor,
  useAdminReactivateDoctor,
} from "../hooks";

export type AdminActionType = "VERIFY" | "REJECT" | "SUSPEND" | "REACTIVATE" | null;

interface AdminDoctorActionDialogProps {
  doctor: Doctor | null;
  actionType: AdminActionType;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const AdminDoctorActionDialog: React.FC<AdminDoctorActionDialogProps> = ({
  doctor,
  actionType,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [reason, setReason] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const verifyMutation = useAdminVerifyDoctor();
  const rejectMutation = useAdminRejectDoctor();
  const suspendMutation = useAdminSuspendDoctor();
  const reactivateMutation = useAdminReactivateDoctor();

  if (!isOpen || !doctor || !actionType) return null;

  const handleAction = async () => {
    setErrorMsg(null);

    if ((actionType === "REJECT" || actionType === "SUSPEND") && reason.trim().length < 5) {
      setErrorMsg("A detailed reason of at least 5 characters is required.");
      return;
    }

    try {
      if (actionType === "VERIFY") {
        await verifyMutation.mutateAsync(doctor.id);
      } else if (actionType === "REJECT") {
        await rejectMutation.mutateAsync({ id: doctor.id, reason });
      } else if (actionType === "SUSPEND") {
        await suspendMutation.mutateAsync({ id: doctor.id, reason });
      } else if (actionType === "REACTIVATE") {
        await reactivateMutation.mutateAsync(doctor.id);
      }

      setReason("");
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as { message?: string } | undefined;
        setErrorMsg(data?.message || "An error occurred while processing the verification action.");
      } else {
        setErrorMsg("An unexpected error occurred.");
      }
    }
  };

  const isPending =
    verifyMutation.isPending ||
    rejectMutation.isPending ||
    suspendMutation.isPending ||
    reactivateMutation.isPending;

  const getTitle = () => {
    switch (actionType) {
      case "VERIFY":
        return `Approve & Verify: ${doctor.full_name}`;
      case "REJECT":
        return `Reject Verification: ${doctor.full_name}`;
      case "SUSPEND":
        return `Suspend Practitioner: ${doctor.full_name}`;
      case "REACTIVATE":
        return `Reactivate Practitioner: ${doctor.full_name}`;
    }
  };

  const getDescription = () => {
    switch (actionType) {
      case "VERIFY":
        return `This will approve the doctor's registration (${doctor.registration_number}) under ${doctor.registration_council}. The doctor will be eligible to accept clinic invitations.`;
      case "REJECT":
        return `This will reject the submission and notify the doctor with the reason provided below. The doctor will be able to correct their details and resubmit.`;
      case "SUSPEND":
        return `This will revoke the doctor's verified status and prevent new clinic affiliations or appointments. A clear administrative justification is required.`;
      case "REACTIVATE":
        return `This will reinstate the doctor's verified standing on the platform.`;
    }
  };

  const getConfirmButtonVariant = () => {
    if (actionType === "REJECT" || actionType === "SUSPEND") return "destructive";
    return "default";
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-xl border bg-card p-6 shadow-xl space-y-4 animate-in fade-in-0 zoom-in-95">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {actionType === "VERIFY" && <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
            {actionType === "REJECT" && <XCircle className="h-5 w-5 text-rose-600" />}
            {actionType === "SUSPEND" && <ShieldAlert className="h-5 w-5 text-red-600" />}
            {actionType === "REACTIVATE" && <CheckCircle2 className="h-5 w-5 text-blue-600" />}
            <h3 className="text-base font-semibold text-foreground">{getTitle()}</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-sm opacity-70 hover:opacity-100 transition-opacity"
            disabled={isPending}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="text-xs text-muted-foreground">{getDescription()}</p>

        {errorMsg && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-xs">{errorMsg}</AlertDescription>
          </Alert>
        )}

        {(actionType === "REJECT" || actionType === "SUSPEND") && (
          <div className="space-y-2 py-1">
            <Label htmlFor="admin_reason" className="text-xs">
              {actionType === "REJECT"
                ? "Rejection Reason & Required Corrections"
                : "Suspension Justification"}
              <span className="text-destructive"> *</span>
            </Label>
            <Textarea
              id="admin_reason"
              rows={4}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                actionType === "REJECT"
                  ? "e.g. The registration number does not match council records or certificate is illegible..."
                  : "e.g. License suspended by State Medical Council order pending inquiry..."
              }
              className="text-xs"
            />
            <p className="text-[11px] text-muted-foreground">Minimum 5 characters required.</p>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2 border-t">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            variant={getConfirmButtonVariant()}
            size="sm"
            onClick={handleAction}
            disabled={isPending}
          >
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {actionType === "VERIFY" && "Approve Doctor"}
            {actionType === "REJECT" && "Confirm Rejection"}
            {actionType === "SUSPEND" && "Confirm Suspension"}
            {actionType === "REACTIVATE" && "Reactivate Doctor"}
          </Button>
        </div>
      </div>
    </div>
  );
};
