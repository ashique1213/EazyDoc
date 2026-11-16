import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Building2, Search, ArrowUpDown } from "lucide-react";
import type { ClinicPerformanceItem } from "../types";

interface ClinicComparisonTableProps {
  clinics: ClinicPerformanceItem[];
}

export const ClinicComparisonTable: React.FC<ClinicComparisonTableProps> = ({ clinics }) => {
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<keyof ClinicPerformanceItem>("gross_volume");
  const [sortAsc, setSortAsc] = useState(false);

  const filtered = clinics.filter((c) => {
    const q = search.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.city.toLowerCase().includes(q) ||
      c.state.toLowerCase().includes(q)
    );
  });

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];

    if (sortField === "gross_volume" || sortField === "platform_commission" || sortField === "clinic_share") {
      const numA = parseFloat((aVal as string) || "0");
      const numB = parseFloat((bVal as string) || "0");
      return sortAsc ? numA - numB : numB - numA;
    }
    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortAsc ? aVal - bVal : bVal - aVal;
    }
    const strA = String(aVal ?? "");
    const strB = String(bVal ?? "");
    return sortAsc ? strA.localeCompare(strB) : strB.localeCompare(strA);
  });

  const toggleSort = (field: keyof ClinicPerformanceItem) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Building2 className="w-4 h-4 text-primary" />
              Clinic Performance Comparison
            </CardTitle>
            <CardDescription className="text-xs">
              Benchmark volume, completion rate, and earnings across registered clinics
            </CardDescription>
          </div>
          <div className="relative w-full md:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-muted-foreground" />
            <Input
              placeholder="Search clinic or city..."
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
                <th className="py-2.5 px-4 cursor-pointer" onClick={() => toggleSort("name")}>
                  <div className="flex items-center gap-1">
                    Clinic Name <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3">Location</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right cursor-pointer" onClick={() => toggleSort("total_doctors")}>
                  <div className="flex items-center justify-end gap-1">
                    Doctors <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3 text-right cursor-pointer" onClick={() => toggleSort("total_appointments")}>
                  <div className="flex items-center justify-end gap-1">
                    Bookings <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3 text-right cursor-pointer" onClick={() => toggleSort("completion_rate")}>
                  <div className="flex items-center justify-end gap-1">
                    Completion <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3 text-right cursor-pointer" onClick={() => toggleSort("gross_volume")}>
                  <div className="flex items-center justify-end gap-1">
                    Gross Collections <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3 text-right cursor-pointer" onClick={() => toggleSort("platform_commission")}>
                  <div className="flex items-center justify-end gap-1">
                    Platform Commission <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-4 text-right cursor-pointer" onClick={() => toggleSort("clinic_share")}>
                  <div className="flex items-center justify-end gap-1">
                    Clinic Net Share <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sorted.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-6 text-center text-muted-foreground text-xs">
                    No clinics found matching criteria.
                  </td>
                </tr>
              ) : (
                sorted.map((c) => (
                  <tr key={c.clinic_id} className="hover:bg-muted/40 transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-foreground">
                      {c.name}
                      {c.commission_rate_override && (
                        <span className="ml-1.5 text-[10px] text-amber-600 font-normal">
                          ({c.commission_rate_override}% override)
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-muted-foreground">
                      {c.city ? `${c.city}, ${c.state}` : "—"}
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={c.status === "APPROVED" ? "outline" : "secondary"}
                        className={`text-[10px] py-0 px-1.5 ${
                          c.status === "APPROVED" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : ""
                        }`}
                      >
                        {c.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-right text-muted-foreground">
                      {c.active_doctors} / {c.total_doctors}
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-foreground">
                      {c.total_appointments}
                    </td>
                    <td className="py-2.5 px-3 text-right text-muted-foreground">
                      {c.completion_rate.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-blue-600">
                      ₹{parseFloat(c.gross_volume).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-emerald-600">
                      ₹{parseFloat(c.platform_commission).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 text-right font-semibold text-purple-600">
                      ₹{parseFloat(c.clinic_share).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
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
