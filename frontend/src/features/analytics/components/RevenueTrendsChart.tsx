import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import type { DailyRevenuePoint } from "../types";

interface RevenueTrendsChartProps {
  data: DailyRevenuePoint[];
  title?: string;
  description?: string;
}

const formatCurrency = (val: number | string) => {
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return "₹0";
  return `₹${num.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
};

export const RevenueTrendsChart: React.FC<RevenueTrendsChartProps> = ({
  data,
  title = "Revenue & Commission Trends",
  description = "Daily timeline of gross collections, platform commission, and clinic payable share",
}) => {
  const formattedData = data.map((d) => ({
    date: d.date.slice(5), // MM-DD
    fullDate: d.date,
    gross: parseFloat(d.gross_revenue || "0"),
    commission: parseFloat(d.platform_commission || "0"),
    clinicShare: parseFloat(d.clinic_share || "0"),
    successfulCount: d.successful_payments,
  }));

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              {title}
            </CardTitle>
            <CardDescription className="text-xs">{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="grossGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="commissionGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="clinicGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
              <YAxis
                tickFormatter={(v) => `₹${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                formatter={(value: unknown, name?: unknown) => {
                  const key = String(name || "");
                  const labels: Record<string, string> = {
                    gross: "Gross Collected",
                    commission: "Platform Commission",
                    clinicShare: "Clinic Share",
                  };
                  return [formatCurrency(String(value ?? "0")), labels[key] || key];
                }}
                labelFormatter={(label, items) => {
                  if (items && items[0]) {
                    return items[0].payload.fullDate;
                  }
                  return label;
                }}
                contentStyle={{
                  backgroundColor: "rgba(255, 255, 255, 0.95)",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  fontSize: "12px",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                }}
              />
              <Legend
                formatter={(val) => {
                  const labels: Record<string, string> = {
                    gross: "Gross Collected",
                    commission: "Platform Commission (Net)",
                    clinicShare: "Clinic Share Payable",
                  };
                  return <span className="text-xs font-medium text-slate-700">{labels[val] || val}</span>;
                }}
                wrapperStyle={{ paddingTop: "12px" }}
              />
              <Area
                type="monotone"
                dataKey="gross"
                stroke="#3b82f6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#grossGradient)"
              />
              <Area
                type="monotone"
                dataKey="clinicShare"
                stroke="#8b5cf6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#clinicGradient)"
              />
              <Area
                type="monotone"
                dataKey="commission"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#commissionGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
