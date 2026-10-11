import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  RotateCcw,
  Building2,
  MapPin,
  Mail,
  Phone,
  Calendar,
  User,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AdminActionModal,
  ClinicStatusBadge,
  useAdminApproveClinic,
  useAdminClinic,
  useAdminReactivateClinic,
  useAdminRejectClinic,
  useAdminSuspendClinic,
} from "@/features/clinics";
import { useAuthStore } from "@/features/auth";

export function AdminClinicDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const { data: clinic, isLoading, isError, refetch } = useAdminClinic(id);

  const approveMutation = useAdminApproveClinic(id || "");
  const rejectMutation = useAdminRejectClinic(id || "");
  const suspendMutation = useAdminSuspendClinic(id || "");
  const reactivateMutation = useAdminReactivateClinic(id || "");

  // Modal states
  const [modalType, setModalType] = useState<"approve" | "reject" | "suspend" | "reactivate" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

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
        <p className="text-sm text-destructive">Failed to find clinic or Super Admin authorization is missing.</p>
        <Link to="/admin/clinics" className="mt-4 inline-block">
          <Button variant="outline" size="sm">Back to Clinics Oversight</Button>
        </Link>
      </Card>
    );
  }

  const isOwner = user?.id === clinic.owner.id;

  const handleConfirmAction = async (reason?: string) => {
    setActionError(null);
    setActionSuccess(null);

    try {
      if (modalType === "approve") {
        await approveMutation.mutateAsync();
        setActionSuccess(`Clinic "${clinic.name}" has been approved.`);
      } else if (modalType === "reject" && reason) {
        await rejectMutation.mutateAsync(reason);
        setActionSuccess(`Clinic "${clinic.name}" has been rejected.`);
      } else if (modalType === "suspend" && reason) {
        await suspendMutation.mutateAsync(reason);
        setActionSuccess(`Clinic "${clinic.name}" has been suspended.`);
      } else if (modalType === "reactivate") {
        await reactivateMutation.mutateAsync();
        setActionSuccess(`Clinic "${clinic.name}" has been reactivated.`);
      }
      setModalType(null);
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      setActionError(axiosErr.response?.data?.message || "Action failed. Please try again.");
    }
  };

  const isActionLoading =
    approveMutation.isPending ||
    rejectMutation.isPending ||
    suspendMutation.isPending ||
    reactivateMutation.isPending;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Top Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Link to="/admin/clinics">
              <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground">
                <ArrowLeft className="h-4 w-4 mr-1" /> All Clinics
              </Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight">{clinic.name}</h1>
          </div>
          <p className="text-xs text-muted-foreground font-mono">
            UUID: {clinic.id} &bull; Slug: /{clinic.slug}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <ClinicStatusBadge status={clinic.status} />
        </div>
      </div>

      {/* Action Messages */}
      {actionSuccess && (
        <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 p-3.5 text-xs text-emerald-800 dark:text-emerald-300 flex items-center space-x-2 animate-in fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span className="font-medium">{actionSuccess}</span>
        </div>
      )}

      {actionError && (
        <div className="rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 p-3.5 text-xs text-rose-800 dark:text-rose-300 flex items-center space-x-2 animate-in fade-in">
          <ShieldAlert className="h-4 w-4 shrink-0 text-rose-600" />
          <span className="font-medium">{actionError}</span>
        </div>
      )}

      {/* Admin Action Control Card */}
      <Card className="border bg-card shadow-sm">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm font-semibold flex items-center justify-between">
            <span>Administrative Verification Decision</span>
            <span className="text-xs font-normal text-muted-foreground">
              Current Status: <strong className="text-foreground">{clinic.status}</strong>
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1 max-w-xl text-xs text-muted-foreground">
              {clinic.status === "PENDING" && (
                <p>
                  This clinic is awaiting verification. Inspect establishment credentials, phone, address, and verify licensing compliance.
                </p>
              )}
              {clinic.status === "APPROVED" && (
                <p>
                  This clinic is verified, active, and publicly discoverable. Suspend only for compliance violations or license expiration.
                </p>
              )}
              {clinic.status === "REJECTED" && (
                <p>
                  This clinic was rejected. The owner must correct submitted information and resubmit before it can be verified.
                </p>
              )}
              {clinic.status === "SUSPENDED" && (
                <p>
                  This clinic is currently suspended and blocked from new appointments. Reactivate once compliance is confirmed.
                </p>
              )}
              {clinic.status === "DRAFT" && (
                <p>
                  This clinic is currently in DRAFT status and has not yet been submitted by the owner.
                </p>
              )}
              {isOwner && (
                <p className="text-amber-600 dark:text-amber-400 font-medium">
                  Notice: You are the owner of this clinic. In accordance with policy, clinic owners cannot approve their own clinic.
                </p>
              )}
            </div>

            {/* Decision Buttons */}
            <div className="flex items-center space-x-2 shrink-0">
              {clinic.status === "PENDING" && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-rose-600 border-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/40 gap-1.5"
                    onClick={() => setModalType("reject")}
                    disabled={isActionLoading}
                  >
                    <XCircle className="h-4 w-4" /> Reject with Reason
                  </Button>
                  <Button
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 shadow-sm"
                    onClick={() => setModalType("approve")}
                    disabled={isActionLoading || isOwner}
                    title={isOwner ? "Clinic owners cannot approve their own clinic" : undefined}
                  >
                    <CheckCircle2 className="h-4 w-4" /> Approve Clinic
                  </Button>
                </>
              )}

              {clinic.status === "APPROVED" && (
                <Button
                  size="sm"
                  variant="destructive"
                  className="gap-1.5"
                  onClick={() => setModalType("suspend")}
                  disabled={isActionLoading}
                >
                  <AlertOctagon className="h-4 w-4" /> Suspend Clinic
                </Button>
              )}

              {clinic.status === "SUSPENDED" && (
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                  onClick={() => setModalType("reactivate")}
                  disabled={isActionLoading}
                >
                  <RotateCcw className="h-4 w-4" /> Reactivate Clinic
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Two Column Layout: Clinic Profile Details */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Left Column: Establishment info */}
        <div className="space-y-6 md:col-span-2">
          <Card className="border">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-sm font-semibold flex items-center space-x-2">
                <Building2 className="h-4 w-4 text-primary" />
                <span>Establishment Profile</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5 space-y-4 text-xs">
              <div className="flex items-center space-x-4">
                {clinic.logo ? (
                  <img
                    src={clinic.logo}
                    alt={clinic.name}
                    className="h-20 w-20 rounded-xl border object-cover shadow-sm"
                  />
                ) : (
                  <div className="flex h-20 w-20 items-center justify-center rounded-xl border border-dashed bg-muted/40 text-muted-foreground">
                    <Building2 className="h-8 w-8" />
                  </div>
                )}
                <div>
                  <h3 className="text-base font-bold text-foreground">{clinic.name}</h3>
                  <p className="text-muted-foreground mt-0.5">/{clinic.slug}</p>
                  <p className="text-muted-foreground mt-1 text-[11px]">
                    Timezone: <span className="font-medium text-foreground">{clinic.timezone}</span>
                  </p>
                </div>
              </div>

              {clinic.description && (
                <div className="pt-2 border-t">
                  <span className="font-semibold text-foreground">About / Description:</span>
                  <p className="mt-1 text-muted-foreground leading-relaxed whitespace-pre-line">
                    {clinic.description}
                  </p>
                </div>
              )}

              <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t">
                <div>
                  <span className="font-semibold text-foreground flex items-center space-x-1.5 mb-1">
                    <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>Official Email:</span>
                  </span>
                  <p className="text-muted-foreground font-mono">{clinic.email}</p>
                </div>
                <div>
                  <span className="font-semibold text-foreground flex items-center space-x-1.5 mb-1">
                    <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>Official Phone:</span>
                  </span>
                  <p className="text-muted-foreground font-mono">{clinic.phone}</p>
                </div>
              </div>

              <div className="pt-2 border-t">
                <span className="font-semibold text-foreground flex items-center space-x-1.5 mb-1">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>Physical Address:</span>
                </span>
                <p className="text-muted-foreground">
                  {clinic.address_line_1}
                  {clinic.address_line_2 ? `, ${clinic.address_line_2}` : ""}
                  <br />
                  {clinic.city}, {clinic.state} — {clinic.pincode}
                  <br />
                  {clinic.country}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Owner & Audit Metadata */}
        <div className="space-y-6">
          {/* Owner Details */}
          <Card className="border">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-sm font-semibold flex items-center space-x-2">
                <User className="h-4 w-4 text-primary" />
                <span>Clinic Owner</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5 space-y-3 text-xs">
              <div>
                <p className="text-muted-foreground">Owner Name</p>
                <p className="font-semibold text-foreground mt-0.5">
                  {clinic.owner.first_name} {clinic.owner.last_name}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Owner Email</p>
                <p className="font-mono text-foreground mt-0.5">{clinic.owner.email}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Account Role</p>
                <p className="font-mono text-foreground mt-0.5">{clinic.owner.role}</p>
              </div>
            </CardContent>
          </Card>

          {/* Audit Trail */}
          <Card className="border">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-sm font-semibold flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-primary" />
                <span>Verification Audit</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5 space-y-3 text-xs">
              <div>
                <p className="text-muted-foreground">Registration Date</p>
                <p className="text-foreground mt-0.5">
                  {new Date(clinic.created_at).toLocaleString()}
                </p>
              </div>

              {clinic.approved_at && (
                <div>
                  <p className="text-muted-foreground">Approval Timestamp</p>
                  <p className="text-foreground mt-0.5">
                    {new Date(clinic.approved_at).toLocaleString()}
                  </p>
                </div>
              )}

              {clinic.approved_by && (
                <div>
                  <p className="text-muted-foreground">Approved By</p>
                  <p className="text-foreground mt-0.5">
                    {clinic.approved_by.first_name} {clinic.approved_by.last_name} ({clinic.approved_by.email})
                  </p>
                </div>
              )}

              {clinic.verification_notes && (
                <div className="pt-2 border-t">
                  <p className="text-muted-foreground font-semibold">Latest Verification Notes / Reason:</p>
                  <p className="mt-1 text-foreground italic bg-muted/30 p-2.5 rounded-lg border">
                    "{clinic.verification_notes}"
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Confirmation & Reason Modals */}
      <AdminActionModal
        isOpen={modalType !== null}
        onClose={() => setModalType(null)}
        onConfirm={handleConfirmAction}
        actionType={modalType || "approve"}
        title={
          modalType === "approve"
            ? `Approve "${clinic.name}"`
            : modalType === "reject"
            ? `Reject "${clinic.name}"`
            : modalType === "suspend"
            ? `Suspend "${clinic.name}"`
            : `Reactivate "${clinic.name}"`
        }
        description={
          modalType === "approve"
            ? "Are you sure you want to approve this clinic? Once approved, the clinic becomes publicly discoverable and can accept appointments."
            : modalType === "reject"
            ? "Please specify the exact reason for rejecting this clinic submission so the owner can correct their information."
            : modalType === "suspend"
            ? "Suspended clinics cannot accept new bookings. Specify the formal administrative reason."
            : "Reactivating will restore the clinic to APPROVED status and allow new patient bookings."
        }
        isLoading={isActionLoading}
      />
    </div>
  );
}

export default AdminClinicDetailPage;
