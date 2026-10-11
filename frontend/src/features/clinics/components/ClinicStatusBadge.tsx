import { Badge } from "@/components/ui/badge";
import type { ClinicStatus } from "../types";
import { CheckCircle2, Clock, XCircle, AlertOctagon, FileEdit } from "lucide-react";

interface ClinicStatusBadgeProps {
  status: ClinicStatus;
  className?: string;
}

export function ClinicStatusBadge({ status, className }: ClinicStatusBadgeProps) {
  switch (status) {
    case "APPROVED":
      return (
        <Badge
          variant="outline"
          className={`bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800 gap-1.5 py-0.5 px-2.5 font-medium ${className || ""}`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          Approved & Active
        </Badge>
      );
    case "PENDING":
      return (
        <Badge
          variant="outline"
          className={`bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800 gap-1.5 py-0.5 px-2.5 font-medium ${className || ""}`}
        >
          <Clock className="h-3.5 w-3.5" />
          Pending Review
        </Badge>
      );
    case "REJECTED":
      return (
        <Badge
          variant="outline"
          className={`bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800 gap-1.5 py-0.5 px-2.5 font-medium ${className || ""}`}
        >
          <XCircle className="h-3.5 w-3.5" />
          Rejected
        </Badge>
      );
    case "SUSPENDED":
      return (
        <Badge
          variant="outline"
          className={`bg-orange-50 text-orange-700 border-orange-300 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800 gap-1.5 py-0.5 px-2.5 font-medium ${className || ""}`}
        >
          <AlertOctagon className="h-3.5 w-3.5" />
          Suspended
        </Badge>
      );
    case "DRAFT":
    default:
      return (
        <Badge
          variant="outline"
          className={`bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 gap-1.5 py-0.5 px-2.5 font-medium ${className || ""}`}
        >
          <FileEdit className="h-3.5 w-3.5" />
          Draft
        </Badge>
      );
  }
}
