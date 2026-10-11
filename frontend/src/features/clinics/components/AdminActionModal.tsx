import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { AlertTriangle, Loader2, X } from "lucide-react";

interface AdminActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason?: string) => Promise<void> | void;
  title: string;
  description: string;
  actionType: "approve" | "reject" | "suspend" | "reactivate";
  isLoading?: boolean;
}

export function AdminActionModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  actionType,
  isLoading = false,
}: AdminActionModalProps) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const requiresReason = actionType === "reject" || actionType === "suspend";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (requiresReason) {
      if (!reason.trim()) {
        setError("A reason is strictly required for this administrative action.");
        return;
      }
      if (reason.trim().length < 5) {
        setError("Please enter a clear explanation (minimum 5 characters).");
        return;
      }
    }
    setError(null);
    await onConfirm(reason.trim());
  };

  const getButtonVariant = () => {
    switch (actionType) {
      case "reject":
      case "suspend":
        return "destructive";
      default:
        return "default";
    }
  };

  const getButtonLabel = () => {
    switch (actionType) {
      case "approve":
        return "Confirm Approval";
      case "reject":
        return "Confirm Rejection";
      case "suspend":
        return "Suspend Clinic";
      case "reactivate":
        return "Reactivate Clinic";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-xl border bg-card p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          disabled={isLoading}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-start space-x-3 mb-4">
          <div className={`p-2.5 rounded-full ${actionType === "reject" || actionType === "suspend" ? "bg-rose-100 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400" : "bg-primary/10 text-primary"}`}>
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">{title}</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {requiresReason && (
            <div className="space-y-2">
              <Label htmlFor="admin-reason">
                {actionType === "reject" ? "Reason for Rejection *" : "Reason for Suspension *"}
              </Label>
              <Textarea
                id="admin-reason"
                rows={4}
                value={reason}
                onChange={(e) => {
                  setReason(e.target.value);
                  if (error) setError(null);
                }}
                placeholder={
                  actionType === "reject"
                    ? "Explain missing licenses, incorrect address, or policy violations so the owner can correct them..."
                    : "Specify the reason for suspension (e.g. license expiration, safety investigation)..."
                }
                className="resize-none text-sm"
                disabled={isLoading}
              />
              {error && <p className="text-xs font-medium text-destructive">{error}</p>}
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-2 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant={getButtonVariant()}
              size="sm"
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {getButtonLabel()}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
