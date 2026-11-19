import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CreditCard,
  AlertTriangle,
  Clock,
  Building2,
  Calendar,
  Users,
  CheckCircle2,
  Info,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/features/auth";
import { ClinicSwitcher, useActiveClinic } from "@/features/clinicOperations";
import {
  BillingHistoryTable,
  CancelSubscriptionModal,
  PlanCard,
  PlanComparisonTable,
  UpgradeModal,
  UsageLimitBar,
  subscriptionsApi,
  useSubscriptionCheckout,
  type BillingInterval,
  type SubscriptionPlan,
} from "@/features/subscriptions";

export function ClinicSubscriptionPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const { activeClinic, activeClinicId } = useActiveClinic();

  const [billingInterval, setBillingInterval] = useState<BillingInterval>("MONTHLY");
  const [selectedPlanForUpgrade, setSelectedPlanForUpgrade] = useState<SubscriptionPlan | null>(null);
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Fetch clinic entitlements summary
  const {
    data: entitlements,
    refetch: refetchEntitlements,
  } = useQuery({
    queryKey: ["clinic-subscription", activeClinicId],
    queryFn: () => subscriptionsApi.getClinicSubscription(activeClinicId!),
    enabled: !!activeClinicId,
  });

  // Fetch all subscription plans
  const { data: plans = [] } = useQuery({
    queryKey: ["subscription-plans"],
    queryFn: () => subscriptionsApi.getPlans(),
  });

  // Fetch clinic invoices
  const { data: invoices = [], refetch: refetchInvoices } = useQuery({
    queryKey: ["clinic-invoices", activeClinicId],
    queryFn: () => subscriptionsApi.getClinicInvoices(activeClinicId!),
    enabled: !!activeClinicId,
  });

  // Razorpay Checkout Hook
  const { initiateCheckout, isProcessing, errorMessage: checkoutError } = useSubscriptionCheckout({
    onSuccess: () => {
      setIsUpgradeModalOpen(false);
      setSelectedPlanForUpgrade(null);
      setActionSuccessMsg("Subscription upgraded successfully! Your new quotas are active immediately.");
      refetchEntitlements();
      refetchInvoices();
      queryClient.invalidateQueries({ queryKey: ["clinic-subscription", activeClinicId] });
    },
  });

  // Cancellation mutation
  const cancelMutation = useMutation({
    mutationFn: (reason: string) => subscriptionsApi.cancelSubscription(activeClinicId!, reason),
    onSuccess: () => {
      setActionSuccessMsg("Cancellation scheduled. You will keep full access until your billing period concludes.");
      refetchEntitlements();
      queryClient.invalidateQueries({ queryKey: ["clinic-subscription", activeClinicId] });
    },
  });

  const handleSelectPlan = (plan: SubscriptionPlan) => {
    setSelectedPlanForUpgrade(plan);
    setIsUpgradeModalOpen(true);
  };

  const handleConfirmCheckout = async (plan: SubscriptionPlan) => {
    if (!activeClinicId) return;
    await initiateCheckout({
      clinicId: activeClinicId,
      planId: plan.id,
      billingInterval: billingInterval,
      userEmail: user?.email,
      userName: user?.first_name ? `${user.first_name} ${user.last_name}` : undefined,
    });
  };

  const handleConfirmCancel = async (reason: string) => {
    await cancelMutation.mutateAsync(reason);
  };

  // Filter plans for the selected interval
  const displayedPlans = plans.filter(
    (p) => p.billing_interval === billingInterval || p.tier === "FREE"
  );

  const subscription = entitlements?.subscription;
  const isTrial = subscription?.is_in_trial;
  const isPastDue = subscription?.status === "PAST_DUE";
  const isCancelled = subscription?.status === "CANCELLED" || subscription?.cancel_at_period_end;

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Top Header & Clinic Switcher */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b">
        <div>
          <div className="flex items-center space-x-2">
            <CreditCard className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">SaaS Subscription & Billing</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your clinic plan, resource seat quotas, billing cycles, and official invoices.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ClinicSwitcher />
        </div>
      </div>

      {actionSuccessMsg && (
        <div className="flex items-center justify-between rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>{actionSuccessMsg}</span>
          </div>
          <button
            onClick={() => setActionSuccessMsg(null)}
            className="text-emerald-700 hover:text-emerald-900 text-xs font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {checkoutError && (
        <div className="flex items-center space-x-2 rounded-xl bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{checkoutError}</span>
        </div>
      )}

      {/* Warnings: Trial, Past Due, Cancellation */}
      {isTrial && (
        <div className="flex items-center justify-between rounded-2xl bg-amber-500/10 border border-amber-500/20 p-4 text-amber-900 dark:text-amber-200">
          <div className="flex items-center space-x-3">
            <Clock className="w-5 h-5 text-amber-600" />
            <div>
              <p className="font-semibold text-sm">
                14-Day Free Trial Active ({subscription?.days_remaining} days remaining)
              </p>
              <p className="text-xs text-amber-700 dark:text-amber-300">
                You are currently exploring full {subscription?.plan_name} capabilities. Choose a paid tier anytime to keep your team active.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            className="bg-amber-600 hover:bg-amber-700 text-white font-semibold"
            onClick={() => {
              const starter = plans.find((p) => p.tier === "STARTER" && p.billing_interval === billingInterval);
              if (starter) handleSelectPlan(starter);
            }}
          >
            Upgrade Now
          </Button>
        </div>
      )}

      {isPastDue && (
        <div className="flex items-center justify-between rounded-2xl bg-destructive/10 border border-destructive/20 p-4 text-destructive">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5" />
            <div>
              <p className="font-bold text-sm">Payment Past Due (Grace Period Active)</p>
              <p className="text-xs">
                Your last renewal charge was unsuccessful. Please update your payment method to avoid service interruption.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => {
              const current = plans.find((p) => p.code === subscription?.plan_code);
              if (current) handleSelectPlan(current);
            }}
          >
            Retry Payment
          </Button>
        </div>
      )}

      {isCancelled && (
        <div className="flex items-center space-x-3 rounded-2xl bg-muted p-4 text-muted-foreground text-sm border">
          <Info className="w-5 h-5 text-foreground shrink-0" />
          <div>
            <span className="font-semibold text-foreground">Cancellation Pending: </span>
            You have scheduled cancellation. You retain full access until{" "}
            {subscription?.current_period_end
              ? new Date(subscription.current_period_end).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })
              : "the period concludes"}
            . Your clinic data will remain safe.
          </div>
        </div>
      )}

      {/* Current Subscription Status & Quota Cards */}
      {entitlements && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Plan Card */}
          <Card className="lg:col-span-1 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold">Current Subscription</CardTitle>
                <Badge
                  variant="outline"
                  className={
                    subscription?.status === "ACTIVE"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-300 font-bold"
                      : subscription?.status === "TRIALING"
                      ? "bg-amber-50 text-amber-700 border-amber-300 font-bold"
                      : "bg-muted text-muted-foreground font-bold"
                  }
                >
                  {subscription?.status}
                </Badge>
              </div>
              <CardDescription className="text-xs">
                Managed facility: <strong className="text-foreground">{activeClinic?.name}</strong>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-2xl font-extrabold text-foreground">{subscription?.plan_name}</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {subscription?.price === 0
                    ? "Free Community Edition"
                    : `₹${subscription?.price.toLocaleString("en-IN")} billed ${subscription?.billing_interval.toLowerCase()}`}
                </div>
              </div>

              <div className="space-y-1.5 text-xs text-muted-foreground border-t pt-3">
                <div className="flex justify-between">
                  <span>Period Active:</span>
                  <span className="text-foreground font-medium">
                    {subscription?.current_period_start
                      ? new Date(subscription.current_period_start).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                        })
                      : "N/A"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Renews / Expires:</span>
                  <span className="text-foreground font-medium">
                    {subscription?.current_period_end
                      ? new Date(subscription.current_period_end).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })
                      : "Continuous"}
                  </span>
                </div>
              </div>

              {!isCancelled && subscription?.status !== "EXPIRED" && subscription?.tier !== "FREE" && (
                <div className="pt-2 border-t">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full text-xs text-destructive hover:bg-destructive/10"
                    onClick={() => setIsCancelModalOpen(true)}
                  >
                    Cancel Subscription...
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Real-Time Quota Usage Bars */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Clinic License Quotas & Limits
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <UsageLimitBar
                label="Doctors"
                quota={entitlements.doctors}
                unitName="doctors"
                icon={<Building2 className="w-4 h-4 text-indigo-600" />}
              />
              <UsageLimitBar
                label="Staff Seats"
                quota={entitlements.staff}
                unitName="staff"
                icon={<Users className="w-4 h-4 text-purple-600" />}
              />
              <UsageLimitBar
                label="Monthly Bookings"
                quota={entitlements.appointments}
                unitName="bookings"
                icon={<Calendar className="w-4 h-4 text-emerald-600" />}
              />
            </div>
          </div>
        </div>
      )}

      {/* Available Plans Catalog */}
      <div className="space-y-6 pt-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-foreground">Available SaaS Plans</h2>
            <p className="text-xs text-muted-foreground">
              Scale up your clinic operations seamlessly. Switch intervals or tiers anytime with instant activation.
            </p>
          </div>

          {/* Monthly vs Yearly Switcher */}
          <div className="flex items-center space-x-2 bg-muted p-1 rounded-xl self-start">
            <button
              onClick={() => setBillingInterval("MONTHLY")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                billingInterval === "MONTHLY"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => setBillingInterval("YEARLY")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                billingInterval === "YEARLY"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span>Annual Billing</span>
              <Badge className="bg-emerald-600 text-white text-[10px] px-1.5 py-0">Save 17%</Badge>
            </button>
          </div>
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {displayedPlans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              billingInterval={billingInterval}
              isCurrent={subscription?.plan_code === plan.code}
              onSelect={handleSelectPlan}
              isLoading={isProcessing}
            />
          ))}
        </div>
      </div>

      {/* Feature Comparison Matrix */}
      <div className="space-y-4 pt-6">
        <h3 className="text-lg font-bold text-foreground">Plan Quota & Feature Comparison</h3>
        <PlanComparisonTable plans={displayedPlans} />
      </div>

      {/* Invoicing and Billing History */}
      <div className="space-y-4 pt-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-foreground">Billing Invoices & History</h3>
            <p className="text-xs text-muted-foreground">
              Official tax invoices for your clinic accounting and GST filings.
            </p>
          </div>
        </div>
        {activeClinicId && <BillingHistoryTable invoices={invoices} clinicId={activeClinicId} />}
      </div>

      {/* Modals */}
      <UpgradeModal
        isOpen={isUpgradeModalOpen}
        onClose={() => {
          setIsUpgradeModalOpen(false);
          setSelectedPlanForUpgrade(null);
        }}
        plan={selectedPlanForUpgrade}
        billingInterval={billingInterval}
        onConfirmCheckout={handleConfirmCheckout}
        isProcessing={isProcessing}
      />

      <CancelSubscriptionModal
        isOpen={isCancelModalOpen}
        onClose={() => setIsCancelModalOpen(false)}
        onConfirm={handleConfirmCancel}
        periodEndDate={subscription?.current_period_end}
      />
    </div>
  );
}

export default ClinicSubscriptionPage;
