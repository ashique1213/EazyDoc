import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Building2, Users, CalendarDays, DollarSign, Plus } from "lucide-react";

export function ClinicPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Clinic SaaS Dashboard</h1>
          <p className="text-sm text-muted-foreground">Manage your clinic, affiliated doctors, schedules, and reception queue.</p>
        </div>
        <div className="flex items-center space-x-2">
          <Link to="/clinic/my-clinics">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Building2 className="h-4 w-4" /> My Clinics
            </Button>
          </Link>
          <Link to="/clinic/register">
            <Button size="sm" className="gap-1.5">
              <Plus className="h-4 w-4" /> Register Clinic
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Affiliated Doctors</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Active practice links</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Today's Queue</CardTitle>
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Checked-in patients</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Operating Hours</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Weekly active shifts</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Net Settlements</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">Post commission payout</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Clinic Management Module Placeholder</CardTitle>
          <CardDescription>
            Doctor invitations by registration number, shift configuration, and live receptionist queue will be implemented in subsequent days.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

export default ClinicPage;
