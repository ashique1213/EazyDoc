import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  Calendar,
  Clock,
  Eye,
  Loader2,
  Plus,
  Trash2,
  UserX,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useDoctorMe } from "@/features/doctors";
import { useDoctorClinics } from "@/features/doctorClinics";
import {
  useDoctorMasterSchedule,
  useDoctorUnavailabilities,
  useDeleteUnavailability,
} from "@/features/schedules";
import { DoctorUnavailabilityModal } from "@/features/schedules/components/DoctorUnavailabilityModal";
import { AvailabilityPreviewModal } from "@/features/schedules/components/AvailabilityPreviewModal";

export const DoctorSchedulesPage: React.FC = () => {
  const { data: doctor, isLoading: isDoctorLoading } = useDoctorMe();
  const { data: associations } = useDoctorClinics();
  const {
    data: masterSchedule,
    isLoading: isScheduleLoading,
  } = useDoctorMasterSchedule();
  const {
    data: leaves,
    refetch: refetchLeaves,
  } = useDoctorUnavailabilities();

  const deleteLeaveMutation = useDeleteUnavailability();

  const [activeTab, setActiveTab] = useState<"calendar" | "leaves">("calendar");
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [previewDoctorClinicId, setPreviewDoctorClinicId] = useState<string | null>(null);

  const activeClinics = associations?.filter((a) => a.status === "ACTIVE") || [];

  const handleDeleteLeave = async (id: string) => {
    if (confirm("Are you sure you want to cancel this leave period?")) {
      await deleteLeaveMutation.mutateAsync(id);
      refetchLeaves();
    }
  };

  if (isDoctorLoading || isScheduleLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!doctor || doctor.verification_status !== "VERIFIED") {
    return (
      <div className="max-w-2xl mx-auto space-y-4 pt-6">
        <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          <AlertTitle className="text-sm font-semibold">Doctor Profile Verification Required</AlertTitle>
          <AlertDescription className="text-xs mt-1">
            Schedules and availability management are accessible strictly once your medical registration number is verified by Super Administration.
          </AlertDescription>
        </Alert>
        <Link to="/doctor">
          <Button variant="outline" size="sm" className="gap-1.5 text-xs">
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Link to="/doctor">
              <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground">
                <ArrowLeft className="h-4 w-4 mr-1" /> Practice Suite
              </Button>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight">Unified Multi-Clinic Schedule & Availability</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Centralized master schedule across all your affiliated clinics with travel buffer awareness and leave controls.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setIsLeaveModalOpen(true)}
            className="text-xs gap-1.5 h-9 shadow-sm"
          >
            <UserX className="h-3.5 w-3.5 text-amber-300" />
            Record Leave / Time-Off
          </Button>
        </div>
      </div>

      {/* Metric Cards Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="p-4 bg-card border shadow-xs flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground block font-medium">Affiliated Clinics</span>
            <span className="text-lg font-bold text-foreground">{activeClinics.length} Clinics</span>
          </div>
        </Card>

        <Card className="p-4 bg-card border shadow-xs flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground block font-medium">Weekly Active Shifts</span>
            <span className="text-lg font-bold text-foreground">
              {masterSchedule?.total_active_shifts || 0} Shifts
            </span>
          </div>
        </Card>

        <Card className="p-4 bg-card border shadow-xs flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600">
            <UserX className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground block font-medium">Scheduled Leaves</span>
            <span className="text-lg font-bold text-foreground">
              {leaves?.length || 0} Periods
            </span>
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-1 border-b pb-1">
        <Button
          variant={activeTab === "calendar" ? "secondary" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("calendar")}
          className="text-xs gap-1.5 h-8 font-semibold"
        >
          <Calendar className="h-3.5 w-3.5" />
          Multi-Clinic Master Calendar
        </Button>
        <Button
          variant={activeTab === "leaves" ? "secondary" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("leaves")}
          className="text-xs gap-1.5 h-8 font-semibold"
        >
          <UserX className="h-3.5 w-3.5" />
          My Leaves & Time-Off ({leaves?.length || 0})
        </Button>
      </div>

      {/* Tab 1: Unified Calendar */}
      {activeTab === "calendar" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-3">
            {masterSchedule?.weekly_schedule.map((dayGroup) => {
              const shifts = dayGroup.shifts;
              const hasShifts = shifts.length > 0;

              return (
                <Card
                  key={dayGroup.day_of_week}
                  className={`flex flex-col h-full border ${
                    hasShifts ? "bg-card border-border shadow-xs" : "bg-muted/15 border-dashed border-border/70"
                  }`}
                >
                  <div className="p-3 border-b bg-muted/20 rounded-t-xl flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                        {dayGroup.day_name}
                      </h4>
                      <span className="text-[10px] text-muted-foreground">
                        {shifts.length === 1 ? "1 Shift" : `${shifts.length} Shifts`}
                      </span>
                    </div>
                  </div>

                  <CardContent className="p-2.5 flex-1 flex flex-col justify-between space-y-2">
                    {hasShifts ? (
                      <div className="space-y-2">
                        {shifts.map((shift) => (
                          <div
                            key={shift.id}
                            className="rounded-lg border bg-background/90 p-2.5 transition-all hover:border-primary/50 shadow-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-foreground flex items-center gap-1">
                                <Clock className="h-3 w-3 text-primary" />
                                {shift.start_time.substring(0, 5)} – {shift.end_time.substring(0, 5)}
                              </span>
                            </div>

                            <div className="flex items-center gap-1 flex-wrap">
                              <Badge variant="secondary" className="text-[10px] py-0 px-1.5 h-4.5 font-semibold">
                                <Building2 className="h-2.5 w-2.5 mr-1" />
                                {shift.clinic_name}
                              </Badge>
                              <Badge variant="outline" className="text-[10px] py-0 px-1.5 h-4.5 bg-muted/30">
                                {shift.effective_slot_duration}m slots
                              </Badge>
                              {shift.buffer_minutes > 0 && (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] py-0 px-1.5 h-4.5 border-amber-500/40 text-amber-700 dark:text-amber-300"
                                >
                                  +{shift.buffer_minutes}m buffer
                                </Badge>
                              )}
                            </div>

                            <button
                              onClick={() => setPreviewDoctorClinicId(shift.doctor_clinic)}
                              className="text-[10px] text-primary hover:underline flex items-center gap-1 pt-0.5"
                            >
                              <Eye className="h-2.5 w-2.5" />
                              Inspect Day Slots
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground/60 space-y-1">
                        <Clock className="h-5 w-5 stroke-1" />
                        <p className="text-[11px]">Free Day</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Leaves Management */}
      {activeTab === "leaves" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-card p-4 rounded-xl border">
            <div>
              <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                <UserX className="h-4 w-4 text-amber-600" />
                Active Leaves & Scheduled Absence
              </h3>
              <p className="text-xs text-muted-foreground">
                Slots during approved leaves are automatically made unavailable to prevent patient bookings across all clinics.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => setIsLeaveModalOpen(true)}
              className="text-xs gap-1.5 h-8"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Leave Period
            </Button>
          </div>

          {leaves && leaves.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {leaves.map((l) => {
                const sDate = new Date(l.start_datetime).toLocaleDateString();
                const sTime = new Date(l.start_datetime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                const eDate = new Date(l.end_datetime).toLocaleDateString();
                const eTime = new Date(l.end_datetime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

                return (
                  <Card key={l.id} className="p-4 border bg-card hover:border-border/80 transition-all">
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <Badge className="text-[10px] bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30">
                            {l.reason_display}
                          </Badge>
                          <span className="text-xs font-bold text-foreground">
                            {sDate} {sTime} – {eDate} {eTime}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Scope: <strong>{l.clinic_name ? l.clinic_name : "All Affiliated Clinics"}</strong>
                        </p>
                        {l.notes && (
                          <p className="text-xs text-foreground/80 italic">"{l.notes}"</p>
                        )}
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteLeave(l.id)}
                        disabled={deleteLeaveMutation.isPending}
                        className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10"
                        title="Cancel Leave"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            <Card className="p-12 text-center border-dashed space-y-2">
              <UserX className="h-8 w-8 mx-auto text-muted-foreground stroke-1" />
              <h4 className="text-sm font-bold text-foreground">No Leaves Scheduled</h4>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                You have not scheduled any upcoming leaves or vacation periods. All recurring shifts are bookable.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* Record Leave Modal */}
      <DoctorUnavailabilityModal
        isOpen={isLeaveModalOpen}
        onClose={() => setIsLeaveModalOpen(false)}
        doctorId={doctor.id}
        doctorName={doctor.full_name}
        isDoctorRole={true}
      />

      {/* Availability Preview Modal */}
      {previewDoctorClinicId && (
        <AvailabilityPreviewModal
          isOpen={Boolean(previewDoctorClinicId)}
          onClose={() => setPreviewDoctorClinicId(null)}
          doctorClinicId={previewDoctorClinicId}
          doctorName={doctor.full_name}
        />
      )}
    </div>
  );
};
export default DoctorSchedulesPage;
