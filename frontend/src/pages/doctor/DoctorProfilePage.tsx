import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DoctorProfileForm,
  DoctorDocumentManager,
  useDoctorMe,
} from "@/features/doctors";

export const DoctorProfilePage: React.FC = () => {
  const { data: doctor, isLoading, refetch } = useDoctorMe();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/doctor">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Doctor Profile</h1>
            <p className="text-sm text-muted-foreground">
              Manage your personal practice details, medical credentials, and council records.
            </p>
          </div>
        </div>

        {doctor && (
          <Link to="/doctor/verification">
            <Button variant="outline" size="sm" className="gap-2 text-xs">
              <ShieldCheck className="h-3.5 w-3.5 text-primary" />
              Verification Status
            </Button>
          </Link>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center p-12 text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Loading profile...
        </div>
      ) : (
        <div className="space-y-6">
          <DoctorProfileForm initialDoctor={doctor} onSuccess={() => refetch()} />
          {doctor && <DoctorDocumentManager />}
        </div>
      )}
    </div>
  );
};

export default DoctorProfilePage;
