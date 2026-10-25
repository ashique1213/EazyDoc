import { Link } from "react-router-dom";
import { Stethoscope, AlertTriangle, ArrowLeft } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ClinicSwitcher, useActiveClinic } from "@/features/clinicOperations";
import { ClinicDoctorsSection } from "@/features/doctorClinics";

export function ClinicDoctorsPage() {
  const { activeClinic, activeClinicId, isLoading: isLoadingClinic } = useActiveClinic();

  if (isLoadingClinic) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!activeClinic) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">Clinic Doctors</h1>
        </div>
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            No clinic selected or you do not have permission to manage clinics.
          </CardContent>
        </Card>
      </div>
    );
  }

  const isApproved = activeClinic.status === "APPROVED";

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              to="/clinic/dashboard"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              <ArrowLeft className="h-3 w-3" /> Dashboard
            </Link>
            <span className="text-xs text-muted-foreground">/</span>
            <span className="text-xs font-medium text-foreground">Doctors & Practitioners</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Stethoscope className="h-6 w-6 text-primary" />
              Doctor Management
            </h1>
            <Badge variant={isApproved ? "default" : "outline"} className="capitalize">
              {activeClinic.status.toLowerCase()}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Manage associated medical practitioners, configure fees, and coordinate availability for{" "}
            <span className="font-semibold text-foreground">{activeClinic.name}</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <ClinicSwitcher />
        </div>
      </div>

      {!isApproved && (
        <Card className="border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-900/50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
            <p className="text-sm text-amber-800 dark:text-amber-300">
              This clinic is currently <strong>{activeClinic.status}</strong>. Doctors can only be invited and accept associations once the clinic has been officially approved by platform administrators.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Main Doctors Section Component */}
      <Card>
        <CardContent className="p-6">
          <ClinicDoctorsSection
            clinicId={activeClinicId}
            isClinicApproved={isApproved}
          />
        </CardContent>
      </Card>
    </div>
  );
}
