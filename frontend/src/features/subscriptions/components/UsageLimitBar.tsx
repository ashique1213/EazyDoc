import { AlertCircle, CheckCircle2 } from "lucide-react";
import type { UsageQuota } from "../types";

interface UsageLimitBarProps {
  label: string;
  quota: UsageQuota;
  unitName?: string;
  icon?: React.ReactNode;
}

export function UsageLimitBar({ label, quota, unitName = "used", icon }: UsageLimitBarProps) {
  const isAtLimit = !quota.is_unlimited && quota.limit !== null && quota.current >= quota.limit;
  const isNearLimit = !quota.is_unlimited && quota.limit !== null && quota.percentage >= 80;

  let progressColor = "bg-primary";
  if (isAtLimit) {
    progressColor = "bg-destructive";
  } else if (isNearLimit) {
    progressColor = "bg-amber-500";
  }

  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {icon && <div className="text-muted-foreground">{icon}</div>}
          <span className="text-sm font-semibold text-foreground">{label}</span>
        </div>
        <div className="text-sm font-medium">
          {quota.is_unlimited ? (
            <span className="inline-flex items-center text-emerald-600 font-semibold text-xs bg-emerald-50 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              {quota.current} (Unlimited)
            </span>
          ) : (
            <span className={isAtLimit ? "text-destructive font-bold" : "text-muted-foreground"}>
              {quota.current} / {quota.limit} {unitName}
            </span>
          )}
        </div>
      </div>

      {!quota.is_unlimited && (
        <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${progressColor}`}
            style={{ width: `${Math.min(100, quota.percentage)}%` }}
          />
        </div>
      )}

      {isAtLimit && quota.restriction_message && (
        <div className="flex items-start space-x-2 rounded-lg bg-destructive/10 p-2.5 text-xs text-destructive">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{quota.restriction_message}</span>
        </div>
      )}
    </div>
  );
}
