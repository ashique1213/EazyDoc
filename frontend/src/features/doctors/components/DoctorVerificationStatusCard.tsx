import React, { useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Edit3,
  FileCheck2,
  FileText,
  Loader2,
  Send,
  ShieldAlert,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { Doctor, DoctorVerificationStatus } from "../types";
import { useSubmitDoctorVerification } from "../hooks";

interface DoctorVerificationStatusCardProps {
  doctor: Doctor;
  onRefresh?: () => void;
}

export const DoctorVerificationStatusCard: React.FC<DoctorVerificationStatusCardProps> = ({
  doctor,
  onRefresh,
}) => {
  const submitMutation = useSubmitDoctorVerification();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const getStatusBadge = (status: DoctorVerificationStatus) => {
    switch (status) {
      case "VERIFIED":
        return (
          <Badge className="bg-emerald-600/10 text-emerald-700 hover:bg-emerald-600/20 dark:text-emerald-400 border-emerald-500/20">
            <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
            Verified Practitioner
          </Badge>
        );
      case "PENDING":
        return (
          <Badge className="bg-amber-500/10 text-amber-700 hover:bg-amber-500/20 dark:text-amber-400 border-amber-500/20">
            <Clock className="mr-1 h-3.5 w-3.5" />
            Pending Verification Review
          </Badge>
        );
      case "REJECTED":
        return (
          <Badge variant="destructive" className="bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20">
            <AlertCircle className="mr-1 h-3.5 w-3.5" />
            Verification Rejected
          </Badge>
        );
      case "SUSPENDED":
        return (
          <Badge variant="destructive" className="bg-red-600/10 text-red-700 dark:text-red-400 border-red-600/20">
            <ShieldAlert className="mr-1 h-3.5 w-3.5" />
            Practitioner Suspended
          </Badge>
        );
      case "DRAFT":
      default:
        return (
          <Badge variant="secondary" className="bg-slate-500/10 text-slate-700 dark:text-slate-400 border-slate-500/20">
            <FileText className="mr-1 h-3.5 w-3.5" />
            Draft — Not Submitted
          </Badge>
        );
    }
  };

  const handleSubmitForVerification = async () => {
    setErrorMessage(null);
    try {
      await submitMutation.mutateAsync();
      onRefresh?.();
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as { message?: string } | undefined;
        setErrorMessage(data?.message || "Failed to submit profile for verification. Please try again.");
      } else {
        setErrorMessage("Failed to submit profile for verification. Please try again.");
      }
    }
  };

  const canSubmit =
    doctor.verification_status === "DRAFT" || doctor.verification_status === "REJECTED";

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle className="text-xl">Medical Registration Status</CardTitle>
            <CardDescription>
              Review the current verification state of your clinical qualifications and council license.
            </CardDescription>
          </div>
          <div>{getStatusBadge(doctor.verification_status)}</div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {errorMessage && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Submission Error</AlertTitle>
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        )}

        {/* Status explanation alert boxes */}
        {doctor.verification_status === "DRAFT" && (
          <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertTitle>Profile Incomplete / Draft</AlertTitle>
            <AlertDescription className="text-xs">
              Your profile is currently saved in draft state. Make sure your registration number,
              council, and qualifications are accurate, attach supporting certificates, and submit
              for Super Admin review.
            </AlertDescription>
          </Alert>
        )}

        {doctor.verification_status === "PENDING" && (
          <Alert className="border-blue-500/30 bg-blue-500/10 text-blue-800 dark:text-blue-300">
            <Clock className="h-4 w-4 text-blue-600" />
            <AlertTitle>Awaiting Administrative Verification</AlertTitle>
            <AlertDescription className="text-xs">
              Your medical registration credentials were submitted on{" "}
              {doctor.submitted_at
                ? new Date(doctor.submitted_at).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "recently"}
              . Our clinical compliance administrators are reviewing your council records.
            </AlertDescription>
          </Alert>
        )}

        {doctor.verification_status === "VERIFIED" && (
          <Alert className="border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <AlertTitle>Registration Verified & Active</AlertTitle>
            <AlertDescription className="text-xs">
              Your medical registration is officially verified. You are eligible to be invited by
              clinics and manage appointments across practice locations.
            </AlertDescription>
          </Alert>
        )}

        {doctor.verification_status === "REJECTED" && (
          <Alert variant="destructive" className="border-rose-500/40 bg-rose-500/10">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Verification Request Rejected</AlertTitle>
            <AlertDescription className="space-y-2 text-xs">
              <p>
                <strong>Admin Reason:</strong>{" "}
                {doctor.verification_notes || "Required verification credentials could not be validated."}
              </p>
              <p>
                Please correct your details or upload updated certificates, then resubmit your profile.
              </p>
            </AlertDescription>
          </Alert>
        )}

        {doctor.verification_status === "SUSPENDED" && (
          <Alert variant="destructive" className="border-red-600/40 bg-red-600/10">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>Practitioner License Suspended</AlertTitle>
            <AlertDescription className="space-y-2 text-xs">
              <p>
                <strong>Suspension Notice:</strong>{" "}
                {doctor.verification_notes || "Your practice license has been suspended by administration."}
              </p>
              <p>
                Please contact support or the compliance administrator for dispute resolution.
              </p>
            </AlertDescription>
          </Alert>
        )}

        {/* Submitted Identity Details */}
        <div className="rounded-xl border bg-muted/20 p-4 space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <h4 className="text-sm font-semibold flex items-center gap-2">
              <FileCheck2 className="h-4 w-4 text-primary" />
              Registered Identity Summary
            </h4>
            <Link to="/doctor/profile">
              <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs">
                <Edit3 className="h-3.5 w-3.5" />
                Edit Profile
              </Button>
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 text-xs">
            <div>
              <span className="text-muted-foreground">Practitioner Name:</span>
              <p className="font-semibold text-foreground">{doctor.full_name}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Specialization:</span>
              <p className="font-semibold text-foreground">{doctor.specialization}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Registration Number:</span>
              <p className="font-semibold font-mono text-foreground">{doctor.registration_number}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Issuing Council:</span>
              <p className="font-semibold text-foreground">{doctor.registration_council}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Qualifications:</span>
              <p className="font-semibold text-foreground">{doctor.qualifications}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Experience:</span>
              <p className="font-semibold text-foreground">{doctor.years_of_experience} years</p>
            </div>
          </div>
        </div>

        {/* Action button */}
        {canSubmit && (
          <div className="flex justify-end pt-2">
            <Button
              onClick={handleSubmitForVerification}
              disabled={submitMutation.isPending}
              className="gap-2"
            >
              {submitMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {doctor.verification_status === "REJECTED"
                ? "Resubmit Profile for Verification"
                : "Submit Profile for Verification"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
