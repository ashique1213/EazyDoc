import { Check, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { SubscriptionPlan, BillingInterval } from "../types";

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  plan: SubscriptionPlan | null;
  billingInterval: BillingInterval;
  onConfirmCheckout: (plan: SubscriptionPlan) => Promise<void>;
  isProcessing?: boolean;
}

export function UpgradeModal({
  isOpen,
  onClose,
  plan,
  billingInterval,
  onConfirmCheckout,
  isProcessing = false,
}: UpgradeModalProps) {
  if (!isOpen || !plan) return null;

  const priceNum = Number(plan.price);
  const isFree = priceNum === 0;

  // 18% GST inclusive calculation
  const subtotal = isFree ? 0 : Math.round((priceNum / 1.18) * 100) / 100;
  const gst = isFree ? 0 : Math.round((priceNum - subtotal) * 100) / 100;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl border bg-card p-6 shadow-xl animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between pb-3 border-b">
          <div>
            <h3 className="font-bold text-lg text-foreground">
              {isFree ? "Switch to Free Community" : `Upgrade to ${plan.name}`}
            </h3>
            <p className="text-xs text-muted-foreground">
              Billed {billingInterval.toLowerCase()} • 18% GST Included
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-4 space-y-4">
          <div className="rounded-xl bg-muted/40 p-4 space-y-2 text-xs">
            <div className="flex justify-between text-muted-foreground">
              <span>Plan Base Cost ({billingInterval.toLowerCase()}):</span>
              <span className="font-semibold text-foreground">
                ₹{subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>Statutory GST (18.00%):</span>
              <span className="font-semibold text-foreground">
                ₹{gst.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="flex justify-between text-sm font-extrabold text-foreground border-t pt-2">
              <span>Total Amount Payable:</span>
              <span className="text-primary text-base">
                ₹{priceNum.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Key Quotas Unlocked
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center space-x-1.5 rounded-lg border p-2 bg-card">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>
                  <strong>{plan.max_doctors ?? "Unlimited"}</strong> Doctors
                </span>
              </div>
              <div className="flex items-center space-x-1.5 rounded-lg border p-2 bg-card">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>
                  <strong>{plan.max_staff ?? "Unlimited"}</strong> Staff Seats
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-xs text-muted-foreground">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Instant activation upon verified gateway payment. Secure Razorpay checkout.</span>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end space-x-3 pt-3 border-t">
          <Button variant="outline" onClick={onClose} disabled={isProcessing}>
            Cancel
          </Button>
          <Button
            onClick={() => onConfirmCheckout(plan)}
            disabled={isProcessing}
            className="font-semibold"
          >
            {isProcessing ? "Processing..." : isFree ? "Confirm Free Tier" : `Proceed to Pay ₹${priceNum.toLocaleString("en-IN")}`}
          </Button>
        </div>
      </div>
    </div>
  );
}
