import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Stethoscope,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AdminDoctorTable, useAdminDoctors } from "@/features/doctors";

export const AdminDoctorsPage: React.FC = () => {
  const { data: allData } = useAdminDoctors({ status: "ALL" });
  const { data: pendingData } = useAdminDoctors({ status: "PENDING" });
  const { data: verifiedData } = useAdminDoctors({ status: "VERIFIED" });
  const { data: suspendedData } = useAdminDoctors({ status: "SUSPENDED" });

  const totalCount = allData?.count ?? 0;
  const pendingCount = pendingData?.count ?? 0;
  const verifiedCount = verifiedData?.count ?? 0;
  const suspendedCount = suspendedData?.count ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/admin">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Doctor Verification & Oversight</h1>
            <p className="text-sm text-muted-foreground">
              Review practitioner medical council credentials, verify licenses, and manage clinical standing.
            </p>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Doctors
            </CardTitle>
            <Stethoscope className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCount}</div>
            <p className="text-[11px] text-muted-foreground">Registered practitioners</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-amber-500/20 bg-amber-500/5">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Pending Verification
            </CardTitle>
            <Clock className="h-4 w-4 text-amber-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-800 dark:text-amber-300">
              {pendingCount}
            </div>
            <p className="text-[11px] text-amber-700/80 dark:text-amber-400/80">
              Awaiting council verification
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-emerald-500/20 bg-emerald-500/5">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
              Verified Doctors
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-800 dark:text-emerald-300">
              {verifiedCount}
            </div>
            <p className="text-[11px] text-emerald-700/80 dark:text-emerald-400/80">
              Active & eligible for clinics
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-red-500/20 bg-red-500/5">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-red-700 dark:text-red-400">
              Suspended
            </CardTitle>
            <ShieldAlert className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-800 dark:text-red-300">
              {suspendedCount}
            </div>
            <p className="text-[11px] text-red-700/80 dark:text-red-400/80">
              Practice revoked / inquiry
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Doctor Verification Table */}
      <AdminDoctorTable />
    </div>
  );
};

export default AdminDoctorsPage;
