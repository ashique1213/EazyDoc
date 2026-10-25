import { useState } from "react";
import { Link } from "react-router-dom";
import {
  IndianRupee,
  TrendingUp,
  Receipt,
  Percent,
  AlertCircle,
  ArrowLeft,
  Search,
  Calendar,
  Building2,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ClinicSwitcher,
  useActiveClinic,
  useClinicFinanceSummary,
  useClinicFinancePayments,
} from "@/features/clinicOperations";

export function ClinicFinancePage() {
  const { activeClinic, activeClinicId, isLoading: isLoadingClinic } = useActiveClinic();

  const [period, setPeriod] = useState<string>("this_month");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");

  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  // Queries
  const summaryParams = {
    period: period !== "custom" ? period : undefined,
    from_date: period === "custom" && fromDate ? fromDate : undefined,
    to_date: period === "custom" && toDate ? toDate : undefined,
  };

  const { data: summaryData, isLoading: isLoadingSummary } = useClinicFinanceSummary(
    activeClinicId,
    summaryParams
  );

  const { data: paymentsData, isLoading: isLoadingPayments } = useClinicFinancePayments(
    activeClinicId,
    {
      status: statusFilter !== "ALL" ? statusFilter : undefined,
      search: search.trim() || undefined,
      page,
      page_size: 15,
    }
  );

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
        <h1 className="text-2xl font-bold tracking-tight">Clinic Finance</h1>
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            No clinic selected or you do not have permission to view finances.
          </CardContent>
        </Card>
      </div>
    );
  }

  const periodMetrics = summaryData?.period_metrics;
  const allTimeMetrics = summaryData?.all_time_metrics;
  const payments = paymentsData?.results || [];
  const totalPages = paymentsData?.total_pages || 1;

  const formatCurrency = (val: string | number | null | undefined) => {
    const num = Number(val || 0);
    return `₹${num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
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
            <span className="text-xs font-medium text-foreground">Financial Summary & Ledger</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <IndianRupee className="h-6 w-6 text-primary" />
              Clinic Financial Ledger
            </h1>
            <Badge variant="outline" className="font-mono text-xs">
              Timezone: {activeClinic.timezone || "UTC"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Track gross patient collections, platform commission splits, and recorded clinic share for{" "}
            <span className="font-semibold text-foreground">{activeClinic.name}</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <ClinicSwitcher />
        </div>
      </div>

      {/* Crucial Multi-tenant Disclaimer / Payout Notice */}
      <Card className="border-amber-200 bg-amber-50/60 dark:bg-amber-950/20 dark:border-amber-900/50">
        <CardContent className="p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-sm text-amber-900 dark:text-amber-200 space-y-1">
            <div className="font-semibold">Calculated Clinic Share — Settlement Disclaimer</div>
            <p className="text-xs text-amber-800 dark:text-amber-300">
              Figures below represent the <strong>calculated clinic entitlement</strong> based on stored commission snapshots at the exact time of each payment transaction. Historical commissions are immutable and never recalculated with newer rates.
              <strong className="block mt-0.5">
                Calculated share is recorded for accounting and reconciliation purposes only; automated bank payouts are not active on this platform.
              </strong>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Date Range Selector */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Reporting Period:
              </span>
              <div className="flex flex-wrap gap-1">
                {[
                  { key: "today", label: "Today" },
                  { key: "this_week", label: "This Week" },
                  { key: "this_month", label: "This Month" },
                  { key: "custom", label: "Custom Range" },
                ].map((p) => (
                  <Button
                    key={p.key}
                    variant={period === p.key ? "default" : "outline"}
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => setPeriod(p.key)}
                  >
                    {p.label}
                  </Button>
                ))}
              </div>
            </div>

            {period === "custom" && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="px-2 py-1 text-xs border rounded bg-background"
                />
                <span className="text-xs text-muted-foreground">to</span>
                <input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  className="px-2 py-1 text-xs border rounded bg-background"
                />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Financial Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Gross Collections */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase flex items-center justify-between">
              Gross Patient Collections
              <TrendingUp className="h-4 w-4 text-emerald-500" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {isLoadingSummary ? "..." : formatCurrency(periodMetrics?.gross_payments)}
            </div>
            <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <span>{periodMetrics?.successful_payments_count || 0} successful transaction(s)</span>
            </div>
          </CardContent>
        </Card>

        {/* Calculated Clinic Share */}
        <Card className="border-primary/30 bg-primary/[0.02]">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-primary uppercase flex items-center justify-between">
              Calculated Clinic Share
              <Receipt className="h-4 w-4 text-primary" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {isLoadingSummary ? "..." : formatCurrency(periodMetrics?.calculated_clinic_share)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Net revenue allocated to clinic
            </div>
          </CardContent>
        </Card>

        {/* Platform Commission Split */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase flex items-center justify-between">
              Platform Commission
              <Percent className="h-4 w-4 text-blue-500" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {isLoadingSummary ? "..." : formatCurrency(periodMetrics?.recorded_platform_commission)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Retained platform SaaS fee
            </div>
          </CardContent>
        </Card>

        {/* Payment Failures & Refunds */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase flex items-center justify-between">
              Failures & Refunds
              <AlertCircle className="h-4 w-4 text-amber-500" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {isLoadingSummary ? "..." : formatCurrency(periodMetrics?.refunded_total)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {periodMetrics?.refunded_count || 0} refunded, {periodMetrics?.failed_payments_count || 0} failed
            </div>
          </CardContent>
        </Card>
      </div>

      {/* All-time comparison banner */}
      <div className="p-4 rounded-lg bg-muted/40 border flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <span className="font-semibold text-foreground">All-Time Clinic Financials:</span>
          <span className="text-muted-foreground">
            Gross: <strong className="text-foreground">{formatCurrency(allTimeMetrics?.all_time_gross)}</strong>
          </span>
          <span className="text-muted-foreground">|</span>
          <span className="text-muted-foreground">
            Clinic Share: <strong className="text-primary">{formatCurrency(allTimeMetrics?.all_time_clinic_share)}</strong>
          </span>
          <span className="text-muted-foreground">|</span>
          <span className="text-muted-foreground">
            Platform Commission: <strong className="text-foreground">{formatCurrency(allTimeMetrics?.all_time_commission)}</strong>
          </span>
        </div>
        <div className="text-muted-foreground text-[11px]">
          * Recorded using transaction-time snapshots
        </div>
      </div>

      {/* Transactions Ledger Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                Clinic Payment Transaction Log
              </CardTitle>
              <CardDescription>
                Detailed audit ledger of patient payments, commission snapshots, and gateway identifiers.
              </CardDescription>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Ref or Patient..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="pl-8 pr-3 py-1.5 text-xs border rounded-md bg-background w-36 sm:w-48"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="text-xs border rounded-md px-2 py-1.5 bg-background"
              >
                <option value="ALL">All Statuses</option>
                <option value="PAID">Paid</option>
                <option value="PENDING">Pending</option>
                <option value="FAILED">Failed</option>
                <option value="REFUNDED">Refunded</option>
              </select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoadingPayments ? (
            <div className="p-8 text-center text-muted-foreground">Loading transaction records...</div>
          ) : payments.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No payment transactions match the selected filters.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Booking Ref</TableHead>
                  <TableHead>Patient & Doctor</TableHead>
                  <TableHead>Gateway / Tx ID</TableHead>
                  <TableHead>Gross Amount</TableHead>
                  <TableHead>Commission</TableHead>
                  <TableHead>Clinic Share</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Paid At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((p) => {
                  const comm = p.commission_snapshot;
                  return (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs font-semibold">
                        {p.booking_reference || "N/A"}
                      </TableCell>
                      <TableCell>
                        <div className="text-xs">
                          <div className="font-medium text-foreground">{p.patient.name}</div>
                          <div className="text-muted-foreground text-[11px]">
                            Dr. {p.doctor_name || "Assigned Doctor"}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-[11px] font-mono text-muted-foreground">
                          <div>{p.gateway_name}</div>
                          <div className="truncate max-w-[130px]" title={p.gateway_payment_id || p.gateway_order_id}>
                            {p.gateway_payment_id || p.gateway_order_id}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="font-semibold text-xs text-foreground">
                        {formatCurrency(p.amount)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {comm ? formatCurrency(comm.commission_amount) : "—"}
                        {comm && (
                          <span className="text-[10px] text-muted-foreground ml-1">
                            ({comm.commission_rate}%)
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs font-semibold text-primary">
                        {comm ? formatCurrency(comm.clinic_share) : "—"}
                      </TableCell>
                      <TableCell>
                        {p.status === "PAID" ? (
                          <Badge variant="default" className="bg-emerald-600 hover:bg-emerald-700 text-[10px]">
                            Paid
                          </Badge>
                        ) : p.status === "FAILED" ? (
                          <Badge variant="destructive" className="text-[10px]">
                            Failed
                          </Badge>
                        ) : p.status === "REFUNDED" ? (
                          <Badge variant="secondary" className="text-[10px]">
                            Refunded
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-[10px]">
                            {p.status}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {p.paid_at
                          ? new Date(p.paid_at).toLocaleDateString("en-IN", {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-4 border-t flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="h-7 text-xs"
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="h-7 text-xs"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
