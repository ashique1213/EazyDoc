import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CalendarDays } from "lucide-react";
import type { PeakDayPoint } from "../types";

interface PeakDaysChartProps {
  data: PeakDayPoint[];
  title?: string;
  description?: string;
}

export const PeakDaysChart: React.FC<PeakDaysChartProps> = ({
  data,
  title = "Peak Booking Days",
  description = "Appointment demand distribution by day of the week",
}) => {
  const chartData = data.map((d) => ({
    day: d.day.slice(0, 3), // Mon, Tue, etc.
    fullDay: d.day,
    count: d.count,
    percentage: d.percentage,
  }));

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-bold flex items-center gap-2">
          <CalendarDays className="w-4 h-4 text-primary" />
          {title}
        </CardTitle>
        <CardDescription className="text-xs">{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[250px] w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={(val: unknown) => [
                  `${String(val ?? 0)} visits`,
                  "Appointments",
                ]}
                labelFormatter={(lbl, items) => {
                  if (items && items[0]) {
                    return items[0].payload.fullDay;
                  }
                  return lbl;
                }}
                contentStyle={{
                  backgroundColor: "rgba(255, 255, 255, 0.95)",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="count" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
