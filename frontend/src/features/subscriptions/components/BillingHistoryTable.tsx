import { FileText, ExternalLink, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SubscriptionInvoice } from "../types";

interface BillingHistoryTableProps {
  invoices: SubscriptionInvoice[];
  clinicId: string;
}

export function BillingHistoryTable({ invoices, clinicId }: BillingHistoryTableProps) {
  if (!invoices || invoices.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground">
        <FileText className="w-12 h-12 mx-auto text-muted-foreground/40 mb-3" />
        <h3 className="font-semibold text-foreground text-base">No Billing Invoices Yet</h3>
        <p className="text-sm mt-1">Completed subscription charges will appear here with downloadable tax invoices.</p>
      </div>
    );
  }

  const handleOpenInvoice = (invoiceId: string) => {
    // Open printable HTML view
    const url = `/api/v1/subscriptions/clinics/${clinicId}/invoices/${invoiceId}/html/`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b bg-muted/50 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <th className="py-3.5 px-6">Invoice Number</th>
              <th className="py-3.5 px-4">Plan</th>
              <th className="py-3.5 px-4">Billing Period</th>
              <th className="py-3.5 px-4">Subtotal</th>
              <th className="py-3.5 px-4">GST (18%)</th>
              <th className="py-3.5 px-4">Total Amount</th>
              <th className="py-3.5 px-4">Status</th>
              <th className="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {invoices.map((inv) => (
              <tr key={inv.id} className="hover:bg-muted/10 transition-colors">
                <td className="py-3.5 px-6 font-semibold text-foreground">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-primary shrink-0" />
                    <span>{inv.invoice_number}</span>
                  </div>
                </td>
                <td className="py-3.5 px-4 text-foreground font-medium">{inv.plan_name}</td>
                <td className="py-3.5 px-4 text-xs text-muted-foreground">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>
                      {new Date(inv.billing_period_start).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </td>
                <td className="py-3.5 px-4 text-muted-foreground">
                  ₹{Number(inv.subtotal_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </td>
                <td className="py-3.5 px-4 text-muted-foreground">
                  ₹{Number(inv.tax_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </td>
                <td className="py-3.5 px-4 font-bold text-foreground">
                  ₹{Number(inv.total_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </td>
                <td className="py-3.5 px-4">
                  <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold text-xs">
                    {inv.status}
                  </Badge>
                </td>
                <td className="py-3.5 px-6 text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs font-medium"
                    onClick={() => handleOpenInvoice(inv.id)}
                  >
                    <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                    View / Print
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
