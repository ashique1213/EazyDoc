import React, { useState } from "react";
import {
  Ban,
  Clock,
  IndianRupee,
  Loader2,
  Stethoscope,
  UserX,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useClinicDoctors } from "@/features/doctorClinics";
import { useSchedules } from "../hooks";
import { WeeklyScheduleGrid } from "./WeeklyScheduleGrid";
import { DoctorUnavailabilityModal } from "./DoctorUnavailabilityModal";
import { BlockedSlotsModal } from "./BlockedSlotsModal";

interface ClinicSchedulesSectionProps {
  clinicId: string;
  clinicName: string;
  isClinicApproved: boolean;
  preselectedDoctorClinicId?: string;
}

export const ClinicSchedulesSection: React.FC<ClinicSchedulesSectionProps> = ({
  clinicId,
  clinicName,
  isClinicApproved,
  preselectedDoctorClinicId,
}) => {
  const { data: doctors, isLoading: isDoctorsLoading } = useClinicDoctors(
    clinicId,
    "ACTIVE"
  );

  const [selectedAssocId, setSelectedAssocId] = useState<string | null>(
    preselectedDoctorClinicId || null
  );

  // Fallback to first active doctor once loaded
  const activeDoctors = doctors?.filter((d) => d.status === "ACTIVE") || [];
  const activeAssocId = selectedAssocId || (activeDoctors.length > 0 ? activeDoctors[0].id : null);
  const selectedDoctorAssoc = activeDoctors.find((d) => d.id === activeAssocId);

  const {
    data: schedules,
    isLoading: isSchedulesLoading,
    refetch: refetchSchedules,
  } = useSchedules(activeAssocId ? { doctor_clinic_id: activeAssocId } : undefined);

  // Modals
  const [isLeavesModalOpen, setIsLeavesModalOpen] = useState(false);
  const [isBlockedModalOpen, setIsBlockedModalOpen] = useState(false);

  if (!isClinicApproved) {
    return (
      <Card className="border-amber-500/30 bg-amber-500/10 p-6 text-center space-y-2">
        <Clock className="h-8 w-8 mx-auto text-amber-600" />
        <h3 className="text-base font-bold text-amber-900 dark:text-amber-200">
          Establishment Pending Verification
        </h3>
        <p className="text-xs text-amber-800 dark:text-amber-300 max-w-md mx-auto">
          Doctor working shifts and bookable availability can only be scheduled once this clinic is approved by Super Administration.
        </p>
      </Card>
    );
  }

  if (isDoctorsLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
      </div>
    );
  }

  if (activeDoctors.length === 0) {
    return (
      <Card className="p-8 text-center border-dashed space-y-3">
        <Stethoscope className="h-8 w-8 mx-auto text-muted-foreground stroke-1" />
        <h3 className="text-base font-bold text-foreground">No Active Medical Practitioners</h3>
        <p className="text-xs text-muted-foreground max-w-md mx-auto">
          To configure weekly consultation schedules, you must first invite licensed doctors and wait for them to accept the affiliation.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Doctor Selection Pill Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-muted/20 p-3 rounded-xl border">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-muted-foreground mr-1">Select Doctor:</span>
          {activeDoctors.map((doc) => {
            const isSelected = doc.id === activeAssocId;
            return (
              <Button
                key={doc.id}
                variant={isSelected ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedAssocId(doc.id)}
                className={`text-xs h-8 gap-1.5 transition-all ${
                  isSelected ? "shadow-sm font-semibold" : "text-muted-foreground"
                }`}
              >
                <Stethoscope className="h-3.5 w-3.5" />
                {doc.doctor.full_name}
                <Badge
                  variant={isSelected ? "secondary" : "outline"}
                  className="text-[10px] ml-1 py-0 px-1 font-normal"
                >
                  {doc.doctor.specialization}
                </Badge>
              </Button>
            );
          })}
        </div>

        {selectedDoctorAssoc && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsBlockedModalOpen(true)}
              className="text-xs h-8 gap-1.5"
            >
              <Ban className="h-3.5 w-3.5 text-rose-600" />
              Blocked Slots
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLeavesModalOpen(true)}
              className="text-xs h-8 gap-1.5"
            >
              <UserX className="h-3.5 w-3.5 text-amber-600" />
              Doctor Leaves
            </Button>
          </div>
        )}
      </div>

      {/* Selected Doctor Summary Card */}
      {selectedDoctorAssoc && (
        <div className="flex flex-wrap items-center justify-between gap-3 bg-card p-4 rounded-xl border shadow-xs text-xs">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold">
              {selectedDoctorAssoc.doctor.full_name.substring(0, 2).toUpperCase()}
            </div>
            <div>
              <h4 className="font-bold text-sm text-foreground">
                {selectedDoctorAssoc.doctor.full_name}
              </h4>
              <p className="text-muted-foreground">
                {selectedDoctorAssoc.doctor.specialization} • {selectedDoctorAssoc.doctor.qualifications}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-muted-foreground">
            <div>
              <span className="block text-[10px] uppercase font-semibold text-muted-foreground">
                Slot Duration
              </span>
              <strong className="text-foreground">
                {selectedDoctorAssoc.appointment_duration_minutes} mins
              </strong>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-semibold text-muted-foreground">
                Consultation Fee
              </span>
              <strong className="text-foreground flex items-center">
                <IndianRupee className="h-3 w-3" />
                {selectedDoctorAssoc.consultation_fee}
              </strong>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-semibold text-muted-foreground">
                Reg Number
              </span>
              <strong className="text-foreground">
                {selectedDoctorAssoc.doctor.registration_number}
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Grid */}
      {selectedDoctorAssoc && (
        <>
          {isSchedulesLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <WeeklyScheduleGrid
              schedules={schedules || []}
              doctorClinicId={selectedDoctorAssoc.id}
              doctorName={selectedDoctorAssoc.doctor.full_name}
              clinicName={clinicName}
              onRefresh={() => {
                refetchSchedules();
              }}
              onManageLeaves={() => setIsLeavesModalOpen(true)}
              onManageBlockedSlots={() => setIsBlockedModalOpen(true)}
            />
          )}

          {/* Leaves Modal */}
          <DoctorUnavailabilityModal
            isOpen={isLeavesModalOpen}
            onClose={() => setIsLeavesModalOpen(false)}
            doctorId={selectedDoctorAssoc.doctor.id}
            clinicId={clinicId}
            doctorName={selectedDoctorAssoc.doctor.full_name}
          />

          {/* Blocked Slots Modal */}
          <BlockedSlotsModal
            isOpen={isBlockedModalOpen}
            onClose={() => setIsBlockedModalOpen(false)}
            doctorClinicId={selectedDoctorAssoc.id}
            doctorName={selectedDoctorAssoc.doctor.full_name}
            clinicName={clinicName}
          />
        </>
      )}
    </div>
  );
};
