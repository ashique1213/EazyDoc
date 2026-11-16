import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Stethoscope, Search, Building2 } from "lucide-react";
import type { DoctorPerformanceItem } from "../types";

interface DoctorPerformanceTableProps {
  doctors: DoctorPerformanceItem[];
}

export const DoctorPerformanceTable: React.FC<DoctorPerformanceTableProps> = ({ doctors }) => {
  const [search, setSearch] = useState("");

  const filtered = doctors.filter((d) => {
    const q = search.toLowerCase();
    return (
      d.name.toLowerCase().includes(q) ||
      d.email.toLowerCase().includes(q) ||
      d.specialization.toLowerCase().includes(q)
    );
  });

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Stethoscope className="w-4 h-4 text-primary" />
              Doctor Practice Analytics
            </CardTitle>
            <CardDescription className="text-xs">
              Performance metrics with multi-clinic affiliation fee tracking
            </CardDescription>
          </div>
          <div className="relative w-full md:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-muted-foreground" />
            <Input
              placeholder="Search doctor or specialization..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 pl-8 text-xs"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-muted/50 border-y text-muted-foreground uppercase font-semibold text-[10px] tracking-wider">
              <tr>
                <th className="py-2.5 px-4">Doctor</th>
                <th className="py-2.5 px-3">Specialization</th>
                <th className="py-2.5 px-3">Clinic Affiliations & Fees</th>
                <th className="py-2.5 px-3 text-right">Total Visits</th>
                <th className="py-2.5 px-3 text-right">Completion Rate</th>
                <th className="py-2.5 px-3 text-right">Avg / Active Day</th>
                <th className="py-2.5 px-3 text-right">Gross Collections</th>
                <th className="py-2.5 px-4 text-right">Clinic Earnings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-muted-foreground text-xs">
                    No doctor performance records found.
                  </td>
                </tr>
              ) : (
                filtered.map((d) => (
                  <tr key={d.doctor_id} className="hover:bg-muted/40 transition-colors">
                    <td className="py-2.5 px-4">
                      <div className="font-semibold text-foreground">{d.name}</div>
                      <div className="text-[10px] text-muted-foreground">{d.email}</div>
                    </td>
                    <td className="py-2.5 px-3 text-muted-foreground font-medium">
                      {d.specialization}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {d.affiliations.map((aff) => (
                          <Badge
                            key={aff.clinic_id}
                            variant="secondary"
                            className="text-[10px] py-0 px-1.5 flex items-center gap-1 font-normal bg-slate-100"
                          >
                            <Building2 className="w-2.5 h-2.5 text-muted-foreground" />
                            <span>{aff.clinic_name}:</span>
                            <span className="font-semibold text-foreground">₹{parseFloat(aff.consultation_fee).toFixed(0)}</span>
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-foreground">
                      {d.total_appointments}
                    </td>
                    <td className="py-2.5 px-3 text-right text-muted-foreground">
                      {d.completion_rate.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-right text-muted-foreground">
                      {d.avg_appointments_per_day}
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-blue-600">
                      ₹{parseFloat(d.gross_revenue).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 text-right font-semibold text-purple-600">
                      ₹{parseFloat(d.clinic_share).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
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
