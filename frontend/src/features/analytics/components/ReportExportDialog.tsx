import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, X, FileText, Check } from "lucide-react";
import type { AnalyticsFilterParams } from "../types";
import { analyticsApi } from "../api";

interface ReportExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  filters: AnalyticsFilterParams;
  isAdmin?: boolean;
  clinicId?: string;
}

export const ReportExportDialog: React.FC<ReportExportDialogProps> = ({
  isOpen,
  onClose,
  filters,
  isAdmin = true,
  clinicId,
}) => {
  const [selectedType, setSelectedType] = useState<string>("revenue");
  const [isExporting, setIsExporting] = useState<boolean>(false);

  if (!isOpen) return null;

  const adminOptions = [
    { id: "revenue", label: "Revenue & Settlements", desc: "Gross collections, platform commission, and clinic payable ledger" },
    { id: "clinics", label: "Clinic Performance", desc: "Comparative booking volume, doctors, completion rate, and earnings" },
    { id: "doctors", label: "Doctor Practice Report", desc: "Multi-clinic appointments, fees, completion rate, and revenues" },
    { id: "appointments", label: "Appointments Summary", desc: "Individual bookings with masked patient names and consultation fee" },
    { id: "reconciliation", label: "Financial Reconciliation", desc: "Audit trail of verified transactions and discrepancy logs" },
  ];

  const clinicOptions = [
    { id: "revenue", label: "Clinic Revenue Ledger", desc: "Gross receipts, platform commission deducted, and net clinic share" },
    { id: "doctors", label: "Clinic Doctor Performance", desc: "Practice stats, fees, and revenue generated per doctor" },
    { id: "appointments", label: "Appointments List", desc: "Scheduled visits, statuses, and masked patient identifiers" },
    { id: "cancellations", label: "Cancellations Audit", desc: "Cancelled appointments with recorded cancellation reasons" },
  ];

  const options = isAdmin ? adminOptions : clinicOptions;

  const handleDownload = async () => {
    try {
      setIsExporting(true);
      if (isAdmin) {
        await analyticsApi.downloadAdminReport(selectedType, filters);
      } else if (clinicId) {
        await analyticsApi.downloadClinicReport(clinicId, selectedType, filters);
      }
      onClose();
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="bg-card border rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-primary/10 rounded-lg text-primary">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-foreground">Export Analytics Report</h2>
              <p className="text-xs text-muted-foreground">
                Download structured CSV files respecting active date range filters
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground pb-2 border-b">
            <span>Active Range:</span>
            <Badge variant="outline" className="text-[11px] font-semibold text-primary">
              {filters.period?.replace(/_/g, " ").toUpperCase() || "LAST 30 DAYS"}
            </Badge>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground">Select Report Dataset:</label>
            <div className="grid gap-2">
              {options.map((opt) => {
                const isSelected = selectedType === opt.id;
                return (
                  <div
                    key={opt.id}
                    onClick={() => setSelectedType(opt.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                      isSelected
                        ? "border-primary bg-primary/5 shadow-xs"
                        : "border-border hover:bg-muted/50"
                    }`}
                  >
                    <div
                      className={`p-1.5 rounded-md mt-0.5 ${
                        isSelected ? "bg-primary text-white" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <div className="text-xs font-bold text-foreground flex items-center justify-between">
                        {opt.label}
                        {isSelected && <Check className="w-3.5 h-3.5 text-primary" />}
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-0.5">{opt.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2.5 p-4 bg-muted/40 border-t">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isExporting}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleDownload} disabled={isExporting} className="gap-2">
            <Download className="w-3.5 h-3.5" />
            <span>{isExporting ? "Generating CSV..." : "Download CSV"}</span>
          </Button>
        </div>
      </div>
    </div>
  );
};

