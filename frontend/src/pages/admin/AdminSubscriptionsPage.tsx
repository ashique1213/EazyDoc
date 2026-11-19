import { CreditCard } from "lucide-react";
import { AdminSubscriptionTab } from "@/features/subscriptions";

export function AdminSubscriptionsPage() {
  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col gap-2 border-b pb-5">
        <div className="flex items-center space-x-2">
          <CreditCard className="w-6 h-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            SaaS Subscriptions & Billing
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Platform-wide SaaS monetization metrics, subscription plans, clinic quota overrides, and audit trails.
        </p>
      </div>

      <AdminSubscriptionTab />
    </div>
  );
}

export default AdminSubscriptionsPage;
