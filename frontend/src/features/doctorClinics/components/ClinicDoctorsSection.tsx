import React, { useState } from "react";
import {
  Clock,
  IndianRupee,
  Loader2,
  RefreshCw,
  Settings,
  ShieldCheck,
  Stethoscope,
  UserMinus,
  UserPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DoctorClinic, DoctorClinicStatus } from "../types";
import { useClinicDoctors } from "../hooks";
import { DoctorClinicStatusBadge } from "./DoctorClinicStatusBadge";
import { InviteDoctorModal } from "./InviteDoctorModal";
import { ClinicDoctorSettingsModal } from "./ClinicDoctorSettingsModal";
import { RemoveDoctorModal } from "./RemoveDoctorModal";

interface ClinicDoctorsSectionProps {
  clinicId: string;
  isClinicApproved: boolean;
}

export const ClinicDoctorsSection: React.FC<ClinicDoctorsSectionProps> = ({
  clinicId,
  isClinicApproved,
}) => {
  const [statusFilter, setStatusFilter] = useState<DoctorClinicStatus | "ALL">("ALL");
  const { data: doctors, isLoading, isError, refetch } = useClinicDoctors(clinicId, statusFilter);

  // Modals state
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [selectedAssocForSettings, setSelectedAssocForSettings] = useState<DoctorClinic | null>(null);
  const [selectedAssocForRemoval, setSelectedAssocForRemoval] = useState<DoctorClinic | null>(null);

  const activeCount = doctors?.filter((d) => d.status === "ACTIVE").length || 0;
  const pendingCount = doctors?.filter((d) => d.status === "INVITED").length || 0;

  return (
    <div className="space-y-6">
      {/* Top Banner / Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
            <Stethoscope className="h-5 w-5 text-primary" />
            Clinic Medical Practitioners
          </h3>
          <p className="text-xs text-muted-foreground">
            Manage doctor affiliations, independent consultation fees, and appointment durations for this establishment.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            onClick={() => setIsInviteOpen(true)}
            disabled={!isClinicApproved}
            className="text-xs gap-1.5 shadow-sm h-9"
          >
            <UserPlus className="h-3.5 w-3.5" />
            Invite Doctor
          </Button>
        </div>
      </div>

      {!isClinicApproved && (
        <Card className="border-amber-500/30 bg-amber-500/10 p-4">
          <p className="text-xs text-amber-800 dark:text-amber-300">
            <strong>Establishment Notice:</strong> Doctor affiliations can only be initiated once this clinic is approved by Super Administration.
          </p>
        </Card>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
        <div className="flex items-center gap-1.5">
          {(
            [
              { label: "All Affiliations", value: "ALL" },
              { label: "Active Doctors", value: "ACTIVE" },
              { label: "Pending Invitations", value: "INVITED" },
              { label: "Removed / Past", value: "REMOVED" },
            ] as const
          ).map((tab) => (
            <Button
              key={tab.value}
              variant={statusFilter === tab.value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setStatusFilter(tab.value)}
              className="text-xs h-7 px-2.5 font-medium"
            >
              {tab.label}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>Active: <strong className="text-foreground">{activeCount}</strong></span>
          <span>Pending: <strong className="text-foreground">{pendingCount}</strong></span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            title="Refresh list"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-primary" />
        </div>
      ) : isError ? (
        <Card className="p-8 text-center border-dashed">
          <p className="text-xs text-destructive">Failed to load affiliated doctors.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-3 text-xs">
            Retry
          </Button>
        </Card>
      ) : !doctors || doctors.length === 0 ? (
        <Card className="p-8 text-center border-dashed bg-muted/20">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary mb-3">
            <Stethoscope className="h-5 w-5" />
          </div>
          <h4 className="text-sm font-semibold text-foreground">No Doctor Affiliations Found</h4>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
            {statusFilter === "ALL"
              ? "You haven't invited any practitioners to this clinic yet. Click 'Invite Doctor' to begin building your clinic's team."
              : `No doctors found matching the status filter "${statusFilter}".`}
          </p>
          {isClinicApproved && (
            <Button
              size="sm"
              onClick={() => setIsInviteOpen(true)}
              className="mt-4 text-xs gap-1.5"
            >
              <UserPlus className="h-3.5 w-3.5" />
              Invite Doctor
            </Button>
          )}
        </Card>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40 text-[11px]">
                <TableHead className="font-semibold">Practitioner</TableHead>
                <TableHead className="font-semibold">Medical Registration</TableHead>
                <TableHead className="font-semibold">Consultation Fee</TableHead>
                <TableHead className="font-semibold">Slot Duration</TableHead>
                <TableHead className="font-semibold">Status</TableHead>
                <TableHead className="text-right font-semibold">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {doctors.map((assoc) => (
                <TableRow key={assoc.id} className="text-xs hover:bg-muted/30 transition-colors">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary font-bold text-xs">
                        {assoc.doctor.full_name
                          .split(" ")
                          .map((n) => n[0])
                          .join("")
                          .substring(0, 2)
                          .toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          {assoc.doctor.full_name}
                          {assoc.doctor.is_verified && (
                            <span title="Verified Medical License">
                              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-primary font-medium">
                          {assoc.doctor.specialization}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {assoc.doctor.qualifications} • {assoc.doctor.years_of_experience} yrs exp
                        </div>
                      </div>
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-mono text-[11px] font-medium text-foreground">
                      {assoc.doctor.registration_number}
                    </div>
                    <div className="text-[11px] text-muted-foreground truncate max-w-[180px]">
                      {assoc.doctor.registration_council}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-semibold text-foreground flex items-center gap-0.5">
                      <IndianRupee className="h-3 w-3" />
                      {parseFloat(assoc.consultation_fee).toFixed(2)}
                    </div>
                    {parseFloat(assoc.follow_up_fee) > 0 && (
                      <div className="text-[11px] text-muted-foreground flex items-center gap-0.5">
                        Follow-up: ₹{parseFloat(assoc.follow_up_fee).toFixed(2)}
                      </div>
                    )}
                  </TableCell>

                  <TableCell>
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="h-3 w-3 text-primary" />
                      <span>{assoc.appointment_duration_minutes} mins</span>
                    </div>
                  </TableCell>

                  <TableCell>
                    <DoctorClinicStatusBadge status={assoc.status} />
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {assoc.status === "ACTIVE" && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedAssocForSettings(assoc)}
                            className="h-7 text-xs px-2 gap-1 text-muted-foreground hover:text-foreground"
                            title="Edit consultation fee and appointment slot duration"
                          >
                            <Settings className="h-3 w-3" />
                            Terms
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedAssocForRemoval(assoc)}
                            className="h-7 text-xs px-2 text-destructive hover:bg-destructive/10"
                            title="Remove doctor from clinic"
                          >
                            <UserMinus className="h-3 w-3" />
                          </Button>
                        </>
                      )}

                      {assoc.status === "INVITED" && (
                        <span className="text-[11px] text-muted-foreground italic">
                          Awaiting doctor response
                        </span>
                      )}

                      {(assoc.status === "REJECTED" || assoc.status === "REMOVED") && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setIsInviteOpen(true)}
                          className="h-7 text-xs px-2 gap-1"
                        >
                          <RefreshCw className="h-3 w-3" />
                          Re-invite
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Modals */}
      <InviteDoctorModal
        clinicId={clinicId}
        isOpen={isInviteOpen}
        onClose={() => setIsInviteOpen(false)}
        onSuccess={() => refetch()}
      />

      <ClinicDoctorSettingsModal
        clinicId={clinicId}
        association={selectedAssocForSettings}
        isOpen={Boolean(selectedAssocForSettings)}
        onClose={() => setSelectedAssocForSettings(null)}
        onSuccess={() => refetch()}
      />

      <RemoveDoctorModal
        clinicId={clinicId}
        association={selectedAssocForRemoval}
        isOpen={Boolean(selectedAssocForRemoval)}
        onClose={() => setSelectedAssocForRemoval(null)}
        onSuccess={() => refetch()}
      />
    </div>
  );
};
