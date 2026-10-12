import React from "react";
import { CheckCircle2, Clock, XCircle, UserMinus, AlertOctagon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { DoctorClinicStatus } from "../types";

interface DoctorClinicStatusBadgeProps {
  status: DoctorClinicStatus;
  className?: string;
}

export const DoctorClinicStatusBadge: React.FC<DoctorClinicStatusBadgeProps> = ({
  status,
  className = "",
}) => {
  switch (status) {
    case "ACTIVE":
      return (
        <Badge
          className={`bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 font-medium ${className}`}
        >
          <CheckCircle2 className="mr-1 h-3 w-3" />
          Active Member
        </Badge>
      );
    case "INVITED":
      return (
        <Badge
          className={`bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/20 font-medium ${className}`}
        >
          <Clock className="mr-1 h-3 w-3" />
          Invitation Pending
        </Badge>
      );
    case "REJECTED":
      return (
        <Badge
          variant="destructive"
          className={`bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/20 font-medium ${className}`}
        >
          <XCircle className="mr-1 h-3 w-3" />
          Declined
        </Badge>
      );
    case "REMOVED":
      return (
        <Badge
          variant="secondary"
          className={`bg-slate-500/15 text-slate-700 dark:text-slate-400 border-slate-500/20 font-medium ${className}`}
        >
          <UserMinus className="mr-1 h-3 w-3" />
          Association Ended
        </Badge>
      );
    case "SUSPENDED":
      return (
        <Badge
          variant="destructive"
          className={`bg-amber-600/15 text-amber-700 dark:text-amber-400 border-amber-600/20 font-medium ${className}`}
        >
          <AlertOctagon className="mr-1 h-3 w-3" />
          Suspended
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
};
