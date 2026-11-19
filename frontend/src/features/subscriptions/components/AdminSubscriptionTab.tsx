import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CreditCard,
  TrendingUp,
  Building2,
  Clock,
  Search,
  CheckCircle2,
  Settings,
  History,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { subscriptionsApi } from "../api";
import type {
  AdminOverridePayload,
  SubscriptionEvent,
  SubscriptionStatus,
} from "../types";

export function AdminSubscriptionTab() {
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedClinicId, setSelectedClinicId] = useState<string | null>(null);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [overrideSuccess, setOverrideSuccess] = useState<string | null>(null);

  // Form state for override modal
  const [overrideStatus, setOverrideStatus] = useState<SubscriptionStatus | "">("");
  const [overridePlanId, setOverridePlanId] = useState<string>("");
  const [overrideDocLimit, setOverrideDocLimit] = useState<string>("");
  const [overrideStaffLimit, setOverrideStaffLimit] = useState<string>("");
  const [overrideExtendDays, setOverrideExtendDays] = useState<string>("");
  const [overrideReason, setOverrideReason] = useState<string>("");

  // 1. SaaS Platform Metrics
  const { data: metrics } = useQuery({
    queryKey: ["admin-subscription-metrics"],
    queryFn: () => subscriptionsApi.getAdminMetrics(),
  });

  // 2. SaaS Plans List
  const { data: plans = [] } = useQuery({
    queryKey: ["admin-subscription-plans"],
    queryFn: () => subscriptionsApi.getAdminPlans(),
  });

  // 3. Clinic Subscriptions List
  const { data: clinicSubs = [], refetch: refetchClinics } = useQuery({
    queryKey: ["admin-clinic-subscriptions", statusFilter, search],
    queryFn: () =>
      subscriptionsApi.getAdminClinicSubscriptions({
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        search: search || undefined,
      }),
  });

  // 4. Subscription Audit Events
  const { data: auditEvents = [] } = useQuery({
    queryKey: ["admin-subscription-events"],
    queryFn: () => subscriptionsApi.getAdminEvents(30),
  });

  // Override mutation
  const overrideMutation = useMutation({
    mutationFn: (payload: AdminOverridePayload) =>
      subscriptionsApi.overrideClinicSubscription(selectedClinicId!, payload),
    onSuccess: () => {
      setOverrideSuccess("Clinic subscription successfully updated with admin override.");
      setIsOverrideModalOpen(false);
      refetchClinics();
      queryClient.invalidateQueries({ queryKey: ["admin-subscription-metrics"] });
      queryClient.invalidateQueries({ queryKey: ["admin-subscription-events"] });
    },
  });

  const handleOpenOverride = (subSummary: any) => {
    setSelectedClinicId(subSummary.clinic_id);
    setOverrideStatus(subSummary.subscription?.status || "");
    setOverridePlanId("");
    setOverrideDocLimit(subSummary.doctors?.limit ? String(subSummary.doctors.limit) : "");
    setOverrideStaffLimit(subSummary.staff?.limit ? String(subSummary.staff.limit) : "");
    setOverrideExtendDays("");
    setOverrideReason("");
    setIsOverrideModalOpen(true);
  };

  const handleSubmitOverride = async () => {
    if (!overrideReason.trim()) {
      alert("Please provide an administrative reason for this override.");
      return;
    }

    const payload: AdminOverridePayload = {
      reason: overrideReason,
      status: overrideStatus ? (overrideStatus as SubscriptionStatus) : undefined,
      plan_id: overridePlanId || undefined,
      custom_doctor_limit: overrideDocLimit ? parseInt(overrideDocLimit, 10) : undefined,
      custom_staff_limit: overrideStaffLimit ? parseInt(overrideStaffLimit, 10) : undefined,
      extend_days: overrideExtendDays ? parseInt(overrideExtendDays, 10) : undefined,
    };

    await overrideMutation.mutateAsync(payload);
  };

  return (
    <div className="space-y-8">
      {/* SaaS Financial & Operational KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Monthly Recurring Revenue (MRR)
            </CardTitle>
            <CreditCard className="w-4 h-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-extrabold text-foreground">
              ₹{Number(metrics?.mrr || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Annualized (ARR): ₹{Number(metrics?.arr || 0).toLocaleString("en-IN")}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Active Paid Clinics
            </CardTitle>
            <Building2 className="w-4 h-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-extrabold text-emerald-600">
              {metrics?.active_paid_subscriptions || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Total Enrolled Facilities: {metrics?.total_clinics_enrolled || 0}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Active Free Trials
            </CardTitle>
            <Clock className="w-4 h-4 text-amber-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-extrabold text-amber-600">
              {metrics?.trialing_subscriptions || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Past Due: {metrics?.past_due_subscriptions || 0}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              30-Day Churn Rate
            </CardTitle>
            <TrendingUp className="w-4 h-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-extrabold text-foreground">
              {metrics?.churn_rate_percentage || 0}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Cancelled / Expired in 30d
            </p>
          </CardContent>
        </Card>
      </div>

      {overrideSuccess && (
        <div className="flex items-center justify-between rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>{overrideSuccess}</span>
          </div>
          <button onClick={() => setOverrideSuccess(null)} className="text-xs font-bold text-emerald-700">
            Dismiss
          </button>
        </div>
      )}

      {/* Plans Distribution & Quota Management */}
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-bold">Configured SaaS Tiers</CardTitle>
          <CardDescription className="text-xs">
            Dynamic subscription plans, active clinic counts, and pricing tiers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="py-3 px-4">Plan Name</th>
                  <th className="py-3 px-4">Tier</th>
                  <th className="py-3 px-4">Interval</th>
                  <th className="py-3 px-4">Price</th>
                  <th className="py-3 px-4">Max Doctors</th>
                  <th className="py-3 px-4">Max Staff</th>
                  <th className="py-3 px-4">Active Clinics</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {plans.map((p) => {
                  const dist = metrics?.plan_distribution?.find((d) => d.plan_id === p.id);
                  return (
                    <tr key={p.id} className="hover:bg-muted/10">
                      <td className="py-3 px-4 font-semibold text-foreground">{p.name}</td>
                      <td className="py-3 px-4">
                        <Badge variant="outline">{p.tier}</Badge>
                      </td>
                      <td className="py-3 px-4 text-xs text-muted-foreground">{p.billing_interval}</td>
                      <td className="py-3 px-4 font-bold">
                        {Number(p.price) === 0 ? "Free" : `₹${Number(p.price).toLocaleString("en-IN")}`}
                      </td>
                      <td className="py-3 px-4 text-xs text-muted-foreground">
                        {p.max_doctors === null ? "Unlimited" : p.max_doctors}
                      </td>
                      <td className="py-3 px-4 text-xs text-muted-foreground">
                        {p.max_staff === null ? "Unlimited" : p.max_staff}
                      </td>
                      <td className="py-3 px-4 font-semibold text-foreground">
                        {dist ? dist.active_clinics : 0}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant="outline"
                          className={p.is_active ? "bg-emerald-50 text-emerald-700 border-emerald-300" : "bg-muted"}
                        >
                          {p.is_active ? "Active" : "Disabled"}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Clinic Subscriptions Oversight Table */}
      <Card className="shadow-sm">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <CardTitle className="text-base font-bold">Clinic Subscriptions & Quota Enforcement</CardTitle>
              <CardDescription className="text-xs">
                Inspect live usage, status, and execute administrative overrides.
              </CardDescription>
            </div>

            <div className="flex items-center space-x-3">
              <div className="relative w-64">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search clinic name..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full rounded-lg border bg-background pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="TRIALING">Trialing</option>
                <option value="PAST_DUE">Past Due</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="EXPIRED">Expired</option>
                <option value="SUSPENDED">Suspended</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="py-3 px-4">Clinic Facility</th>
                  <th className="py-3 px-4">Plan Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Doctors Quota</th>
                  <th className="py-3 px-4">Staff Quota</th>
                  <th className="py-3 px-4">Cycle Ends</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {clinicSubs.map((sub: any) => (
                  <tr key={sub.clinic_id} className="hover:bg-muted/10">
                    <td className="py-3 px-4 font-semibold text-foreground">{sub.clinic_name}</td>
                    <td className="py-3 px-4 font-medium text-foreground">{sub.subscription?.plan_name}</td>
                    <td className="py-3 px-4">
                      <Badge
                        variant="outline"
                        className={
                          sub.subscription?.status === "ACTIVE"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                            : sub.subscription?.status === "TRIALING"
                            ? "bg-amber-50 text-amber-700 border-amber-300"
                            : "bg-muted text-muted-foreground"
                        }
                      >
                        {sub.subscription?.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {sub.doctors?.current} / {sub.doctors?.is_unlimited ? "Unlimited" : sub.doctors?.limit}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {sub.staff?.current} / {sub.staff?.is_unlimited ? "Unlimited" : sub.staff?.limit}
                    </td>
                    <td className="py-3 px-4 text-xs text-muted-foreground">
                      {sub.subscription?.current_period_end
                        ? new Date(sub.subscription.current_period_end).toLocaleDateString("en-IN", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })
                        : "Continuous"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs h-7"
                        onClick={() => handleOpenOverride(sub)}
                      >
                        <Settings className="w-3.5 h-3.5 mr-1" />
                        Admin Override
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Subscription Audit Event Stream */}
      <Card className="shadow-sm">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <History className="w-4 h-4 text-primary" />
            <CardTitle className="text-base font-bold">Subscription Audit Event Stream</CardTitle>
          </div>
          <CardDescription className="text-xs">
            Append-only event log recording all upgrades, downgrades, cancellations, and administrative actions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b bg-muted/40 font-semibold uppercase tracking-wider text-muted-foreground">
                  <th className="py-2.5 px-4">Timestamp</th>
                  <th className="py-2.5 px-4">Clinic</th>
                  <th className="py-2.5 px-4">Event Type</th>
                  <th className="py-2.5 px-4">Transition</th>
                  <th className="py-2.5 px-4">Actor</th>
                  <th className="py-2.5 px-4">Reason / Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y text-muted-foreground">
                {auditEvents.map((evt: SubscriptionEvent) => (
                  <tr key={evt.id} className="hover:bg-muted/10">
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      {new Date(evt.created_at).toLocaleString("en-IN", {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="py-2.5 px-4 font-semibold text-foreground">{evt.old_plan_name || evt.new_plan_name || "Clinic"}</td>
                    <td className="py-2.5 px-4 font-mono font-medium text-foreground">{evt.event_type}</td>
                    <td className="py-2.5 px-4">
                      {evt.old_status ? `${evt.old_status} → ` : ""}
                      <span className="font-semibold text-foreground">{evt.new_status}</span>
                    </td>
                    <td className="py-2.5 px-4">{evt.triggered_by_name}</td>
                    <td className="py-2.5 px-4 max-w-xs truncate">{evt.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Admin Override Dialog */}
      {isOverrideModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border bg-card p-6 shadow-xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b">
              <h3 className="font-bold text-lg text-foreground">Clinic Subscription Override</h3>
              <button
                onClick={() => setIsOverrideModalOpen(false)}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3.5 text-xs">
              <div>
                <label className="font-semibold block mb-1">Status Override:</label>
                <select
                  value={overrideStatus}
                  onChange={(e) => setOverrideStatus(e.target.value as SubscriptionStatus)}
                  className="w-full rounded-lg border bg-background p-2"
                >
                  <option value="">Keep Existing</option>
                  <option value="ACTIVE">ACTIVE (Comp / Reinstated)</option>
                  <option value="SUSPENDED">SUSPENDED (Restrict Access)</option>
                  <option value="EXPIRED">EXPIRED (Shift to Free)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold block mb-1">Assign Plan (Comp / Change):</label>
                <select
                  value={overridePlanId}
                  onChange={(e) => setOverridePlanId(e.target.value)}
                  className="w-full rounded-lg border bg-background p-2"
                >
                  <option value="">Keep Current Plan</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.tier} - ₹{p.price})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Custom Doctor Limit:</label>
                  <input
                    type="number"
                    placeholder="e.g. 15 (empty=plan default)"
                    value={overrideDocLimit}
                    onChange={(e) => setOverrideDocLimit(e.target.value)}
                    className="w-full rounded-lg border bg-background p-2"
                  />
                </div>
                <div>
                  <label className="font-semibold block mb-1">Custom Staff Limit:</label>
                  <input
                    type="number"
                    placeholder="e.g. 10 (empty=plan default)"
                    value={overrideStaffLimit}
                    onChange={(e) => setOverrideStaffLimit(e.target.value)}
                    className="w-full rounded-lg border bg-background p-2"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold block mb-1">Extend Access Duration (Days):</label>
                <input
                  type="number"
                  placeholder="e.g. 30 (extends period end date)"
                  value={overrideExtendDays}
                  onChange={(e) => setOverrideExtendDays(e.target.value)}
                  className="w-full rounded-lg border bg-background p-2"
                />
              </div>

              <div>
                <label className="font-semibold block mb-1">Reason for Override (Mandatory Audit):</label>
                <input
                  type="text"
                  placeholder="e.g. Special institutional pilot agreement"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  className="w-full rounded-lg border bg-background p-2"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end space-x-3 pt-3 border-t">
              <Button variant="outline" size="sm" onClick={() => setIsOverrideModalOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSubmitOverride} disabled={overrideMutation.isPending}>
                {overrideMutation.isPending ? "Applying..." : "Apply Override"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
