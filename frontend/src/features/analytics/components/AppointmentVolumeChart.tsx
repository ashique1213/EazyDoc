import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar } from "lucide-react";
import type { DailyAppointmentPoint } from "../types";

interface AppointmentVolumeChartProps {
  data: DailyAppointmentPoint[];
  title?: string;
  description?: string;
}

export const AppointmentVolumeChart: React.FC<AppointmentVolumeChartProps> = ({
  data,
  title = "Appointment Volume Trends",
  description = "Daily distribution of completed, confirmed, and cancelled bookings",
}) => {
  const formattedData = data.map((d) => ({
    date: d.date.slice(5),
    fullDate: d.date,
    total: d.total,
    completed: d.completed,
    confirmed: d.confirmed,
    cancelled: d.cancelled,
  }));

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-bold flex items-center gap-2">
          <Calendar className="w-4 h-4 text-primary" />
          {title}
        </CardTitle>
        <CardDescription className="text-xs">{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={formattedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(255, 255, 255, 0.95)",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  fontSize: "12px",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "12px" }}
                formatter={(val) => {
                  const labels: Record<string, string> = {
                    completed: "Completed Visits",
                    confirmed: "Upcoming Confirmed",
                    cancelled: "Cancelled",
                  };
                  return <span className="text-xs font-medium text-slate-700">{labels[val] || val}</span>;
                }}
              />
              <Bar dataKey="completed" fill="#10b981" radius={[4, 4, 0, 0]} stackId="a" />
              <Bar dataKey="confirmed" fill="#3b82f6" radius={[0, 0, 0, 0]} stackId="a" />
              <Bar dataKey="cancelled" fill="#ef4444" radius={[4, 4, 0, 0]} stackId="a" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

