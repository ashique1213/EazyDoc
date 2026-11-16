import React from "react";
import { Button } from "@/components/ui/button";
import { Calendar, Download, RefreshCw } from "lucide-react";
import type { AnalyticsFilterParams, DateRangePeriod } from "../types";

interface AnalyticsFilterBarProps {
  filters: AnalyticsFilterParams;
  onFilterChange: (filters: AnalyticsFilterParams) => void;
  onRefresh: () => void;
  onOpenExport?: () => void;
  isRefreshing?: boolean;
}

const PRESETS: Array<{ label: string; value: DateRangePeriod }> = [
  { label: "Today", value: "today" },
  { label: "Yesterday", value: "yesterday" },
  { label: "7 Days", value: "last_7_days" },
  { label: "30 Days", value: "last_30_days" },
  { label: "90 Days", value: "last_90_days" },
  { label: "This Month", value: "this_month" },
  { label: "Prev Month", value: "previous_month" },
  { label: "This Year", value: "this_year" },
];

export const AnalyticsFilterBar: React.FC<AnalyticsFilterBarProps> = ({
  filters,
  onFilterChange,
  onRefresh,
  onOpenExport,
  isRefreshing = false,
}) => {
  const currentPeriod = filters.period || "last_30_days";

  const handlePresetClick = (preset: DateRangePeriod) => {
    onFilterChange({
      ...filters,
      period: preset,
      date_from: undefined,
      date_to: undefined,
    });
  };

  return (
    <div className="bg-card border rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      {/* Date Presets */}
      <div className="flex flex-wrap items-center gap-1.5">
        <div className="flex items-center gap-1.5 mr-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          <Calendar className="w-3.5 h-3.5 text-primary" />
          <span>Period:</span>
        </div>
        {PRESETS.map((p) => {
          const isSelected = currentPeriod === p.value;
          return (
            <Button
              key={p.value}
              variant={isSelected ? "default" : "outline"}
              size="sm"
              className={`h-8 px-3 text-xs font-medium rounded-lg transition-all ${
                isSelected ? "shadow-sm" : "hover:bg-muted text-muted-foreground"
              }`}
              onClick={() => handlePresetClick(p.value)}
            >
              {p.label}
            </Button>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 self-end md:self-center">
        {onOpenExport && (
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenExport}
            className="h-8 gap-1.5 text-xs font-medium border-dashed"
          >
            <Download className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Export CSV</span>
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          className="h-8 gap-1.5 text-xs font-medium"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-muted-foreground ${isRefreshing ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </Button>
      </div>
    </div>
  );
};
