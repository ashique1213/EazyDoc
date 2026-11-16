import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CreditCard } from "lucide-react";
import type { PaymentStatusPoint } from "../types";

interface PaymentStatusPieChartProps {
  data: PaymentStatusPoint[];
  title?: string;
  description?: string;
}

const COLORS: Record<string, string> = {
  PAID: "#10b981", // Emerald
  FAILED: "#ef4444", // Rose
  PENDING: "#f59e0b", // Amber
  REFUNDED: "#64748b", // Slate
};

export const PaymentStatusPieChart: React.FC<PaymentStatusPieChartProps> = ({
  data,
  title = "Payment Status Distribution",
  description = "Proportion of settled, failed, pending, and refunded transactions",
}) => {
  const chartData = data.filter((d) => d.count > 0);

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-bold flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-primary" />
          {title}
        </CardTitle>
        <CardDescription className="text-xs">{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full pt-4">
          {chartData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
              No transactions recorded in this period.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="count"
                  nameKey="status"
                >
                  {chartData.map((entry) => (
                    <Cell key={entry.status} fill={COLORS[entry.status] || "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: unknown, name?: unknown) => [
                    `${String(val ?? 0)} payments`,
                    String(name || ""),
                  ]}
                  contentStyle={{
                    backgroundColor: "rgba(255, 255, 255, 0.95)",
                    borderRadius: "8px",
                    border: "1px solid #e2e8f0",
                    fontSize: "12px",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  formatter={(val) => <span className="text-xs font-medium text-slate-700">{val}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
