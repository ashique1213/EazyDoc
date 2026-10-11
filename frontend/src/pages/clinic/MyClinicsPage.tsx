import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Building2, Clock, CheckCircle2, AlertOctagon, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ClinicCard, useMyClinics, useSubmitClinic } from "@/features/clinics";

export function MyClinicsPage() {
  const { data: clinics, isLoading, isError, refetch } = useMyClinics();
  const [submittingClinicId, setSubmittingClinicId] = useState<string | null>(null);

  const submitMutation = useSubmitClinic(submittingClinicId || "");

  const handleSubmitForVerification = async (id: string) => {
    setSubmittingClinicId(id);
    try {
      await submitMutation.mutateAsync();
      refetch();
    } finally {
      setSubmittingClinicId(null);
    }
  };

  const total = clinics?.length || 0;
  const approved = clinics?.filter((c) => c.status === "APPROVED").length || 0;
  const pending = clinics?.filter((c) => c.status === "PENDING").length || 0;
  const draftOrRejected = clinics?.filter((c) => c.status === "DRAFT" || c.status === "REJECTED").length || 0;

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Clinics</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage your registered medical centers, practice locations, and verification submissions.
          </p>
        </div>
        <Link to="/clinic/register">
          <Button className="gap-1.5 shadow-sm">
            <Plus className="h-4 w-4" />
            Register New Clinic
          </Button>
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
        <Card className="border bg-card/60">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Total Establishments</p>
              <h3 className="text-2xl font-bold mt-1 text-foreground">{total}</h3>
            </div>
            <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
              <Building2 className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border bg-card/60">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Active & Bookable</p>
              <h3 className="text-2xl font-bold mt-1 text-emerald-600">{approved}</h3>
            </div>
            <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-600">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border bg-card/60">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Pending Review</p>
              <h3 className="text-2xl font-bold mt-1 text-amber-600">{pending}</h3>
            </div>
            <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-600">
              <Clock className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border bg-card/60">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Drafts & Needs Attention</p>
              <h3 className="text-2xl font-bold mt-1 text-slate-600 dark:text-slate-300">{draftOrRejected}</h3>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-500/10 text-slate-600 dark:text-slate-300">
              <AlertOctagon className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : isError ? (
        <Card className="p-8 text-center border-dashed">
          <p className="text-sm text-destructive">Failed to load clinics. Please check your connection.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-4">
            Retry
          </Button>
        </Card>
      ) : clinics && clinics.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {clinics.map((clinic) => (
            <ClinicCard
              key={clinic.id}
              clinic={clinic}
              onSubmitForVerification={handleSubmitForVerification}
              isSubmitting={submittingClinicId === clinic.id}
            />
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center border-dashed bg-card/40">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-4">
            <Sparkles className="h-7 w-7" />
          </div>
          <h3 className="text-lg font-bold text-foreground">No Clinics Registered Yet</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1 mb-6">
            Get started by registering your first clinic facility. Once verified by Super Admin, you can affiliate doctors and accept patient bookings.
          </p>
          <Link to="/clinic/register">
            <Button className="gap-1.5">
              <Plus className="h-4 w-4" />
              Register Your First Clinic
            </Button>
          </Link>
        </Card>
      )}
    </div>
  );
}

export default MyClinicsPage;
