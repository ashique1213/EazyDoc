import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, AlertTriangle, ShieldCheck } from "lucide-react";
import type { FinancialReconciliationData } from "../types";

interface FinancialReconciliationTableProps {
  data: FinancialReconciliationData;
}

export const FinancialReconciliationTable: React.FC<FinancialReconciliationTableProps> = ({ data }) => {
  const isHealthy = data.health_status === "HEALTHY";

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-primary" />
                Financial Reconciliation & Integrity Ledger
              </CardTitle>
              <Badge
                variant={isHealthy ? "outline" : "destructive"}
                className={`text-xs py-0.5 px-2 font-semibold ${
                  isHealthy
                    ? "bg-emerald-50 text-emerald-700 border-emerald-300 flex items-center gap-1"
                    : "flex items-center gap-1"
                }`}
              >
                {isHealthy ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    HEALTHY — ALL RECORDS BALANCED
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5" />
                    DISCREPANCIES DETECTED ({data.discrepancy_count})
                  </>
                )}
              </Badge>
            </div>
            <CardDescription className="text-xs mt-1">
              Cross-model automated verification comparing appointment schedules, payment gateway transactions, and commission ledger equations.
            </CardDescription>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="text-right">
              <span className="text-muted-foreground">Transactions Reconciled:</span>{" "}
              <span className="font-bold text-foreground">{data.total_reconciled_transactions}</span>
            </div>
            <div className="text-right">
              <span className="text-muted-foreground">Discrepancy Volume:</span>{" "}
              <span className="font-bold text-rose-600">₹{parseFloat(data.total_discrepancy_value).toFixed(2)}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-muted/50 border-y text-muted-foreground uppercase font-semibold text-[10px] tracking-wider">
              <tr>
                <th className="py-2.5 px-4">Discrepancy Type</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Clinic</th>
                <th className="py-2.5 px-3">Payment / Booking Ref</th>
                <th className="py-2.5 px-3 text-right">Amount (INR)</th>
                <th className="py-2.5 px-4">Audit Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.discrepancies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-emerald-600 font-medium text-xs">
                    <CheckCircle2 className="w-5 h-5 mx-auto mb-1 text-emerald-500" />
                    No financial anomalies detected. 100% of transactions satisfy accounting invariants.
                  </td>
                </tr>
              ) : (
                data.discrepancies.map((disc, idx) => (
                  <tr key={idx} className="hover:bg-muted/40 transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-foreground">
                      {disc.type}
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={disc.severity === "CRITICAL" ? "destructive" : "secondary"}
                        className="text-[10px] py-0 px-1.5"
                      >
                        {disc.severity}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-muted-foreground">
                      {disc.clinic_name}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-muted-foreground">
                      {disc.payment_id?.slice(0, 8) || disc.appointment_id?.slice(0, 8) || "N/A"}
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-rose-600">
                      ₹{parseFloat(disc.amount).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-muted-foreground">
                      {disc.description}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
};

