import React, { useState } from "react";
import {
  AlertCircle,
  Clock,
  Loader2,
  Search,
  Send,
  ShieldCheck,
  Stethoscope,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { lookupDoctorRegistration } from "@/features/doctors/api";
import type { DoctorRegistrationLookupResult } from "@/features/doctors/types";
import { useInviteDoctorToClinic } from "../hooks";

interface InviteDoctorModalProps {
  clinicId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const InviteDoctorModal: React.FC<InviteDoctorModalProps> = ({
  clinicId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  // Search state
  const [regNumber, setRegNumber] = useState("");
  const [council, setCouncil] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [lookupResult, setLookupResult] = useState<DoctorRegistrationLookupResult | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);

  // Form terms
  const [consultationFee, setConsultationFee] = useState("500.00");
  const [followUpFee, setFollowUpFee] = useState("250.00");
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [message, setMessage] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const inviteMutation = useInviteDoctorToClinic(clinicId);

  if (!isOpen) return null;

  const handleSearchDoctor = async (e: React.FormEvent) => {
    e.preventDefault();
    setLookupError(null);
    setLookupResult(null);
    setSubmitError(null);

    if (!regNumber.trim()) {
      setLookupError("Please enter the doctor's medical council registration number.");
      return;
    }

    setIsSearching(true);
    try {
      const result = await lookupDoctorRegistration(regNumber.trim(), council.trim() || undefined);
      setLookupResult(result);
      if (!result.found) {
        setLookupError(result.message || "No practitioner profile found with this registration number.");
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setLookupError(axiosErr.response?.data?.message || "Failed to look up doctor registration. Please check inputs.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleSendInvitation = async () => {
    if (!lookupResult?.found || !lookupResult.doctor_id) return;
    setSubmitError(null);

    const feeNum = parseFloat(consultationFee);
    if (isNaN(feeNum) || feeNum < 0) {
      setSubmitError("Consultation fee must be a valid non-negative amount.");
      return;
    }

    const followUpNum = parseFloat(followUpFee);
    if (isNaN(followUpNum) || followUpNum < 0) {
      setSubmitError("Follow-up fee must be a valid non-negative amount.");
      return;
    }

    if (durationMinutes < 5 || durationMinutes > 240) {
      setSubmitError("Appointment duration must be between 5 and 240 minutes.");
      return;
    }

    try {
      await inviteMutation.mutateAsync({
        doctor_id: lookupResult.doctor_id,
        consultation_fee: consultationFee,
        follow_up_fee: followUpFee,
        appointment_duration_minutes: durationMinutes,
        invitation_message: message.trim(),
      });
      onSuccess?.();
      handleClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setSubmitError(axiosErr.response?.data?.message || "Failed to issue invitation. Please verify eligibility.");
    }
  };

  const handleClose = () => {
    setRegNumber("");
    setCouncil("");
    setLookupResult(null);
    setLookupError(null);
    setSubmitError(null);
    setMessage("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl bg-card border shadow-2xl p-6 sm:p-7 space-y-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Stethoscope className="h-5 w-5 text-primary" />
              Invite Doctor to Clinic
            </h3>
            <p className="text-xs text-muted-foreground">
              Verify credentials via Medical Council registration before sending an affiliation request.
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClose}
            className="h-8 w-8 text-muted-foreground hover:text-foreground rounded-full"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Step 1: Doctor Lookup Form */}
        <form onSubmit={handleSearchDoctor} className="space-y-3.5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="regNumber" className="text-xs font-semibold">
                Medical Registration Number <span className="text-destructive">*</span>
              </Label>
              <Input
                id="regNumber"
                placeholder="e.g. MMC-112233"
                value={regNumber}
                onChange={(e) => setRegNumber(e.target.value)}
                className="h-9 text-xs"
                disabled={isSearching}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="council" className="text-xs font-semibold">
                Medical Council (Optional)
              </Label>
              <Input
                id="council"
                placeholder="e.g. Maharashtra Medical Council"
                value={council}
                onChange={(e) => setCouncil(e.target.value)}
                className="h-9 text-xs"
                disabled={isSearching}
              />
            </div>
          </div>

          <Button
            type="submit"
            size="sm"
            variant="secondary"
            disabled={isSearching || !regNumber.trim()}
            className="w-full text-xs gap-1.5 h-8 font-medium"
          >
            {isSearching ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Search className="h-3.5 w-3.5" />
            )}
            Search Verified Practitioners
          </Button>
        </form>

        {/* Lookup Feedback / Error */}
        {lookupError && (
          <Alert variant="destructive" className="py-2.5 px-3 text-xs">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{lookupError}</AlertDescription>
          </Alert>
        )}

        {/* Doctor Found Card */}
        {lookupResult?.found && (
          <div className="rounded-xl border bg-muted/30 p-4 space-y-3 animate-in fade-in">
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-sm font-bold text-foreground">
                  {lookupResult.full_name}
                </h4>
                <p className="text-xs font-medium text-primary">
                  {lookupResult.specialization}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Reg: <span className="font-mono text-foreground font-medium">{lookupResult.registration_number}</span> ({lookupResult.registration_council})
                </p>
              </div>

              {lookupResult.is_verified ? (
                <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 text-[11px]">
                  <ShieldCheck className="h-3 w-3 mr-1" />
                  Verified Doctor
                </Badge>
              ) : (
                <Badge variant="outline" className="text-[11px] text-amber-600 border-amber-400/30">
                  <Clock className="h-3 w-3 mr-1" />
                  Not Verified
                </Badge>
              )}
            </div>

            {!lookupResult.is_eligible_for_invitation && (
              <Alert variant="destructive" className="py-2 px-3 text-xs">
                <AlertCircle className="h-3.5 w-3.5" />
                <AlertDescription>
                  This practitioner is not currently eligible to associate with clinics. They must have a verified and active profile.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Step 2: Clinic-Specific Commercial Terms (Only if doctor is eligible) */}
        {lookupResult?.found && lookupResult.is_eligible_for_invitation && (
          <div className="space-y-4 pt-2 border-t">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Clinic Commercial & Appointment Terms
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="fee" className="text-xs font-semibold">
                  Consultation Fee (₹) <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="fee"
                  type="number"
                  min="0"
                  step="10"
                  value={consultationFee}
                  onChange={(e) => setConsultationFee(e.target.value)}
                  className="h-9 text-xs"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="followUp" className="text-xs font-semibold">
                  Follow-up Fee (₹)
                </Label>
                <Input
                  id="followUp"
                  type="number"
                  min="0"
                  step="10"
                  value={followUpFee}
                  onChange={(e) => setFollowUpFee(e.target.value)}
                  className="h-9 text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="duration" className="text-xs font-semibold">
                  Slot Duration (Min) <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="duration"
                  type="number"
                  min="5"
                  max="240"
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 15)}
                  className="h-9 text-xs"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="invMsg" className="text-xs font-semibold">
                Invitation Message / Note (Optional)
              </Label>
              <Textarea
                id="invMsg"
                rows={2}
                placeholder="e.g. We would be delighted to have you lead cardiology consultations at our Apollo facility."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="text-xs resize-none"
                maxLength={500}
              />
            </div>

            {submitError && (
              <Alert variant="destructive" className="py-2.5 px-3 text-xs">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{submitError}</AlertDescription>
              </Alert>
            )}

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <Button variant="outline" size="sm" onClick={handleClose} disabled={inviteMutation.isPending} className="text-xs h-9">
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSendInvitation}
                disabled={inviteMutation.isPending}
                className="text-xs h-9 gap-1.5 shadow-sm"
              >
                {inviteMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Send className="h-3.5 w-3.5" />
                )}
                Send Affiliation Invitation
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
