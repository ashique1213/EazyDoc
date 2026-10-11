import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ClinicForm, useCreateClinic } from "@/features/clinics";
import type { ClinicCreatePayload, ClinicUpdatePayload } from "@/features/clinics";

export function ClinicRegisterPage() {
  const navigate = useNavigate();
  const createClinicMutation = useCreateClinic();
  const [serverErrors, setServerErrors] = useState<Record<string, string[] | string> | null>(null);
  const [successClinic, setSuccessClinic] = useState<{ name: string; status: string } | null>(null);

  const handleSubmit = async (data: ClinicCreatePayload | ClinicUpdatePayload) => {
    setServerErrors(null);
    try {
      const created = await createClinicMutation.mutateAsync(data as ClinicCreatePayload);
      setSuccessClinic({ name: created.name, status: created.status });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { errors?: Record<string, string[]>; message?: string } } };
      if (axiosErr.response?.data?.errors) {
        setServerErrors(axiosErr.response.data.errors);
      } else if (axiosErr.response?.data?.message) {
        setServerErrors({ non_field_errors: axiosErr.response.data.message });
      } else {
        setServerErrors({ non_field_errors: "An unexpected error occurred. Please try again." });
      }
    }
  };

  if (successClinic) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-bold tracking-tight">Clinic Registered Successfully!</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            {successClinic.status === "PENDING"
              ? `Your clinic "${successClinic.name}" has been submitted to Super Admin for verification. You will be notified once approved.`
              : `Your clinic "${successClinic.name}" has been saved as a draft. You can complete its details and submit it whenever you are ready.`}
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-4">
          <Button onClick={() => navigate("/clinic/my-clinics")}>View My Clinics</Button>
          <Button variant="outline" onClick={() => setSuccessClinic(null)}>
            Register Another Clinic
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Link to="/clinic/my-clinics">
              <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground">
                <ArrowLeft className="h-4 w-4 mr-1" /> Back
              </Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight">Register New Clinic</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Complete the establishment details below. Submitted clinics undergo platform Super Admin verification.
          </p>
        </div>
      </div>

      <ClinicForm
        onSubmit={handleSubmit}
        isSubmitting={createClinicMutation.isPending}
        serverErrors={serverErrors}
        mode="create"
      />
    </div>
  );
}

export default ClinicRegisterPage;
