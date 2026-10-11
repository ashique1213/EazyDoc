import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Send, CheckCircle2, AlertTriangle, Clock, AlertOctagon, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ClinicForm,
  ClinicStatusBadge,
  useClinic,
  useSubmitClinic,
  useUpdateClinic,
} from "@/features/clinics";
import type { ClinicUpdatePayload } from "@/features/clinics";

export function ClinicDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: clinic, isLoading, isError, refetch } = useClinic(id);
  const updateMutation = useUpdateClinic(id || "");
  const submitMutation = useSubmitClinic(id || "");

  const [serverErrors, setServerErrors] = useState<Record<string, string[] | string> | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !clinic) {
    return (
      <Card className="max-w-xl mx-auto p-8 text-center border-dashed">
        <p className="text-sm text-destructive">Clinic not found or you lack permission to view it.</p>
        <Link to="/clinic/my-clinics" className="mt-4 inline-block">
          <Button variant="outline" size="sm">Back to My Clinics</Button>
        </Link>
      </Card>
    );
  }

  const handleUpdate = async (data: ClinicUpdatePayload) => {
    setServerErrors(null);
    setSuccessMessage(null);
    try {
      await updateMutation.mutateAsync(data);
      setSuccessMessage("Clinic profile updated successfully.");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { errors?: Record<string, string[]>; message?: string } } };
      if (axiosErr.response?.data?.errors) {
        setServerErrors(axiosErr.response.data.errors);
      } else if (axiosErr.response?.data?.message) {
        setServerErrors({ non_field_errors: axiosErr.response.data.message });
      }
    }
  };

  const handleSubmitForVerification = async () => {
    setServerErrors(null);
    setSuccessMessage(null);
    try {
      await submitMutation.mutateAsync();
      setSuccessMessage("Clinic submitted for Super Admin verification!");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      if (axiosErr.response?.data?.message) {
        setServerErrors({ non_field_errors: axiosErr.response.data.message });
      }
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Link to="/clinic/my-clinics">
              <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground">
                <ArrowLeft className="h-4 w-4 mr-1" /> My Clinics
              </Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight">{clinic.name}</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Establishment Slug: <span className="font-mono text-foreground font-medium">/{clinic.slug}</span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <ClinicStatusBadge status={clinic.status} />

          {(clinic.status === "DRAFT" || clinic.status === "REJECTED") && (
            <Button
              size="sm"
              onClick={handleSubmitForVerification}
              disabled={submitMutation.isPending}
              className="gap-1.5 shadow-sm"
            >
              {submitMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {clinic.status === "REJECTED" ? "Resubmit for Approval" : "Submit for Verification"}
            </Button>
          )}
        </div>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 p-3.5 text-xs text-emerald-800 dark:text-emerald-300 flex items-center space-x-2 animate-in fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span className="font-medium">{successMessage}</span>
        </div>
      )}

      {/* Status Advisory Banner */}
      {clinic.status === "REJECTED" && (
        <Card className="border-rose-200 dark:border-rose-900 bg-rose-50/50 dark:bg-rose-950/20">
          <CardContent className="p-4 flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-rose-900 dark:text-rose-200">
                Clinic Verification Rejected
              </h4>
              <p className="text-xs text-rose-800 dark:text-rose-300">
                Reason from Super Admin: <span className="font-semibold italic">{clinic.verification_notes || "Missing verification credentials."}</span>
              </p>
              <p className="text-[11px] text-muted-foreground pt-1">
                Please correct the information in the form below and click "Resubmit for Approval".
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {clinic.status === "PENDING" && (
        <Card className="border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/20">
          <CardContent className="p-4 flex items-start space-x-3">
            <Clock className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">
                Submission Under Review
              </h4>
              <p className="text-xs text-amber-800 dark:text-amber-300">
                Your clinic information has been queued for Super Admin compliance and credential check. You will be notified when your clinic is approved.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {clinic.status === "APPROVED" && (
        <Card className="border-emerald-200 dark:border-emerald-900 bg-emerald-50/40 dark:bg-emerald-950/20">
          <CardContent className="p-4 flex items-start space-x-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">
                Verified & Publicly Discoverable
              </h4>
              <p className="text-xs text-emerald-800 dark:text-emerald-300">
                Approved by {clinic.approved_by ? `${clinic.approved_by.first_name} ${clinic.approved_by.last_name}` : "Super Admin"} on{" "}
                {clinic.approved_at ? new Date(clinic.approved_at).toLocaleDateString() : "platform record"}. Patients can discover this establishment.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {clinic.status === "SUSPENDED" && (
        <Card className="border-orange-200 dark:border-orange-900 bg-orange-50/50 dark:bg-orange-950/20">
          <CardContent className="p-4 flex items-start space-x-3">
            <AlertOctagon className="h-5 w-5 text-orange-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-orange-900 dark:text-orange-200">
                Establishment Suspended
              </h4>
              <p className="text-xs text-orange-800 dark:text-orange-300">
                Reason: {clinic.verification_notes || "Administrative hold applied."}
              </p>
              <p className="text-[11px] text-muted-foreground pt-1">
                This clinic cannot accept new patient bookings. Please reach out to administrative support.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Profile Edit Form */}
      <ClinicForm
        initialData={clinic}
        onSubmit={handleUpdate}
        isSubmitting={updateMutation.isPending}
        serverErrors={serverErrors}
        mode="edit"
      />
    </div>
  );
}

export default ClinicDetailPage;
