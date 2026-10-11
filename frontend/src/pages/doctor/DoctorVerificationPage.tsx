import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Edit3, Loader2, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DoctorVerificationStatusCard,
  DoctorDocumentManager,
  useDoctorMe,
} from "@/features/doctors";

export const DoctorVerificationPage: React.FC = () => {
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
            <h1 className="text-2xl font-bold tracking-tight">Medical Verification</h1>
            <p className="text-sm text-muted-foreground">
              Official verification state of your medical council credentials and practice license.
            </p>
          </div>
        </div>

        {doctor && (
          <Link to="/doctor/profile">
            <Button variant="outline" size="sm" className="gap-2 text-xs">
              <Edit3 className="h-3.5 w-3.5" />
              Edit Profile
            </Button>
          </Link>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center p-12 text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Loading verification status...
        </div>
      ) : !doctor ? (
        <Card className="text-center p-8">
          <CardHeader>
            <CardTitle>Doctor Profile Not Found</CardTitle>
            <CardDescription>
              You need to complete your doctor profile and medical registration details before submitting for verification.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/doctor/profile">
              <Button className="gap-2">
                <PlusCircle className="h-4 w-4" />
                Create Doctor Profile
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <DoctorVerificationStatusCard doctor={doctor} onRefresh={() => refetch()} />
          <DoctorDocumentManager />
        </div>
      )}
    </div>
  );
};

export default DoctorVerificationPage;
