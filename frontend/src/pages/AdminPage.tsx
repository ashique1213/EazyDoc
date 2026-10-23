import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Building2,
  Stethoscope,
  Users,
  Calendar,
  CreditCard,
  Percent,
  ShieldCheck,
  ArrowUpRight,
  Clock,
  CheckCircle2,
  TrendingUp,
  RefreshCw,
  Info,
} from "lucide-react";
import {
  useAdminAppointmentsTrend,
  useAdminDashboardSummary,
  useAdminFinancialSummary,
} from "@/features/admin";

export function AdminPage() {
  const [days] = useState<number>(14);
  const {
    data: summary,
    isLoading: isSummaryLoading,
    refetch: refetchSummary,
    isRefetching,
  } = useAdminDashboardSummary();

  const { data: trendData } = useAdminAppointmentsTrend({ days });
  const { data: financialData } = useAdminFinancialSummary({ days });

  return (
    <div className="space-y-8 pb-10">
      {/* Top Banner / Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
              Super Admin SaaS Dashboard
            </h1>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 text-xs py-0.5">
              Live Platform Metrics
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Centralized platform intelligence, verification management, financial controls, and audit trails.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchSummary()}
            disabled={isRefetching}
            className="text-xs h-9"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isRefetching ? "animate-spin" : ""}`} />
            Refresh Data
          </Button>
          <Link to="/admin/settings/commission">
            <Button size="sm" className="text-xs h-9 gap-1.5 shadow-sm">
              <Percent className="h-3.5 w-3.5" /> Configure Commission
            </Button>
          </Link>
        </div>
      </div>

      {/* Primary Operational Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Clinics Metric Card */}
        <Link to="/admin/clinics">
          <Card className="hover:border-primary/50 hover:shadow-md transition-all cursor-pointer h-full border-muted/80">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Healthcare Clinics
              </CardTitle>
              <div className="h-8 w-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600">
                <Building2 className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : summary?.clinics.total ?? 0}
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs">
                <span className="text-emerald-600 font-medium flex items-center gap-0.5">
                  <CheckCircle2 className="h-3 w-3" /> {summary?.clinics.approved ?? 0} Approved
                </span>
                <span className="text-muted-foreground">•</span>
                <span className="text-amber-600 font-medium flex items-center gap-0.5">
                  <Clock className="h-3 w-3" /> {summary?.clinics.pending ?? 0} Pending
                </span>
              </div>
            </CardContent>
          </Card>
        </Link>

        {/* Doctors Metric Card */}
        <Link to="/admin/doctors">
          <Card className="hover:border-primary/50 hover:shadow-md transition-all cursor-pointer h-full border-muted/80">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Medical Practitioners
              </CardTitle>
              <div className="h-8 w-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-600">
                <Stethoscope className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : summary?.doctors.total ?? 0}
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs">
                <span className="text-blue-600 font-medium flex items-center gap-0.5">
                  <CheckCircle2 className="h-3 w-3" /> {summary?.doctors.verified ?? 0} Verified
                </span>
                <span className="text-muted-foreground">•</span>
                <span className="text-amber-600 font-medium flex items-center gap-0.5">
                  <Clock className="h-3 w-3" /> {summary?.doctors.pending ?? 0} Pending
                </span>
              </div>
            </CardContent>
          </Card>
        </Link>

        {/* Patients & Users Metric Card */}
        <Link to="/admin/users">
          <Card className="hover:border-primary/50 hover:shadow-md transition-all cursor-pointer h-full border-muted/80">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Patients & Users
              </CardTitle>
              <div className="h-8 w-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-600">
                <Users className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : summary?.users.total_patients ?? 0}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Across {summary?.users.total_users ?? 0} total platform user accounts
              </p>
            </CardContent>
          </Card>
        </Link>

        {/* Platform Appointments Metric Card */}
        <Link to="/admin/appointments">
          <Card className="hover:border-primary/50 hover:shadow-md transition-all cursor-pointer h-full border-muted/80">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Appointments Today
              </CardTitle>
              <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-600">
                <Calendar className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : summary?.appointments.today ?? 0}
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs">
                <span className="text-indigo-600 font-medium">
                  {summary?.appointments.upcoming ?? 0} Upcoming
                </span>
                <span className="text-muted-foreground">•</span>
                <span className="text-emerald-600 font-medium">
                  {summary?.appointments.completed ?? 0} Completed
                </span>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Financial Overview Section */}
      <Card className="border-muted/80 shadow-sm overflow-hidden">
        <CardHeader className="bg-muted/30 border-b">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-emerald-600" />
                Financial Operations & SaaS Commission Summary
              </CardTitle>
              <CardDescription className="text-xs">
                Strict accounting separation of platform commission snapshots and clinic allocations.
              </CardDescription>
            </div>
            <Link to="/admin/finance">
              <Button variant="outline" size="sm" className="text-xs gap-1 h-8">
                View Full Ledger <ArrowUpRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid gap-6 md:grid-cols-4">
            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Gross Successful Payments</span>
              <div className="text-2xl font-bold text-foreground">
                ₹{summary?.finance.gross_volume ?? "0.00"}
              </div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                {summary?.finance.successful_payments ?? 0} successful transactions
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Recorded Platform Commission</span>
              <div className="text-2xl font-bold text-primary">
                ₹{summary?.finance.recorded_commission ?? "0.00"}
              </div>
              <p className="text-[11px] text-muted-foreground">
                Default rate: {summary?.finance.default_commission_rate ?? "5.00"}%
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Calculated Clinic Share</span>
              <div className="text-2xl font-bold text-emerald-600">
                ₹{summary?.finance.calculated_clinic_share ?? "0.00"}
              </div>
              <p className="text-[11px] text-muted-foreground">
                Total earmarked for clinic partners
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Failed Payments Attention</span>
              <div className="text-2xl font-bold text-destructive">
                {summary?.finance.failed_payments ?? 0}
              </div>
              <p className="text-[11px] text-muted-foreground">
                Payment attempts requiring review
              </p>
            </div>
          </div>

          {/* Transparent Settlement Notice */}
          <div className="mt-6 rounded-lg bg-muted/40 border p-3 flex items-start gap-2.5 text-xs text-muted-foreground">
            <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-foreground">Accounting Transparency Notice: </span>
              {summary?.finance.payout_disclaimer || "Calculated clinic shares represent internal ledger allocations. Actual clinic bank payouts are 0.00 until explicit payout gateway clearance."}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Visual Activity Breakdown */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Appointment Trend Breakdown */}
        <Card className="border-muted/80 shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Appointment Booking Activity (Last 14 Days)
                </CardTitle>
                <CardDescription className="text-xs">
                  Daily distribution of confirmed, completed, and cancelled consultations.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {trendData && trendData.length > 0 ? (
              <div className="space-y-3">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b text-muted-foreground font-semibold">
                        <th className="text-left py-2">Date</th>
                        <th className="text-right py-2">Total</th>
                        <th className="text-right py-2 text-emerald-600">Confirmed</th>
                        <th className="text-right py-2 text-blue-600">Completed</th>
                        <th className="text-right py-2 text-destructive">Cancelled</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {trendData.slice(-7).map((pt) => (
                        <tr key={pt.date} className="hover:bg-muted/40 transition-colors">
                          <td className="py-2 font-medium">{pt.date}</td>
                          <td className="text-right py-2 font-bold">{pt.total}</td>
                          <td className="text-right py-2 text-emerald-600">{pt.confirmed}</td>
                          <td className="text-right py-2 text-blue-600">{pt.completed}</td>
                          <td className="text-right py-2 text-destructive">{pt.cancelled}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-muted-foreground">
                No appointment trends recorded in this period.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Financial Activity Breakdown */}
        <Card className="border-muted/80 shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <CreditCard className="h-4 w-4 text-emerald-600" />
                  Recent Daily Financial Flow (Last 7 Days)
                </CardTitle>
                <CardDescription className="text-xs">
                  Recorded gross transaction volume versus platform commission snapshots.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {financialData?.daily_trend && financialData.daily_trend.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b text-muted-foreground font-semibold">
                      <th className="text-left py-2">Date</th>
                      <th className="text-right py-2">Gross Volume</th>
                      <th className="text-right py-2 text-primary">Commission</th>
                      <th className="text-right py-2 text-emerald-600">Clinic Share</th>
                      <th className="text-right py-2">Success/Fail</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {financialData.daily_trend.slice(-7).map((item) => (
                      <tr key={item.date} className="hover:bg-muted/40 transition-colors">
                        <td className="py-2 font-medium">{item.date}</td>
                        <td className="text-right py-2 font-bold">₹{item.gross_volume}</td>
                        <td className="text-right py-2 text-primary font-semibold">₹{item.commission_recorded}</td>
                        <td className="text-right py-2 text-emerald-600">₹{item.clinic_share}</td>
                        <td className="text-right py-2 text-muted-foreground">
                          {item.successful_count} / {item.failed_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-muted-foreground">
                No financial transactions recorded in this period.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Navigation Panels */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link to="/admin/clinics">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-emerald-600" />
                  Clinics Management
                </span>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription className="text-xs">
                Review pending verification requests, suspend or reactivate facilities, and inspect operating licenses.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link to="/admin/doctors">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Stethoscope className="h-4 w-4 text-blue-600" />
                  Doctor Verification
                </span>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription className="text-xs">
                Inspect medical council registrations, credential certificates, and manage practitioner verifications.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link to="/admin/users">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-purple-600" />
                  User Accounts
                </span>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription className="text-xs">
                Monitor user accounts across roles, activate, deactivate, or suspend access with safety lockouts.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link to="/admin/appointments">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-indigo-600" />
                  Appointment Administration
                </span>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription className="text-xs">
                Track booking references, clinic and practitioner schedules, and inspect cancellation event histories.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link to="/admin/settings/commission">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Percent className="h-4 w-4 text-amber-600" />
                  Commission Configuration
                </span>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription className="text-xs">
                Configure default platform commission rate and review clinic-specific commercial overrides.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link to="/admin/audit-logs">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  Audit Trail & Security
                </span>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription className="text-xs">
                Inspect immutable security logs, administrative decisions, IP addresses, and state modifications.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}

export default AdminPage;
