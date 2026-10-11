import { Link } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CalendarCheck,
  CheckCircle2,
  Clock,
  Edit3,
  FileText,
  ShieldCheck,
  Stethoscope,
  UserPlus,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useDoctorMe } from "@/features/doctors";

export function DoctorPage() {
  const { data: doctor, isLoading } = useDoctorMe();

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Doctor Practice Suite</h1>
          <p className="text-sm text-muted-foreground">
            Global practitioner dashboard across all your affiliated clinics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {doctor ? (
            <>
              <Link to="/doctor/profile">
                <Button variant="outline" size="sm" className="gap-1.5 text-xs">
                  <Edit3 className="h-3.5 w-3.5" />
                  Edit Profile
                </Button>
              </Link>
              <Link to="/doctor/verification">
                <Button size="sm" className="gap-1.5 text-xs">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Verification
                </Button>
              </Link>
            </>
          ) : (
            <Link to="/doctor/profile">
              <Button size="sm" className="gap-1.5 text-xs">
                <UserPlus className="h-3.5 w-3.5" />
                Setup Profile
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Verification Status Banner */}
      {!isLoading && (
        <>
          {!doctor ? (
            <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <AlertTitle className="text-sm font-semibold">Doctor Profile Incomplete</AlertTitle>
              <AlertDescription className="text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mt-1">
                <span>
                  Please complete your doctor profile and medical council registration number to submit for verification.
                </span>
                <Link to="/doctor/profile">
                  <Button size="sm" variant="outline" className="h-7 text-xs gap-1">
                    Complete Profile <ArrowRight className="h-3 w-3" />
                  </Button>
                </Link>
              </AlertDescription>
            </Alert>
          ) : doctor.verification_status === "PENDING" ? (
            <Alert className="border-blue-500/30 bg-blue-500/10 text-blue-800 dark:text-blue-300">
              <Clock className="h-4 w-4 text-blue-600" />
              <AlertTitle className="text-sm font-semibold">Verification Pending Review</AlertTitle>
              <AlertDescription className="text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mt-1">
                <span>
                  Your medical registration ({doctor.registration_number}) is currently under review by Super Administration.
                </span>
                <Link to="/doctor/verification">
                  <Button size="sm" variant="outline" className="h-7 text-xs gap-1">
                    View Status <ArrowRight className="h-3 w-3" />
                  </Button>
                </Link>
              </AlertDescription>
            </Alert>
          ) : doctor.verification_status === "REJECTED" ? (
            <Alert variant="destructive" className="border-rose-500/40 bg-rose-500/10">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle className="text-sm font-semibold">Verification Action Required</AlertTitle>
              <AlertDescription className="text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mt-1">
                <span>
                  Your profile was returned for corrections: {doctor.verification_notes || "Please check details."}
                </span>
                <Link to="/doctor/verification">
                  <Button size="sm" variant="destructive" className="h-7 text-xs gap-1">
                    Correct & Resubmit <ArrowRight className="h-3 w-3" />
                  </Button>
                </Link>
              </AlertDescription>
            </Alert>
          ) : doctor.verification_status === "VERIFIED" ? (
            <Alert className="border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <AlertTitle className="text-sm font-semibold">
                Verified Practitioner — {doctor.full_name} ({doctor.specialization})
              </AlertTitle>
              <AlertDescription className="text-xs mt-1">
                Registered with {doctor.registration_council} (Reg: {doctor.registration_number}). Your credentials are active.
              </AlertDescription>
            </Alert>
          ) : null}
        </>
      )}

      {/* Metrics Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Affiliated Clinics</CardTitle>
            <Stethoscope className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Connected practices</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Today's Schedule</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Total appointments</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CalendarCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Consultations finished</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Prescriptions</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Issued digital Rx</p>
          </CardContent>
        </Card>
      </div>

      {/* Overview Quick Links */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Doctor Profile & Medical Registration</CardTitle>
            <CardDescription className="text-xs">
              Manage your personal practice identity, qualifications, languages, and biography.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/doctor/profile">
              <Button variant="outline" size="sm" className="text-xs gap-1.5">
                <Edit3 className="h-3.5 w-3.5" />
                Manage Profile Details
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Registration Evidence & Verification</CardTitle>
            <CardDescription className="text-xs">
              Upload registration certificates, degree proofs, and track council verification review.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/doctor/verification">
              <Button variant="outline" size="sm" className="text-xs gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5" />
                View Verification Status
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default DoctorPage;
