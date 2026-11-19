import { Check, Sparkles, Shield, Zap, Award } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { SubscriptionPlan, BillingInterval } from "../types";

interface PlanCardProps {
  plan: SubscriptionPlan;
  isCurrent: boolean;
  onSelect: (plan: SubscriptionPlan) => void;
  isLoading?: boolean;
  billingInterval: BillingInterval;
}

export function PlanCard({ plan, isCurrent, onSelect, isLoading = false, billingInterval }: PlanCardProps) {
  const isPro = plan.tier === "PROFESSIONAL";
  const isEnterprise = plan.tier === "ENTERPRISE";

  const getTierIcon = () => {
    switch (plan.tier) {
      case "ENTERPRISE":
        return <Award className="w-5 h-5 text-purple-600" />;
      case "PROFESSIONAL":
        return <Sparkles className="w-5 h-5 text-blue-600" />;
      case "STARTER":
        return <Zap className="w-5 h-5 text-amber-600" />;
      default:
        return <Shield className="w-5 h-5 text-emerald-600" />;
    }
  };

  return (
    <div
      className={`relative flex flex-col justify-between rounded-2xl border bg-card p-6 shadow-sm transition-all hover:shadow-md ${
        isPro ? "border-primary ring-2 ring-primary/20" : ""
      } ${isCurrent ? "bg-accent/10 border-emerald-500" : ""}`}
    >
      {isPro && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <Badge className="bg-primary text-primary-foreground text-xs uppercase tracking-wider px-3 py-0.5">
            Most Popular
          </Badge>
        </div>
      )}

      {isCurrent && (
        <div className="absolute -top-3 right-4">
          <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 font-bold text-xs">
            Current Plan
          </Badge>
        </div>
      )}

      <div>
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-lg bg-muted">{getTierIcon()}</div>
          <div>
            <h3 className="font-bold text-lg text-foreground">{plan.name}</h3>
            <p className="text-xs text-muted-foreground">{plan.tier} Tier</p>
          </div>
        </div>

        <p className="mt-3 text-xs text-muted-foreground min-h-[36px]">{plan.description}</p>

        <div className="mt-4 flex items-baseline space-x-1 border-b pb-4">
          <span className="text-3xl font-extrabold text-foreground">
            {Number(plan.price) === 0 ? "Free" : `₹${Number(plan.price).toLocaleString("en-IN")}`}
          </span>
          {Number(plan.price) > 0 && (
            <span className="text-xs text-muted-foreground">
              /{billingInterval === "YEARLY" ? "year" : "month"}
            </span>
          )}
        </div>

        <div className="mt-4 space-y-2.5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Included Quotas</p>
          <div className="text-xs space-y-1.5 text-foreground">
            <div className="flex items-center space-x-2">
              <Check className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                <strong>{plan.max_doctors === null ? "Unlimited" : plan.max_doctors}</strong> Doctor
                {plan.max_doctors === 1 ? "" : "s"}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <Check className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                <strong>{plan.max_staff === null ? "Unlimited" : plan.max_staff}</strong> Staff Account
                {plan.max_staff === 1 ? "" : "s"}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <Check className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                <strong>{plan.max_appointments_per_month === null ? "Unlimited" : plan.max_appointments_per_month}</strong> Appointments/mo
              </span>
            </div>
          </div>

          <p className="pt-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Capabilities</p>
          <ul className="space-y-2 text-xs text-muted-foreground">
            {plan.features?.map((feat, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <Check className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                <span className="text-foreground">{feat}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t">
        <Button
          onClick={() => onSelect(plan)}
          disabled={isCurrent || isLoading}
          className="w-full"
          variant={isCurrent ? "outline" : isPro ? "default" : isEnterprise ? "secondary" : "outline"}
        >
          {isCurrent ? "Active Plan" : Number(plan.price) === 0 ? "Select Free Plan" : "Upgrade to this Plan"}
        </Button>
      </div>
    </div>
  );
}
