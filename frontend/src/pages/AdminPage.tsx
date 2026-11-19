import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Building2,
  Stethoscope,
  Calendar,
  CreditCard,
  Percent,
  ShieldCheck,
  CheckCircle2,
  TrendingUp,
  BarChart3,
  Layers,
  FileCheck2,
  Zap,
} from "lucide-react";
import { AdminSubscriptionTab } from "@/features/subscriptions";
import {
  AnalyticsFilterBar,
  AppointmentVolumeChart,
  ClinicComparisonTable,
  DoctorPerformanceTable,
  FinancialReconciliationTable,
  PaymentStatusPieChart,
  PeakDaysChart,
  PeakHoursChart,
  ReportExportDialog,
  RevenueTrendsChart,
  useAdminAnalyticsAppointments,
  useAdminAnalyticsClinics,
  useAdminAnalyticsDoctors,
  useAdminAnalyticsOverview,
  useAdminAnalyticsReconciliation,
  useAdminAnalyticsRevenue,
  type AnalyticsFilterParams,
} from "@/features/analytics";

type ActiveTab =
  | "overview"
  | "revenue"
  | "appointments"
  | "clinics"
  | "doctors"
  | "reconciliation"
  | "subscriptions";

export function AdminPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");
  const [filters, setFilters] = useState<AnalyticsFilterParams>({
    period: "last_30_days",
  });
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Queries
  const {
    data: overview,
    isLoading: isOverviewLoading,
    refetch: refetchOverview,
    isRefetching: isRefetchingOverview,
  } = useAdminAnalyticsOverview(filters);

  const {
    data: revenue,
    refetch: refetchRevenue,
  } = useAdminAnalyticsRevenue(filters);

  const {
    data: appointments,
    refetch: refetchAppts,
  } = useAdminAnalyticsAppointments(filters);

  const {
    data: clinics,
    refetch: refetchClinics,
  } = useAdminAnalyticsClinics(filters);

  const {
    data: doctors,
    refetch: refetchDoctors,
  } = useAdminAnalyticsDoctors(filters);

  const {
    data: reconciliation,
    refetch: refetchRec,
  } = useAdminAnalyticsReconciliation(filters);

  const handleRefreshAll = () => {
    refetchOverview();
    refetchRevenue();
    refetchAppts();
    refetchClinics();
    refetchDoctors();
    refetchRec();
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
              SaaS Analytics & Business Intelligence
            </h1>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 text-xs py-0.5 font-semibold">
              Platform Executive View
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time financial performance, appointment operations, multi-clinic doctor practices, and financial reconciliation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/admin/settings/commission">
            <Button size="sm" variant="outline" className="text-xs h-9 gap-1.5">
              <Percent className="h-3.5 w-3.5 text-primary" /> Commission Settings
            </Button>
          </Link>
          <Link to="/admin/audit-logs">
            <Button size="sm" variant="outline" className="text-xs h-9 gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" /> Security Audit
            </Button>
          </Link>
        </div>
      </div>

      {/* Global Filter Bar */}
      <AnalyticsFilterBar
        filters={filters}
        onFilterChange={setFilters}
        onRefresh={handleRefreshAll}
        onOpenExport={() => setIsExportOpen(true)}
        isRefreshing={isRefetchingOverview}
      />

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b overflow-x-auto pb-1 text-sm font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "overview"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers className="w-4 h-4" />
          Overview KPIs
        </button>
        <button
          onClick={() => setActiveTab("revenue")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "revenue"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Revenue & Commissions
        </button>
        <button
          onClick={() => setActiveTab("appointments")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "appointments"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Appointment Analytics
        </button>
        <button
          onClick={() => setActiveTab("clinics")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "clinics"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Clinic Performance
        </button>
        <button
          onClick={() => setActiveTab("doctors")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "doctors"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Stethoscope className="w-4 h-4" />
          Doctor Practice
        </button>
        <button
          onClick={() => setActiveTab("reconciliation")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "reconciliation"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          Financial Reconciliation
          {reconciliation && reconciliation.discrepancy_count > 0 && (
            <Badge variant="destructive" className="ml-1 text-[10px] px-1.5 py-0">
              {reconciliation.discrepancy_count}
            </Badge>
          )}
        </button>
        <button
          onClick={() => setActiveTab("subscriptions")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
            activeTab === "subscriptions"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Zap className="w-4 h-4 text-purple-600" />
          SaaS Monetization & MRR
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Executive KPI Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Gross Collected */}
            <Card className="border shadow-xs">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Gross Revenue Collected
                </CardTitle>
                <div className="h-8 w-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-600">
                  <CreditCard className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-blue-600">
                  {isOverviewLoading ? "—" : `₹${parseFloat(overview?.finance.gross_collected || "0").toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <span className="text-emerald-600 font-medium flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    {overview?.finance.successful_payments_count ?? 0} paid
                  </span>
                  <span>•</span>
                  <span>Conv: {overview?.finance.conversion_rate ?? 0}%</span>
                </div>
              </CardContent>
            </Card>

            {/* Platform Commission */}
            <Card className="border shadow-xs">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Platform Commission (Net)
                </CardTitle>
                <div className="h-8 w-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600">
                  <Percent className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-emerald-600">
                  {isOverviewLoading ? "—" : `₹${parseFloat(overview?.finance.platform_commission || "0").toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Retained SaaS margin across all bookings
                </p>
              </CardContent>
            </Card>

            {/* Clinic Payable Share */}
            <Card className="border shadow-xs">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Clinic Payable Share
                </CardTitle>
                <div className="h-8 w-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-600">
                  <Building2 className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-purple-600">
                  {isOverviewLoading ? "—" : `₹${parseFloat(overview?.finance.clinic_payable || "0").toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Total earnings allocated to partner clinics
                </p>
              </CardContent>
            </Card>

            {/* Appointments */}
            <Card className="border shadow-xs">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Total Bookings
                </CardTitle>
                <div className="h-8 w-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-600">
                  <Calendar className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {isOverviewLoading ? "—" : overview?.appointments.total ?? 0}
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs">
                  <span className="text-emerald-600 font-medium">
                    {overview?.appointments.completion_rate ?? 0}% completed
                  </span>
                  <span className="text-muted-foreground">•</span>
                  <span className="text-rose-600 font-medium">
                    {overview?.appointments.cancellation_rate ?? 0}% cancelled
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Secondary Entity Count Cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="border shadow-xs">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Platform Users</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold text-foreground">
                  {overview?.users.total_users ?? 0} Accounts
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {overview?.users.total_patients ?? 0} registered patients
                </p>
              </CardContent>
            </Card>

            <Card className="border shadow-xs">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Clinics Registered</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold text-foreground">
                  {overview?.clinics.total ?? 0} Total Clinics
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {overview?.clinics.approved ?? 0} approved ({overview?.clinics.active ?? 0} active)
                </p>
              </CardContent>
            </Card>

            <Card className="border shadow-xs">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Medical Practitioners</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold text-foreground">
                  {overview?.doctors.total ?? 0} Total Doctors
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {overview?.doctors.verified ?? 0} verified practitioners
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Trends Grid */}
          <div className="grid gap-6 lg:grid-cols-2">
            {revenue && <RevenueTrendsChart data={revenue.daily_trend} />}
            {appointments && <AppointmentVolumeChart data={appointments.daily_trend} />}
          </div>
        </div>
      )}

      {/* Tab 2: Revenue & Commissions */}
      {activeTab === "revenue" && revenue && (
        <div className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <RevenueTrendsChart data={revenue.daily_trend} />
            </div>
            <div>
              <PaymentStatusPieChart data={revenue.payment_status_distribution} />
            </div>
          </div>

          {/* Top Clinics Revenue Breakdown */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Building2 className="w-4 h-4 text-primary" />
                Clinic Revenue Breakdown
              </CardTitle>
              <CardDescription className="text-xs">
                Top revenue-generating clinics for the selected timeframe
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-muted/50 border-y text-muted-foreground uppercase font-semibold text-[10px] tracking-wider">
                    <tr>
                      <th className="py-2.5 px-4">Clinic Name</th>
                      <th className="py-2.5 px-3 text-right">Settled Bookings</th>
                      <th className="py-2.5 px-3 text-right">Gross Collections</th>
                      <th className="py-2.5 px-3 text-right">Platform Commission</th>
                      <th className="py-2.5 px-4 text-right">Clinic Payable Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {revenue.clinic_revenue_breakdown.map((c) => (
                      <tr key={c.clinic_id} className="hover:bg-muted/40 transition-colors">
                        <td className="py-2.5 px-4 font-semibold text-foreground">{c.clinic_name}</td>
                        <td className="py-2.5 px-3 text-right text-muted-foreground">{c.settled_appointments}</td>
                        <td className="py-2.5 px-3 text-right font-medium text-blue-600">
                          ₹{parseFloat(c.gross_revenue).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium text-emerald-600">
                          ₹{parseFloat(c.platform_commission).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2.5 px-4 text-right font-semibold text-purple-600">
                          ₹{parseFloat(c.clinic_share).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 3: Appointments */}
      {activeTab === "appointments" && appointments && (
        <div className="space-y-6">
          <AppointmentVolumeChart data={appointments.daily_trend} />
          <div className="grid gap-6 md:grid-cols-2">
            <PeakHoursChart data={appointments.peak_hours} />
            <PeakDaysChart data={appointments.peak_days} />
          </div>
        </div>
      )}

      {/* Tab 4: Clinics */}
      {activeTab === "clinics" && clinics && (
        <div className="space-y-6">
          <ClinicComparisonTable clinics={clinics} />
        </div>
      )}

      {/* Tab 5: Doctors */}
      {activeTab === "doctors" && doctors && (
        <div className="space-y-6">
          <DoctorPerformanceTable doctors={doctors} />
        </div>
      )}

      {/* Tab 6: Financial Reconciliation */}
      {activeTab === "reconciliation" && reconciliation && (
        <div className="space-y-6">
          <FinancialReconciliationTable data={reconciliation} />
        </div>
      )}

      {/* Tab 7: SaaS Subscriptions & Monetization */}
      {activeTab === "subscriptions" && (
        <div className="space-y-6">
          <AdminSubscriptionTab />
        </div>
      )}

      {/* Export Report Modal Dialog */}
      <ReportExportDialog
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        filters={filters}
        isAdmin={true}
      />
    </div>
  );
}

export default AdminPage;
