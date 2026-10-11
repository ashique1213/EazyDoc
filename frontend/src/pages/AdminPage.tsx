import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Building2, UserCheck, Percent, ArrowUpRight, Stethoscope } from "lucide-react";
import { useAdminClinics } from "@/features/clinics";
import { useAdminDoctors } from "@/features/doctors";

export function AdminPage() {
  const { data: pendingClinicsData } = useAdminClinics({ status: "PENDING" });
  const pendingClinicsCount = pendingClinicsData?.count ?? 0;

  const { data: pendingDoctorsData } = useAdminDoctors({ status: "PENDING" });
  const pendingDoctorsCount = pendingDoctorsData?.count ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Super Admin Platform Controls</h1>
          <p className="text-sm text-muted-foreground">
            Platform-level oversight, clinic verifications, doctor credentialing, and commission controls.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/admin/clinics">
            <Badge variant="outline" className="cursor-pointer hover:bg-accent gap-1">
              Clinics <ArrowUpRight className="h-3 w-3" />
            </Badge>
          </Link>
          <Link to="/admin/doctors">
            <Badge variant="outline" className="cursor-pointer hover:bg-accent gap-1">
              Doctors <ArrowUpRight className="h-3 w-3" />
            </Badge>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Link to="/admin/clinics">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Pending Clinics</CardTitle>
              <Building2 className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-amber-600">{pendingClinicsCount}</div>
              <p className="text-xs text-muted-foreground">Awaiting establishment check</p>
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/doctors">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Pending Doctors</CardTitle>
              <UserCheck className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-amber-600">{pendingDoctorsCount}</div>
              <p className="text-xs text-muted-foreground">Registration verification</p>
            </CardContent>
          </Card>
        </Link>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Commission Rate</CardTitle>
            <Percent className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5.0%</div>
            <p className="text-xs text-muted-foreground">Default platform rate</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">System Audit</CardTitle>
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Active</div>
            <p className="text-xs text-muted-foreground">Immutable audit logs</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              Clinic Facilities Oversight
            </CardTitle>
            <CardDescription className="text-xs">
              Review new healthcare establishment registrations, licenses, addresses, and operating parameters.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/admin/clinics">
              <Button variant="outline" size="sm" className="text-xs gap-1.5">
                Open Clinics Directory <ArrowUpRight className="h-3 w-3" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Stethoscope className="h-4 w-4 text-primary" />
              Doctor Credentials Verification
            </CardTitle>
            <CardDescription className="text-xs">
              Verify practitioner medical council registrations, qualifications, and manage suspension disputes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/admin/doctors">
              <Button variant="outline" size="sm" className="text-xs gap-1.5">
                Open Doctors Oversight <ArrowUpRight className="h-3 w-3" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default AdminPage;
