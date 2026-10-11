import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  Clock,
  Eye,
  FileText,
  Loader2,
  Search,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Doctor, DoctorVerificationStatus } from "../types";
import { useAdminDoctors } from "../hooks";
import { AdminDoctorActionDialog, type AdminActionType } from "./AdminDoctorActionDialog";

export const AdminDoctorTable: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  // Action dialog state
  const [activeDoctor, setActiveDoctor] = useState<Doctor | null>(null);
  const [actionType, setActionType] = useState<AdminActionType>(null);
  const [isDialogOpen, setIsDialogOpen] = useState<boolean>(false);

  const { data, isLoading, isError, refetch } = useAdminDoctors({
    status: statusFilter,
    search: debouncedSearch,
    page,
  });

  const doctors = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.ceil(totalCount / 15) || 1;

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(1);
    // Debounce
    const timer = setTimeout(() => {
      setDebouncedSearch(e.target.value);
    }, 400);
    return () => clearTimeout(timer);
  };

  const openAction = (doctor: Doctor, action: AdminActionType) => {
    setActiveDoctor(doctor);
    setActionType(action);
    setIsDialogOpen(true);
  };

  const getStatusBadge = (status: DoctorVerificationStatus) => {
    switch (status) {
      case "VERIFIED":
        return (
          <Badge className="bg-emerald-600/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 text-[11px]">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Verified
          </Badge>
        );
      case "PENDING":
        return (
          <Badge className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20 text-[11px]">
            <Clock className="mr-1 h-3 w-3" />
            Pending Review
          </Badge>
        );
      case "REJECTED":
        return (
          <Badge variant="destructive" className="bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20 text-[11px]">
            <XCircle className="mr-1 h-3 w-3" />
            Rejected
          </Badge>
        );
      case "SUSPENDED":
        return (
          <Badge variant="destructive" className="bg-red-600/10 text-red-700 dark:text-red-400 border-red-600/20 text-[11px]">
            <ShieldAlert className="mr-1 h-3 w-3" />
            Suspended
          </Badge>
        );
      case "DRAFT":
      default:
        return (
          <Badge variant="secondary" className="bg-slate-500/10 text-slate-700 dark:text-slate-400 border-slate-500/20 text-[11px]">
            <FileText className="mr-1 h-3 w-3" />
            Draft
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters and search bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, council, reg #..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="pl-9 text-xs"
          />
        </div>

        {/* Status Filter Buttons */}
        <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
          {["ALL", "PENDING", "VERIFIED", "REJECTED", "SUSPENDED"].map((st) => (
            <Button
              key={st}
              variant={statusFilter === st ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className="text-xs h-8 capitalize"
            >
              {st.toLowerCase()}
            </Button>
          ))}
        </div>
      </div>

      {/* Main Table */}
      <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center p-12 text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Loading doctor profiles...
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-sm text-destructive">
            Failed to load doctor profiles. Please refresh or try again later.
          </div>
        ) : doctors.length === 0 ? (
          <div className="p-12 text-center text-sm text-muted-foreground">
            No doctor profiles found matching the criteria.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead className="text-xs font-semibold">Doctor Name & User</TableHead>
                <TableHead className="text-xs font-semibold">Registration Number</TableHead>
                <TableHead className="text-xs font-semibold">Medical Council</TableHead>
                <TableHead className="text-xs font-semibold">Specialization</TableHead>
                <TableHead className="text-xs font-semibold">Status</TableHead>
                <TableHead className="text-xs font-semibold">Submission Date</TableHead>
                <TableHead className="text-xs font-semibold text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {doctors.map((doctor: Doctor) => (
                <TableRow key={doctor.id} className="hover:bg-muted/20">
                  <TableCell>
                    <div>
                      <p className="font-semibold text-xs text-foreground">{doctor.full_name}</p>
                      <p className="text-[11px] text-muted-foreground">{doctor.user?.email}</p>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{doctor.registration_number}</TableCell>
                  <TableCell className="text-xs">{doctor.registration_council}</TableCell>
                  <TableCell className="text-xs">
                    <Badge variant="outline" className="text-[10px] py-0">
                      {doctor.specialization}
                    </Badge>
                  </TableCell>
                  <TableCell>{getStatusBadge(doctor.verification_status)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {doctor.submitted_at
                      ? new Date(doctor.submitted_at).toLocaleDateString()
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link to={`/admin/doctors/${doctor.id}`}>
                        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1">
                          <Eye className="h-3.5 w-3.5" />
                          Review
                        </Button>
                      </Link>

                      {doctor.verification_status === "PENDING" && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                            onClick={() => openAction(doctor, "VERIFY")}
                          >
                            Verify
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                            onClick={() => openAction(doctor, "REJECT")}
                          >
                            Reject
                          </Button>
                        </>
                      )}

                      {doctor.verification_status === "VERIFIED" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30"
                          onClick={() => openAction(doctor, "SUSPEND")}
                        >
                          Suspend
                        </Button>
                      )}

                      {doctor.verification_status === "SUSPENDED" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950/30"
                          onClick={() => openAction(doctor, "REACTIVATE")}
                        >
                          Reactivate
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t p-3 text-xs text-muted-foreground">
            <span>
              Showing page {page} of {totalPages} ({totalCount} total doctors)
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-7 px-2 text-xs"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="h-7 px-2 text-xs"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Action Dialog */}
      <AdminDoctorActionDialog
        doctor={activeDoctor}
        actionType={actionType}
        isOpen={isDialogOpen}
        onClose={() => {
          setIsDialogOpen(false);
          setActiveDoctor(null);
          setActionType(null);
        }}
        onSuccess={() => refetch()}
      />
    </div>
  );
};
