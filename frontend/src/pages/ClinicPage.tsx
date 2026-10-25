import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Building2,
  Users,
  Calendar,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  ArrowRight,
  Percent,
  CalendarDays,
  UserCheck,
  CreditCard,
  Settings,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ClinicSwitcher,
  useActiveClinic,
  useClinicDashboardSummary,
  useClinicDashboardTrends,
} from "@/features/clinicOperations";

export function ClinicPage() {
  const { activeClinic, activeClinicId, isLoading: isLoadingClinic } = useActiveClinic();
  const [period, setPeriod] = useState<string>("this_month");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");

  const queryParams = {
    period,
    ...(period === "custom" && fromDate && toDate ? { from_date: fromDate, to_date: toDate } : {}),
  };

  const { data: summaryData } = useClinicDashboardSummary(
    activeClinicId,
    queryParams
  );

  const { data: trendsData, isLoading: isLoadingTrends } = useClinicDashboardTrends(
    activeClinicId,
    queryParams
  );

  if (isLoadingClinic) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!activeClinic) {
    return (
      <Card className="max-w-xl mx-auto p-8 text-center border-dashed">
        <Building2 className="mx-auto h-12 w-12 text-muted-foreground/60 mb-3" />
        <h2 className="text-xl font-bold">No Active Clinic Selected</h2>
        <p className="text-sm text-muted-foreground mt-1 mb-4">
          You haven't registered a clinic or don't have access to an approved clinic facility yet.
        </p>
        <Link to="/clinic/register">
          <Button size="sm">Register Your First Clinic</Button>
        </Link>
      </Card>
    );
  }

  const metrics = summaryData?.appointment_metrics;
  const docMetrics = summaryData?.doctor_metrics;
  const finMetrics = summaryData?.financial_metrics;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner & Clinic Switcher */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-card p-5 rounded-2xl border shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{activeClinic.name}</h1>
            <Badge
              variant="outline"
              className={
                activeClinic.status === "APPROVED"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : activeClinic.status === "PENDING"
                  ? "bg-amber-50 text-amber-700 border-amber-200"
                  : "bg-muted text-muted-foreground"
              }
            >
              {activeClinic.status}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground flex items-center space-x-2">
            <span>{activeClinic.city}, {activeClinic.state}</span>
            <span>•</span>
            <span className="flex items-center gap-1 font-mono">
              <Clock className="h-3 w-3" /> {activeClinic.timezone}
            </span>
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          <ClinicSwitcher />
          <Link to="/clinic/calendar">
            <Button size="sm" variant="outline" className="gap-1.5 text-xs">
              <Calendar className="h-3.5 w-3.5 text-primary" /> Calendar
            </Button>
          </Link>
          <Link to="/clinic/settings">
            <Button size="sm" variant="outline" className="gap-1.5 text-xs">
              <Settings className="h-3.5 w-3.5" /> Clinic Settings
            </Button>
          </Link>
        </div>
      </div>

      {/* Date Filter Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-muted/40 p-3 rounded-xl border">
        <div className="flex items-center space-x-1.5 text-xs font-medium text-muted-foreground">
          <CalendarDays className="h-4 w-4 text-primary" />
          <span>Reporting Period:</span>
        </div>
        <div className="flex items-center flex-wrap gap-2">
          {[
            { id: "today", label: "Today" },
            { id: "this_week", label: "This Week" },
            { id: "this_month", label: "This Month" },
            { id: "custom", label: "Custom Range" },
          ].map((item) => (
            <Button
              key={item.id}
              variant={period === item.id ? "default" : "outline"}
              size="sm"
              onClick={() => setPeriod(item.id)}
              className="h-7 text-xs px-2.5"
            >
              {item.label}
            </Button>
          ))}
          {period === "custom" && (
            <div className="flex items-center space-x-1.5">
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="h-7 text-xs rounded border bg-background px-2"
              />
              <span className="text-xs text-muted-foreground">to</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="h-7 text-xs rounded border bg-background px-2"
              />
            </div>
          )}
        </div>
      </div>

      {/* Appointments Requiring Attention Alert Banner */}
      {metrics && metrics.appointments_requiring_attention > 0 && (
        <div className="flex items-center justify-between bg-amber-50/80 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl shadow-xs">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
            <div>
              <p className="text-sm font-semibold">
                {metrics.appointments_requiring_attention} Appointment(s) Require Your Attention
              </p>
              <p className="text-xs text-amber-700">
                Reschedule requests or unconfirmed consultations are pending action.
              </p>
            </div>
          </div>
          <Link to="/clinic/appointments?requires_attention=true">
            <Button size="sm" variant="outline" className="bg-white border-amber-300 text-amber-900 hover:bg-amber-100/50 text-xs gap-1">
              Review Queue <ArrowRight className="h-3 w-3" />
            </Button>
          </Link>
        </div>
      )}

      {/* Primary Operational Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Doctors Card */}
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Affiliated Doctors
            </CardTitle>
            <div className="h-8 w-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Users className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight">
              {docMetrics ? docMetrics.total_active_doctors : "--"}
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{docMetrics?.pending_doctor_invitations || 0} pending invitations</span>
              <Link to="/clinic/doctors" className="text-primary hover:underline text-[11px] font-medium">
                Manage
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Today's Appointments */}
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Today's Schedule
            </CardTitle>
            <div className="h-8 w-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Clock className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight">
              {metrics ? metrics.today_appointments : "--"}
            </div>
            <p className="text-xs text-muted-foreground">
              Booked consultations for today
            </p>
          </CardContent>
        </Card>

        {/* Upcoming Appointments */}
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Upcoming Queue
            </CardTitle>
            <div className="h-8 w-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Calendar className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight">
              {metrics ? metrics.upcoming_appointments : "--"}
            </div>
            <p className="text-xs text-muted-foreground">
              Future confirmed visits
            </p>
          </CardContent>
        </Card>

        {/* Completed in Period */}
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Completed Visits
            </CardTitle>
            <div className="h-8 w-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight">
              {metrics ? metrics.completed_appointments : "--"}
            </div>
            <p className="text-xs text-muted-foreground">
              {metrics?.total_appointments_in_period || 0} total in this period
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Financial Snapshot Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Gross Revenue */}
        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Gross Patient Payments
            </CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight">
              ₹{finMetrics ? Number(finMetrics.gross_patient_payments).toLocaleString() : "0"}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Verified successful payments
            </p>
          </CardContent>
        </Card>

        {/* Platform Commission */}
        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Recorded Commission
            </CardTitle>
            <Percent className="h-4 w-4 text-amber-600" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight">
              ₹{finMetrics ? Number(finMetrics.recorded_platform_commission).toLocaleString() : "0"}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Retained platform fee snapshot
            </p>
          </CardContent>
        </Card>

        {/* Calculated Clinic Share */}
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Calculated Clinic Share
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight text-blue-700">
              ₹{finMetrics ? Number(finMetrics.calculated_clinic_share).toLocaleString() : "0"}
            </div>
            <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200">
              Calculated — Not Transferred
            </Badge>
          </CardContent>
        </Card>

        {/* Cancellation Rate */}
        <Card className="border-l-4 border-l-rose-500">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Cancellation Rate
            </CardTitle>
            <XCircle className="h-4 w-4 text-rose-600" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-2xl font-bold tracking-tight text-rose-700">
              {metrics ? `${metrics.cancellation_rate_percentage}%` : "--"}
            </div>
            <p className="text-[11px] text-muted-foreground">
              {metrics?.cancelled_appointments || 0} cancellations in period
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Visual Trends & Activity Section */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Daily Breakdown / Trends Table */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold">Appointment Activity Distribution</CardTitle>
                <CardDescription className="text-xs">
                  Daily appointment progression in clinic timezone ({activeClinic.timezone})
                </CardDescription>
              </div>
              <Badge variant="secondary" className="text-xs">
                {trendsData?.trends.length || 0} Days
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingTrends ? (
              <div className="h-48 flex items-center justify-center text-xs text-muted-foreground">
                Loading daily breakdown...
              </div>
            ) : trendsData?.trends.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-xs text-muted-foreground">
                No appointment activity recorded in this period.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[280px] overflow-y-auto pr-1">
                {trendsData?.trends.slice(-7).reverse().map((day) => (
                  <div
                    key={day.date}
                    className="flex items-center justify-between p-2.5 rounded-lg border bg-card/60 text-xs"
                  >
                    <div className="font-semibold text-foreground">{day.date}</div>
                    <div className="flex items-center space-x-3">
                      <span className="text-muted-foreground">
                        Total: <strong className="text-foreground">{day.total}</strong>
                      </span>
                      <span className="text-emerald-600">
                        Done: <strong>{day.completed}</strong>
                      </span>
                      <span className="text-blue-600">
                        Conf: <strong>{day.confirmed}</strong>
                      </span>
                      <span className="text-rose-600">
                        Canc: <strong>{day.cancelled}</strong>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Operational Modules Navigation Cards */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-bold">Quick Operations</CardTitle>
            <CardDescription className="text-xs">
              Manage reception queue, schedules, and staff
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link
              to="/clinic/appointments"
              className="flex items-center justify-between p-2.5 rounded-lg border hover:bg-accent transition-colors"
            >
              <div className="flex items-center space-x-2.5">
                <CalendarDays className="h-4 w-4 text-primary" />
                <div className="text-left">
                  <p className="text-xs font-semibold">Appointment Desk</p>
                  <p className="text-[10px] text-muted-foreground">Search, confirm & reschedule</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              to="/clinic/calendar"
              className="flex items-center justify-between p-2.5 rounded-lg border hover:bg-accent transition-colors"
            >
              <div className="flex items-center space-x-2.5">
                <Calendar className="h-4 w-4 text-blue-600" />
                <div className="text-left">
                  <p className="text-xs font-semibold">Live Calendar</p>
                  <p className="text-[10px] text-muted-foreground">Doctor shifts & blocked slots</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              to="/clinic/staff"
              className="flex items-center justify-between p-2.5 rounded-lg border hover:bg-accent transition-colors"
            >
              <div className="flex items-center space-x-2.5">
                <UserCheck className="h-4 w-4 text-purple-600" />
                <div className="text-left">
                  <p className="text-xs font-semibold">Clinic Staff</p>
                  <p className="text-[10px] text-muted-foreground">Assign receptionist permissions</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              to="/clinic/finance"
              className="flex items-center justify-between p-2.5 rounded-lg border hover:bg-accent transition-colors"
            >
              <div className="flex items-center space-x-2.5">
                <CreditCard className="h-4 w-4 text-emerald-600" />
                <div className="text-left">
                  <p className="text-xs font-semibold">Financial Ledger</p>
                  <p className="text-[10px] text-muted-foreground">Transactions & commission audit</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              to="/clinic/settings"
              className="flex items-center justify-between p-2.5 rounded-lg border hover:bg-accent transition-colors"
            >
              <div className="flex items-center space-x-2.5">
                <Settings className="h-4 w-4 text-amber-600" />
                <div className="text-left">
                  <p className="text-xs font-semibold">Operating Closures</p>
                  <p className="text-[10px] text-muted-foreground">Public holidays & facility leave</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default ClinicPage;
