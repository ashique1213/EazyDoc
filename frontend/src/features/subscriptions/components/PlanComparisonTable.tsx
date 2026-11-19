import { Check, X } from "lucide-react";
import type { SubscriptionPlan } from "../types";

interface PlanComparisonTableProps {
  plans: SubscriptionPlan[];
}

export function PlanComparisonTable({ plans }: PlanComparisonTableProps) {
  // Sort plans Free -> Starter -> Professional -> Enterprise
  const sortedPlans = [...plans].sort((a, b) => Number(a.price) - Number(b.price));

  const features = [
    {
      category: "Resource Quotas",
      items: [
        { name: "Doctor Affiliations", key: "doctors", render: (p: SubscriptionPlan) => p.max_doctors ?? "Unlimited" },
        { name: "Staff Account Seats", key: "staff", render: (p: SubscriptionPlan) => p.max_staff ?? "Unlimited" },
        { name: "Monthly Bookings", key: "appts", render: (p: SubscriptionPlan) => p.max_appointments_per_month ?? "Unlimited" },
      ],
    },
    {
      category: "Analytics & Reporting",
      items: [
        {
          name: "Clinic Dashboard",
          key: "basic_dash",
          render: () => <Check className="w-4 h-4 text-emerald-600 mx-auto" />,
        },
        {
          name: "Advanced Financial Analytics",
          key: "adv_analytics",
          render: (p: SubscriptionPlan) =>
            p.feature_flags?.advanced_analytics ? (
              <Check className="w-4 h-4 text-emerald-600 mx-auto" />
            ) : (
              <X className="w-4 h-4 text-muted-foreground/40 mx-auto" />
            ),
        },
        {
          name: "CSV Data Exports",
          key: "csv_export",
          render: (p: SubscriptionPlan) =>
            p.feature_flags?.export_reports ? (
              <Check className="w-4 h-4 text-emerald-600 mx-auto" />
            ) : (
              <X className="w-4 h-4 text-muted-foreground/40 mx-auto" />
            ),
        },
        {
          name: "Official PDF Reports",
          key: "pdf_export",
          render: (p: SubscriptionPlan) =>
            p.feature_flags?.export_pdf ? (
              <Check className="w-4 h-4 text-emerald-600 mx-auto" />
            ) : (
              <X className="w-4 h-4 text-muted-foreground/40 mx-auto" />
            ),
        },
      ],
    },
    {
      category: "Support & SLA",
      items: [
        {
          name: "Priority Support SLA",
          key: "support",
          render: (p: SubscriptionPlan) =>
            p.tier === "ENTERPRISE" ? (
              "Dedicated Manager"
            ) : p.tier === "PROFESSIONAL" ? (
              "4-Hour Response"
            ) : p.tier === "STARTER" ? (
              "24-Hour Email"
            ) : (
              "Community"
            ),
        },
      ],
    },
  ];

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="py-4 px-6 font-semibold text-foreground w-1/3">Feature Comparison</th>
              {sortedPlans.map((plan) => (
                <th key={plan.id} className="py-4 px-4 text-center font-bold text-foreground">
                  <div>{plan.name}</div>
                  <div className="text-xs font-normal text-muted-foreground mt-0.5">
                    {Number(plan.price) === 0 ? "Free" : `₹${Number(plan.price).toLocaleString("en-IN")}`}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {features.map((cat, catIdx) => (
              <React.Fragment key={catIdx}>
                <tr className="bg-muted/30 border-b">
                  <td colSpan={sortedPlans.length + 1} className="py-2.5 px-6 font-bold text-xs uppercase tracking-wider text-muted-foreground">
                    {cat.category}
                  </td>
                </tr>
                {cat.items.map((item, itemIdx) => (
                  <tr key={itemIdx} className="border-b hover:bg-muted/10 transition-colors">
                    <td className="py-3 px-6 text-foreground font-medium">{item.name}</td>
                    {sortedPlans.map((plan) => (
                      <td key={plan.id} className="py-3 px-4 text-center text-muted-foreground font-medium">
                        {item.render(plan)}
                      </td>
                    ))}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import React from "react";
