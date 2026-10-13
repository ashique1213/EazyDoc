import React, { useState } from "react";
import {
  Clock,
  Eye,
  Plus,
  UserX,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  WEEKDAY_LABELS,
  type DoctorSchedule,
  type WeekdayNumber,
} from "../types";
import { useDeactivateSchedule } from "../hooks";
import { ScheduleModal } from "./ScheduleModal";
import { AvailabilityPreviewModal } from "./AvailabilityPreviewModal";

interface WeeklyScheduleGridProps {
  schedules: DoctorSchedule[];
  doctorClinicId: string;
  doctorName?: string;
  clinicName?: string;
  isReadOnly?: boolean;
  onRefresh?: () => void;
  onManageLeaves?: () => void;
  onManageBlockedSlots?: () => void;
}

export const WeeklyScheduleGrid: React.FC<WeeklyScheduleGridProps> = ({
  schedules,
  doctorClinicId,
  doctorName,
  clinicName,
  isReadOnly = false,
  onRefresh,
  onManageLeaves,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [scheduleToEdit, setScheduleToEdit] = useState<DoctorSchedule | null>(null);
  const [selectedDayForAdd, setSelectedDayForAdd] = useState<WeekdayNumber>(0);
  const [isAvailabilityPreviewOpen, setIsAvailabilityPreviewOpen] = useState(false);

  const deactivateMutation = useDeactivateSchedule();

  const handleOpenAdd = (day: WeekdayNumber) => {
    setScheduleToEdit(null);
    setSelectedDayForAdd(day);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (sched: DoctorSchedule) => {
    setScheduleToEdit(sched);
    setSelectedDayForAdd(sched.day_of_week);
    setIsModalOpen(true);
  };

  const handleDeactivate = async (sched: DoctorSchedule) => {
    if (confirm(`Are you sure you want to deactivate shift ${sched.start_time.substring(0, 5)} - ${sched.end_time.substring(0, 5)} on ${WEEKDAY_LABELS[sched.day_of_week]}?`)) {
      await deactivateMutation.mutateAsync(sched.id);
      onRefresh?.();
    }
  };

  // Group schedules by day of week (0 to 6)
  const days: WeekdayNumber[] = [0, 1, 2, 3, 4, 5, 6];
  const shiftsByDay = days.reduce((acc, day) => {
    acc[day] = schedules.filter((s) => s.day_of_week === day && s.is_active);
    return acc;
  }, {} as Record<WeekdayNumber, DoctorSchedule[]>);

  const totalActiveShifts = schedules.filter((s) => s.is_active).length;

  return (
    <div className="space-y-6">
      {/* Action Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-card p-4 rounded-xl border shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-foreground flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              Weekly Consultation Shifts
            </h3>
            <Badge variant="secondary" className="text-xs">
              {totalActiveShifts} Active Shifts
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Configure independent working hours, split shifts, and travel buffers for this clinic association.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAvailabilityPreviewOpen(true)}
            className="text-xs h-8 gap-1.5"
          >
            <Eye className="h-3.5 w-3.5 text-primary" />
            Inspect Bookable Slots
          </Button>

          {onManageLeaves && (
            <Button
              variant="outline"
              size="sm"
              onClick={onManageLeaves}
              className="text-xs h-8 gap-1.5"
            >
              <UserX className="h-3.5 w-3.5 text-amber-600" />
              Doctor Leaves
            </Button>
          )}

          {!isReadOnly && (
            <Button
              size="sm"
              onClick={() => handleOpenAdd(0)}
              className="text-xs h-8 gap-1.5 shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Shift
            </Button>
          )}
        </div>
      </div>

      {/* 7-Day Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-3.5">
        {days.map((day) => {
          const dayShifts = shiftsByDay[day];
          const hasShifts = dayShifts.length > 0;

          return (
            <Card
              key={day}
              className={`flex flex-col h-full transition-all border ${
                hasShifts
                  ? "bg-card border-border shadow-xs"
                  : "bg-muted/15 border-dashed border-border/70"
              }`}
            >
              {/* Day Header */}
              <div className="p-3 border-b flex items-center justify-between bg-muted/20 rounded-t-xl">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    {WEEKDAY_LABELS[day]}
                  </h4>
                  <span className="text-[10px] text-muted-foreground">
                    {dayShifts.length === 1
                      ? "1 Shift"
                      : `${dayShifts.length} Shifts`}
                  </span>
                </div>

                {!isReadOnly && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 rounded-full hover:bg-primary hover:text-primary-foreground"
                    onClick={() => handleOpenAdd(day)}
                    title={`Add shift on ${WEEKDAY_LABELS[day]}`}
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>

              {/* Shifts List for Day */}
              <CardContent className="p-2.5 flex-1 flex flex-col justify-between space-y-2">
                {hasShifts ? (
                  <div className="space-y-2">
                    {dayShifts.map((shift) => {
                      const startTimeDisplay = shift.start_time.substring(0, 5);
                      const endTimeDisplay = shift.end_time.substring(0, 5);

                      return (
                        <div
                          key={shift.id}
                          className="group relative rounded-lg border bg-background/80 p-2.5 transition-all hover:border-primary/50 hover:shadow-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-foreground flex items-center gap-1">
                              <Clock className="h-3 w-3 text-primary" />
                              {startTimeDisplay} – {endTimeDisplay}
                            </span>

                            {!isReadOnly && (
                              <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100">
                                <button
                                  onClick={() => handleOpenEdit(shift)}
                                  className="text-[10px] text-muted-foreground hover:text-foreground font-medium p-0.5"
                                  title="Edit Shift"
                                >
                                  Edit
                                </button>
                                <span className="text-muted-foreground text-[10px]">•</span>
                                <button
                                  onClick={() => handleDeactivate(shift)}
                                  className="text-[10px] text-destructive hover:underline p-0.5"
                                  title="Deactivate Shift"
                                >
                                  Delete
                                </button>
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-1 flex-wrap text-[10px]">
                            <Badge variant="outline" className="text-[10px] py-0 px-1.5 h-4.5 bg-muted/40">
                              {shift.slot_duration_minutes || shift.effective_slot_duration}m slots
                            </Badge>

                            {shift.buffer_minutes > 0 && (
                              <Badge
                                variant="outline"
                                className="text-[10px] py-0 px-1.5 h-4.5 border-amber-500/40 text-amber-700 dark:text-amber-300"
                              >
                                +{shift.buffer_minutes}m buffer
                              </Badge>
                            )}

                            {shift.clinic_name && shift.clinic_name !== clinicName && (
                              <Badge variant="secondary" className="text-[10px] py-0 px-1.5 h-4.5">
                                {shift.clinic_name}
                              </Badge>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-6 text-center text-muted-foreground/60 space-y-1">
                    <Clock className="h-5 w-5 stroke-1" />
                    <p className="text-[11px]">No shifts</p>
                  </div>
                )}

                {!isReadOnly && !hasShifts && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full text-[11px] h-7 text-muted-foreground hover:text-primary border border-dashed border-border/80"
                    onClick={() => handleOpenAdd(day)}
                  >
                    + Add Shift
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Add / Edit Schedule Modal */}
      <ScheduleModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        doctorClinicId={doctorClinicId}
        doctorName={doctorName}
        clinicName={clinicName}
        scheduleToEdit={scheduleToEdit}
        defaultDay={selectedDayForAdd}
        onSuccess={() => {
          onRefresh?.();
        }}
      />

      {/* Available Slots Inspector */}
      <AvailabilityPreviewModal
        isOpen={isAvailabilityPreviewOpen}
        onClose={() => setIsAvailabilityPreviewOpen(false)}
        doctorClinicId={doctorClinicId}
        doctorName={doctorName}
        clinicName={clinicName}
      />
    </div>
  );
};
