import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  FileCheck2,
  FileText,
  Loader2,
  ShieldAlert,
  UserCheck,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AdminDoctorActionDialog,
  useAdminDoctor,
  type AdminActionType,
  type DoctorVerificationStatus,
} from "@/features/doctors";

export const AdminDoctorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: doctor, isLoading, isError, refetch } = useAdminDoctor(id);

  const [actionType, setActionType] = useState<AdminActionType>(null);
  const [isDialogOpen, setIsDialogOpen] = useState<boolean>(false);

  const openAction = (type: AdminActionType) => {
    setActionType(type);
    setIsDialogOpen(true);
  };

  const getStatusBadge = (status: DoctorVerificationStatus) => {
    switch (status) {
      case "VERIFIED":
        return (
          <Badge className="bg-emerald-600/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
            <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
            Verified Practitioner
          </Badge>
        );
      case "PENDING":
        return (
          <Badge className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20">
            <Clock className="mr-1 h-3.5 w-3.5" />
            Pending Verification Review
          </Badge>
        );
      case "REJECTED":
        return (
          <Badge variant="destructive" className="bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20">
            <XCircle className="mr-1 h-3.5 w-3.5" />
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
            Draft Submission
          </Badge>
        );
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-20 text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading doctor verification records...
      </div>
    );
  }

  if (isError || !doctor) {
    return (
      <div className="max-w-2xl mx-auto space-y-4 p-8 text-center">
        <Alert variant="destructive">
          <AlertTitle>Not Found</AlertTitle>
          <AlertDescription>The requested doctor profile could not be found.</AlertDescription>
        </Alert>
        <Link to="/admin/doctors">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Doctors Oversight
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/admin/doctors">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">{doctor.full_name}</h1>
              {getStatusBadge(doctor.verification_status)}
            </div>
            <p className="text-xs text-muted-foreground">
              Doctor ID: <span className="font-mono">{doctor.id}</span> • Registered on{" "}
              {new Date(doctor.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {doctor.verification_status === "PENDING" && (
            <>
              <Button
                variant="default"
                size="sm"
                onClick={() => openAction("VERIFY")}
                className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
              >
                <CheckCircle2 className="h-4 w-4" />
                Approve & Verify
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => openAction("REJECT")}
                className="gap-1.5"
              >
                <XCircle className="h-4 w-4" />
                Reject Profile
              </Button>
            </>
          )}

          {doctor.verification_status === "VERIFIED" && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => openAction("SUSPEND")}
              className="gap-1.5"
            >
              <ShieldAlert className="h-4 w-4" />
              Suspend Practitioner
            </Button>
          )}

          {doctor.verification_status === "SUSPENDED" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => openAction("REACTIVATE")}
              className="border-blue-500/40 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/30 gap-1.5"
            >
              <CheckCircle2 className="h-4 w-4" />
              Reactivate Practitioner
            </Button>
          )}
        </div>
      </div>

      {/* Verification Notes / Rejection Alert */}
      {doctor.verification_notes && (
        <Alert
          className={
            doctor.verification_status === "REJECTED"
              ? "border-rose-500/40 bg-rose-500/10 text-rose-800 dark:text-rose-300"
              : doctor.verification_status === "SUSPENDED"
              ? "border-red-600/40 bg-red-600/10 text-red-800 dark:text-red-300"
              : "border-blue-500/30 bg-blue-500/10 text-blue-800 dark:text-blue-300"
          }
        >
          <AlertTitle className="text-xs font-semibold">
            {doctor.verification_status === "REJECTED"
              ? "Rejection Reason Provided"
              : doctor.verification_status === "SUSPENDED"
              ? "Suspension Justification"
              : "Administrative Notes"}
          </AlertTitle>
          <AlertDescription className="text-xs pt-1">{doctor.verification_notes}</AlertDescription>
        </Alert>
      )}

      {/* Grid: Credentials & Medical Registration Details */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Medical Authority & License */}
        <Card className="shadow-sm">
          <CardHeader className="pb-3 border-b">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileCheck2 className="h-4 w-4 text-primary" />
              Medical Council & Registration
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Registration Number:</span>
              <span className="font-mono font-bold text-foreground">
                {doctor.registration_number}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Normalized Identifier:</span>
              <span className="font-mono text-muted-foreground">
                {doctor.normalized_registration_number || doctor.registration_number}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Issuing Medical Council:</span>
              <span className="font-semibold text-foreground">{doctor.registration_council}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">State / Jurisdiction:</span>
              <span className="text-foreground">{doctor.registration_state || "—"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Primary Specialization:</span>
              <span className="font-semibold text-foreground">{doctor.specialization}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Qualifications:</span>
              <span className="text-foreground">{doctor.qualifications}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Clinical Experience:</span>
              <span className="text-foreground">{doctor.years_of_experience} years</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Languages:</span>
              <span className="text-foreground">{doctor.languages || "English"}</span>
            </div>
          </CardContent>
        </Card>

        {/* User Account & Verification Audit */}
        <Card className="shadow-sm">
          <CardHeader className="pb-3 border-b">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-primary" />
              User Account & Verification Audit
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Account Email:</span>
              <span className="font-medium text-foreground">{doctor.user?.email}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Account User ID:</span>
              <span className="font-mono text-muted-foreground">{doctor.user?.id}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Clinic Eligible:</span>
              <span className="font-medium text-foreground">
                {doctor.is_eligible_for_clinics ? "Yes (Active & Verified)" : "No"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Submission Date:</span>
              <span className="text-foreground">
                {doctor.submitted_at
                  ? new Date(doctor.submitted_at).toLocaleString()
                  : "Not yet submitted"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Last Verified / Reviewed:</span>
              <span className="text-foreground">
                {doctor.verified_at ? new Date(doctor.verified_at).toLocaleString() : "—"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <span className="text-muted-foreground">Reviewed By Admin:</span>
              <span className="text-foreground">
                {doctor.verified_by
                  ? `${doctor.verified_by.first_name} ${doctor.verified_by.last_name} (${doctor.verified_by.email})`
                  : "—"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Biography */}
      {doctor.bio && (
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Professional Biography</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground leading-relaxed">
            {doctor.bio}
          </CardContent>
        </Card>
      )}

      {/* Verification Evidence Documents */}
      <Card className="shadow-sm">
        <CardHeader className="pb-3 border-b">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-semibold">
                Uploaded Verification Evidence ({doctor.documents?.length || 0})
              </CardTitle>
              <CardDescription className="text-xs">
                Private documents submitted by practitioner for credential verification.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {!doctor.documents || doctor.documents.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">
              No private verification documents were uploaded by this practitioner.
            </p>
          ) : (
            <div className="divide-y rounded-lg border">
              {doctor.documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-3 text-xs hover:bg-muted/20"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-primary shrink-0" />
                    <div>
                      <p className="font-semibold text-foreground">{doc.file_name}</p>
                      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                        <Badge variant="outline" className="text-[10px] py-0">
                          {doc.document_type_display}
                        </Badge>
                        <span>{(doc.file_size / (1024 * 1024)).toFixed(2)} MB</span>
                        <span>•</span>
                        <span>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-[10px]">
                    Private Evidence
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Action Dialog */}
      <AdminDoctorActionDialog
        doctor={doctor}
        actionType={actionType}
        isOpen={isDialogOpen}
        onClose={() => {
          setIsDialogOpen(false);
          setActionType(null);
        }}
        onSuccess={() => refetch()}
      />
    </div>
  );
};

export default AdminDoctorDetailPage;
