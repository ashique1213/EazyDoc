import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  CreditCard,
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Percent,
  CheckCircle2,
} from "lucide-react";
import {
  useAdminCommissions,
  useAdminFinancialSummary,
  useAdminPayments,
} from "@/features/admin";

export function AdminFinancePage() {
  const [activeTab, setActiveTab] = useState<"PAYMENTS" | "COMMISSIONS">("PAYMENTS");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  const { data: financialSummary } = useAdminFinancialSummary();

  const { data: paymentsData, isLoading: isPaymentsLoading } = useAdminPayments({
    status: statusFilter === "ALL" ? undefined : statusFilter,
    search: search.trim() || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page: activeTab === "PAYMENTS" ? page : 1,
  });

  const { data: commissionsData, isLoading: isCommissionsLoading } = useAdminCommissions({
    status: statusFilter === "ALL" ? undefined : statusFilter,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page: activeTab === "COMMISSIONS" ? page : 1,
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/admin" className="text-xs text-muted-foreground hover:underline">
              Dashboard
            </Link>
            <span className="text-xs text-muted-foreground">/</span>
            <span className="text-xs font-semibold text-foreground">Finance</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2 mt-1">
            <CreditCard className="h-6 w-6 text-emerald-600" />
            Payment Transactions & SaaS Commission Ledger
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Monitor real-time gateway payments, historical commission snapshots, and clinic share allocations.
          </p>
        </div>
        <Link to="/admin/settings/commission">
          <Button size="sm" variant="outline" className="text-xs h-9 gap-1.5 shadow-sm">
            <Percent className="h-3.5 w-3.5 text-primary" /> Commission Rate Settings
          </Button>
        </Link>
      </div>

      {/* Financial Summary Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-muted/80 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Gross Successful Payments
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              ₹{financialSummary?.totals.gross_successful_payments ?? "0.00"}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-600" />
              {financialSummary?.totals.successful_payments_count ?? 0} paid transactions
            </p>
          </CardContent>
        </Card>

        <Card className="border-muted/80 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Recorded Platform Commission
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              ₹{financialSummary?.totals.recorded_commission ?? "0.00"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Sum of immutable commission snapshots
            </p>
          </CardContent>
        </Card>

        <Card className="border-muted/80 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Calculated Clinic Share
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600">
              ₹{financialSummary?.totals.calculated_clinic_share ?? "0.00"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Net internal allocation for clinics
            </p>
          </CardContent>
        </Card>

        <Card className="border-muted/80 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Actual Disbursed Payouts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              ₹{financialSummary?.totals.actual_payouts ?? "0.00"}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Gateway settlement inactive (zero external transfer)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs Switcher */}
      <div className="flex items-center gap-2 border-b">
        <button
          onClick={() => {
            setActiveTab("PAYMENTS");
            setStatusFilter("ALL");
            setPage(1);
          }}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "PAYMENTS"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <CreditCard className="h-4 w-4" /> Gateway Payment Records
        </button>
        <button
          onClick={() => {
            setActiveTab("COMMISSIONS");
            setStatusFilter("ALL");
            setPage(1);
          }}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "COMMISSIONS"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Percent className="h-4 w-4" /> Commission & Share Ledger
        </button>
      </div>

      {/* Search and Filters */}
      <Card className="border-muted/80 shadow-sm">
        <CardContent className="pt-5">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search order ID, patient, clinic..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-9 text-xs"
              />
            </div>

            <div>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="ALL">All Statuses</option>
                {activeTab === "PAYMENTS" ? (
                  <>
                    <option value="PAID">Paid</option>
                    <option value="FAILED">Failed</option>
                    <option value="PENDING">Pending</option>
                    <option value="REFUNDED">Refunded</option>
                  </>
                ) : (
                  <>
                    <option value="PENDING_SETTLEMENT">Pending Settlement</option>
                    <option value="SETTLED">Settled</option>
                    <option value="REFUNDED">Refunded</option>
                    <option value="CANCELLED">Cancelled</option>
                  </>
                )}
              </select>
            </div>

            <div>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(1);
                }}
                className="text-xs h-9"
                title="Date From"
              />
            </div>

            <div>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPage(1);
                }}
                className="text-xs h-9"
                title="Date To"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table Content */}
      {activeTab === "PAYMENTS" ? (
        <Card className="border-muted/80 shadow-sm overflow-hidden">
          <CardHeader className="py-3.5 px-6 border-b bg-muted/20">
            <CardTitle className="text-sm font-semibold">
              Payment Transactions ({paymentsData?.count ?? 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {isPaymentsLoading ? (
              <div className="flex items-center justify-center py-20 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                <span className="text-xs">Loading payments...</span>
              </div>
            ) : paymentsData?.results && paymentsData.results.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b bg-muted/40 text-muted-foreground font-semibold text-left">
                      <th className="py-3 px-4">Gateway Order / Payment ID</th>
                      <th className="py-3 px-4">Patient</th>
                      <th className="py-3 px-4">Clinic Facility</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Commission Snapshot</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Created Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {paymentsData.results.map((p) => (
                      <tr key={p.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-4 font-mono">
                          <div className="font-semibold text-foreground">{p.gateway_order_id}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {p.gateway_payment_id || "No payment id yet"}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-foreground">{p.patient_name}</div>
                          <div className="text-[10px] text-muted-foreground">{p.patient_email}</div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-foreground">{p.clinic?.name}</div>
                          <div className="text-[10px] text-muted-foreground">{p.clinic?.city}</div>
                        </td>
                        <td className="py-3 px-4 font-bold text-foreground">
                          ₹{p.amount} {p.currency}
                        </td>
                        <td className="py-3 px-4">
                          {p.commission_record ? (
                            <div className="space-y-0.5">
                              <div className="text-[11px] font-semibold text-primary">
                                Comm: ₹{p.commission_record.commission_amount} ({p.commission_record.commission_rate}%)
                              </div>
                              <div className="text-[10px] text-emerald-600">
                                Clinic: ₹{p.commission_record.clinic_share}
                              </div>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-[10px]">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <Badge
                            variant={
                              p.status === "PAID"
                                ? "default"
                                : p.status === "FAILED"
                                ? "destructive"
                                : "outline"
                            }
                            className="text-[10px]"
                          >
                            {p.status}
                          </Badge>
                          {p.failure_description && (
                            <p className="text-[10px] text-destructive mt-0.5 max-w-[200px] truncate" title={p.failure_description}>
                              {p.failure_description}
                            </p>
                          )}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {new Date(p.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-16 text-center text-xs text-muted-foreground">
                No payment transactions found matching the filter criteria.
              </div>
            )}

            {/* Pagination */}
            {paymentsData && paymentsData.count > 15 && (
              <div className="flex items-center justify-between p-4 border-t text-xs">
                <span className="text-muted-foreground">
                  Showing page {page} of {Math.ceil(paymentsData.count / 15)}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="h-8"
                  >
                    <ChevronLeft className="h-3.5 w-3.5 mr-1" /> Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!paymentsData.next}
                    onClick={() => setPage((p) => p + 1)}
                    className="h-8"
                  >
                    Next <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="border-muted/80 shadow-sm overflow-hidden">
          <CardHeader className="py-3.5 px-6 border-b bg-muted/20">
            <CardTitle className="text-sm font-semibold">
              Commission Accounting Records ({commissionsData?.count ?? 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {isCommissionsLoading ? (
              <div className="flex items-center justify-center py-20 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                <span className="text-xs">Loading commission records...</span>
              </div>
            ) : commissionsData?.results && commissionsData.results.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b bg-muted/40 text-muted-foreground font-semibold text-left">
                      <th className="py-3 px-4">Booking Reference</th>
                      <th className="py-3 px-4">Clinic Partner</th>
                      <th className="py-3 px-4">Gross Charge</th>
                      <th className="py-3 px-4">Applied Snapshot Rate</th>
                      <th className="py-3 px-4">Platform Commission</th>
                      <th className="py-3 px-4">Clinic Net Share</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Created Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {commissionsData.results.map((c) => (
                      <tr key={c.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-foreground">
                          {c.booking_reference}
                        </td>
                        <td className="py-3 px-4 font-medium text-foreground">
                          {c.clinic_name}
                        </td>
                        <td className="py-3 px-4 font-bold text-foreground">
                          ₹{c.gross_amount}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="outline" className="font-mono text-[10px]">
                            {c.commission_rate}%
                          </Badge>
                        </td>
                        <td className="py-3 px-4 font-semibold text-primary">
                          ₹{c.commission_amount}
                        </td>
                        <td className="py-3 px-4 font-semibold text-emerald-600">
                          ₹{c.clinic_share}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="secondary" className="text-[10px]">
                            {c.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {new Date(c.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-16 text-center text-xs text-muted-foreground">
                No commission records found matching the filter criteria.
              </div>
            )}

            {/* Pagination */}
            {commissionsData && commissionsData.count > 15 && (
              <div className="flex items-center justify-between p-4 border-t text-xs">
                <span className="text-muted-foreground">
                  Showing page {page} of {Math.ceil(commissionsData.count / 15)}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="h-8"
                  >
                    <ChevronLeft className="h-3.5 w-3.5 mr-1" /> Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!commissionsData.next}
                    onClick={() => setPage((p) => p + 1)}
                    className="h-8"
                  >
                    Next <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default AdminFinancePage;
