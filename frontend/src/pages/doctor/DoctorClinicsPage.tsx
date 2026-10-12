import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  Clock,
  IndianRupee,
  Loader2,
  MapPin,
  Phone,
  RefreshCw,
  Stethoscope,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  DoctorClinicStatusBadge,
  useAcceptClinicInvitation,
  useDoctorClinicInvitations,
  useDoctorClinics,
  useRejectClinicInvitation,
} from "@/features/doctorClinics";
import type { DoctorClinic } from "@/features/doctorClinics";

export const DoctorClinicsPage: React.FC = () => {
  const {
    data: invitations,
    isLoading: isInvitationsLoading,
    refetch: refetchInvitations,
  } = useDoctorClinicInvitations();

  const {
    data: allAssociations,
    isLoading: isAssociationsLoading,
    refetch: refetchAssociations,
  } = useDoctorClinics();

  const acceptMutation = useAcceptClinicInvitation();
  const rejectMutation = useRejectClinicInvitation();

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const activeAssociations = allAssociations?.filter((a) => a.status === "ACTIVE") || [];
  const pastAssociations = allAssociations?.filter(
    (a) => a.status === "REMOVED" || a.status === "REJECTED"
  ) || [];

  const handleAccept = async (association: DoctorClinic) => {
    setActionSuccess(null);
    setActionError(null);
    try {
      await acceptMutation.mutateAsync(association.id);
      setActionSuccess(`Successfully accepted affiliation with ${association.clinic.name}!`);
      refetchInvitations();
      refetchAssociations();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setActionError(axiosErr.response?.data?.message || "Failed to accept clinic invitation.");
    }
  };

  const handleReject = async (association: DoctorClinic) => {
    setActionSuccess(null);
    setActionError(null);
    try {
      await rejectMutation.mutateAsync(association.id);
      setActionSuccess(`Declined affiliation invitation from ${association.clinic.name}.`);
      refetchInvitations();
      refetchAssociations();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setActionError(axiosErr.response?.data?.message || "Failed to decline clinic invitation.");
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Link to="/doctor">
              <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground">
                <ArrowLeft className="h-4 w-4 mr-1" /> Practice Suite
              </Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight">Affiliated Clinics & Practice Network</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Manage your affiliations across multiple clinics. Each clinic maintains independent consultation fees and appointment slots.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            refetchInvitations();
            refetchAssociations();
          }}
          className="text-xs gap-1.5 h-8"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh Network
        </Button>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <Alert className="border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <AlertTitle className="text-xs font-semibold">Action Completed</AlertTitle>
          <AlertDescription className="text-xs">{actionSuccess}</AlertDescription>
        </Alert>
      )}

      {actionError && (
        <Alert variant="destructive" className="text-xs">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle className="text-xs font-semibold">Operation Failed</AlertTitle>
          <AlertDescription className="text-xs">{actionError}</AlertDescription>
        </Alert>
      )}

      {/* Section 1: Pending Clinic Invitations */}
      <Card className="border-blue-500/20 bg-blue-500/5 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/15 text-blue-600">
                <Clock className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base">Pending Clinic Invitations</CardTitle>
                <CardDescription className="text-xs">
                  Healthcare establishments inviting you to practice at their facilities.
                </CardDescription>
              </div>
            </div>
            {invitations && invitations.length > 0 && (
              <Badge className="bg-blue-600 text-white font-semibold">
                {invitations.length} New
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isInvitationsLoading ? (
            <div className="flex h-24 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : !invitations || invitations.length === 0 ? (
            <div className="py-6 text-center text-xs text-muted-foreground">
              No pending clinic invitations at this time. Clinics can invite you using your verified registration number.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {invitations.map((inv) => (
                <div
                  key={inv.id}
                  className="rounded-xl border bg-card p-4 shadow-sm space-y-3.5 flex flex-col justify-between"
                >
                  <div className="space-y-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-sm">
                          <Building2 className="h-5 w-5" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-foreground">
                            {inv.clinic.name}
                          </h4>
                          <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {inv.clinic.city}, {inv.clinic.state}
                          </p>
                        </div>
                      </div>
                      <DoctorClinicStatusBadge status={inv.status} />
                    </div>

                    {inv.invitation_message && (
                      <div className="rounded-lg bg-muted/40 p-2.5 text-[11px] text-muted-foreground italic border-l-2 border-primary">
                        "{inv.invitation_message}"
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t">
                      <div>
                        <span className="text-muted-foreground">Consultation Fee:</span>
                        <p className="font-semibold text-foreground flex items-center gap-0.5 mt-0.5">
                          <IndianRupee className="h-3 w-3" />
                          {parseFloat(inv.consultation_fee).toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Slot Duration:</span>
                        <p className="font-semibold text-foreground flex items-center gap-0.5 mt-0.5">
                          <Clock className="h-3 w-3" />
                          {inv.appointment_duration_minutes} mins
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReject(inv)}
                      disabled={rejectMutation.isPending || acceptMutation.isPending}
                      className="text-xs h-8 text-destructive hover:bg-destructive/10"
                    >
                      <XCircle className="h-3.5 w-3.5 mr-1" /> Decline
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleAccept(inv)}
                      disabled={acceptMutation.isPending || rejectMutation.isPending}
                      className="text-xs h-8 gap-1 shadow-sm"
                    >
                      {acceptMutation.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      )}
                      Accept Invitation
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 2: Active Clinic Affiliations */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-600">
                <Stethoscope className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base">Active Clinic Associations</CardTitle>
                <CardDescription className="text-xs">
                  Establishments where your practice is active and publicly available for patient booking.
                </CardDescription>
              </div>
            </div>
            <Badge variant="outline" className="text-xs font-semibold">
              {activeAssociations.length} Active
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {isAssociationsLoading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : activeAssociations.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground border border-dashed rounded-xl p-6">
              You are not currently affiliated with any active clinics. Accept an invitation above or contact partner clinics with your medical registration details.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {activeAssociations.map((assoc) => (
                <div
                  key={assoc.id}
                  className="rounded-xl border bg-card p-4 shadow-sm space-y-3 hover:border-primary/40 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-sm">
                        <Building2 className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-foreground">
                          {assoc.clinic.name}
                        </h4>
                        <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {assoc.clinic.address_line_1}, {assoc.clinic.city}
                        </p>
                      </div>
                    </div>
                    <DoctorClinicStatusBadge status={assoc.status} />
                  </div>

                  {/* Commercial Terms Banner */}
                  <div className="rounded-lg bg-muted/40 p-2.5 grid grid-cols-3 gap-2 text-center text-[11px]">
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Consultation Fee</span>
                      <strong className="text-foreground text-xs flex items-center justify-center gap-0.5 mt-0.5">
                        <IndianRupee className="h-3 w-3" />
                        {parseFloat(assoc.consultation_fee).toFixed(2)}
                      </strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Follow-Up Fee</span>
                      <strong className="text-foreground text-xs flex items-center justify-center gap-0.5 mt-0.5">
                        <IndianRupee className="h-3 w-3" />
                        {parseFloat(assoc.follow_up_fee).toFixed(2)}
                      </strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Slot Duration</span>
                      <strong className="text-foreground text-xs flex items-center justify-center gap-0.5 mt-0.5">
                        <Clock className="h-3 w-3" />
                        {assoc.appointment_duration_minutes}m
                      </strong>
                    </div>
                  </div>

                  {/* Contact & Meta */}
                  <div className="text-[11px] text-muted-foreground flex items-center justify-between pt-1 border-t">
                    <span className="flex items-center gap-1">
                      <Phone className="h-3 w-3" /> {assoc.clinic.phone}
                    </span>
                    <span>
                      Affiliated since{" "}
                      {assoc.accepted_at ? new Date(assoc.accepted_at).toLocaleDateString() : "recently"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 3: Inactive / Past Associations (if any) */}
      {pastAssociations.length > 0 && (
        <Card className="opacity-80">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Past / Inactive Affiliations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pastAssociations.map((assoc) => (
                <div
                  key={assoc.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-muted/20 text-xs"
                >
                  <div>
                    <span className="font-medium text-foreground">{assoc.clinic.name}</span>
                    <span className="text-muted-foreground ml-2">({assoc.clinic.city})</span>
                  </div>
                  <DoctorClinicStatusBadge status={assoc.status} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default DoctorClinicsPage;
