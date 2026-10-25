import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  User,
  CalendarDays,
  Ban,
  Stethoscope,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ClinicSwitcher,
  useActiveClinic,
  useClinicCalendar,
} from "@/features/clinicOperations";
import type { CalendarAppointment, CalendarClosure } from "@/features/clinicOperations/types";

export function ClinicCalendarPage() {
  const { activeClinic, activeClinicId } = useActiveClinic();
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [viewMode, setViewMode] = useState<"day" | "week">("week");

  // Calculate start and end dates based on viewMode
  const getBounds = () => {
    const start = new Date(currentDate);
    if (viewMode === "day") {
      const sStr = start.toISOString().split("T")[0];
      return { start_date: sStr, end_date: sStr };
    }
    // Week: Sunday to Saturday
    const day = start.getDay();
    const diff = start.getDate() - day;
    const sunday = new Date(start.setDate(diff));
    const saturday = new Date(sunday);
    saturday.setDate(sunday.getDate() + 6);
    return {
      start_date: sunday.toISOString().split("T")[0],
      end_date: saturday.toISOString().split("T")[0],
    };
  };

  const bounds = getBounds();
  const { data: calendarData, isLoading } = useClinicCalendar(activeClinicId, {
    start_date: bounds.start_date,
    end_date: bounds.end_date,
  });

  const navigateDate = (step: number) => {
    const next = new Date(currentDate);
    if (viewMode === "day") {
      next.setDate(next.getDate() + step);
    } else {
      next.setDate(next.getDate() + step * 7);
    }
    setCurrentDate(next);
  };

  const resetToToday = () => {
    setCurrentDate(new Date());
  };

  const appointments: CalendarAppointment[] = calendarData?.appointments || [];
  const shifts = calendarData?.shifts || [];
  const unavailabilities = calendarData?.unavailabilities || [];
  const closures: CalendarClosure[] = calendarData?.closures || [];

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between bg-card p-5 rounded-2xl border shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <CalendarIcon className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Clinic Master Calendar</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Coordinated doctor shifts, consultations, leaves, and closures in {activeClinic?.timezone || "clinic local time"}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <ClinicSwitcher />
        </div>
      </div>

      {/* Calendar Controls */}
      <Card>
        <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <Button size="sm" variant="outline" onClick={() => navigateDate(-1)} className="h-8 w-8 p-0">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={resetToToday} className="h-8 text-xs font-medium">
              Today
            </Button>
            <Button size="sm" variant="outline" onClick={() => navigateDate(1)} className="h-8 w-8 p-0">
              <ChevronRight className="h-4 w-4" />
            </Button>
            <span className="font-semibold text-foreground px-2">
              {viewMode === "day"
                ? currentDate.toLocaleDateString("en-IN", { dateStyle: "full" })
                : `${bounds.start_date} to ${bounds.end_date}`}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex rounded-lg border bg-muted/30 p-0.5">
              <button
                onClick={() => setViewMode("day")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "day" ? "bg-card shadow-xs text-foreground" : "text-muted-foreground"
                }`}
              >
                Day
              </button>
              <button
                onClick={() => setViewMode("week")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "week" ? "bg-card shadow-xs text-foreground" : "text-muted-foreground"
                }`}
              >
                Week
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Operational Closures Banner */}
      {closures.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 text-rose-900 px-4 py-3 rounded-xl space-y-1">
          <div className="flex items-center space-x-2 font-semibold text-xs">
            <Ban className="h-4 w-4 text-rose-600" />
            <span>Clinic Closure Active in this Range:</span>
          </div>
          {closures.map((c) => (
            <p key={c.id} className="text-xs text-rose-800 ml-6">
              • {c.start_date} to {c.end_date} — <strong>{c.reason}</strong> {c.notes ? `(${c.notes})` : ""}
            </p>
          ))}
        </div>
      )}

      {/* Main Calendar Grid */}
      <div className="grid gap-6 lg:grid-cols-4">
        {/* Appointments & Schedule View */}
        <Card className="lg:col-span-3">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-sm font-semibold">
              Consultation Schedule & Bookings ({appointments.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {isLoading ? (
              <div className="h-64 flex items-center justify-center text-xs text-muted-foreground">
                Loading calendar feeds...
              </div>
            ) : appointments.length === 0 ? (
              <div className="h-64 flex flex-col items-center justify-center text-center space-y-2">
                <CalendarDays className="h-10 w-10 text-muted-foreground/40" />
                <p className="text-sm font-medium">No appointments booked in this period.</p>
                <p className="text-xs text-muted-foreground">Doctor shifts remain active as configured.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {appointments.map((appt) => {
                  const localStart = new Date(appt.start_at).toLocaleTimeString("en-IN", {
                    timeZone: activeClinic?.timezone || "Asia/Kolkata",
                    hour: "2-digit",
                    minute: "2-digit",
                  });
                  const localEnd = new Date(appt.end_at).toLocaleTimeString("en-IN", {
                    timeZone: activeClinic?.timezone || "Asia/Kolkata",
                    hour: "2-digit",
                    minute: "2-digit",
                  });

                  return (
                    <div
                      key={appt.id}
                      className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-xl border bg-card hover:border-primary/40 transition-colors gap-2 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-primary">{localStart} - {localEnd}</span>
                          <span className="font-mono text-muted-foreground text-[11px]">{appt.booking_reference}</span>
                          <Badge
                            variant="outline"
                            className={
                              appt.status === "CONFIRMED"
                                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                : appt.status === "COMPLETED"
                                ? "bg-purple-50 text-purple-700 border-purple-200"
                                : "bg-muted text-muted-foreground"
                            }
                          >
                            {appt.status}
                          </Badge>
                        </div>
                        <div className="flex items-center space-x-4 text-muted-foreground">
                          <span className="flex items-center gap-1 font-medium text-foreground">
                            <User className="h-3.5 w-3.5 text-muted-foreground" /> {appt.patient_name}
                          </span>
                          <span className="flex items-center gap-1">
                            <Stethoscope className="h-3.5 w-3.5 text-muted-foreground" /> {appt.doctor_name}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Link to="/clinic/appointments">
                          <Button size="sm" variant="outline" className="h-7 text-[11px]">
                            Manage
                          </Button>
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sidebar: Recurring Shifts & Unavailabilities */}
        <div className="space-y-4">
          {/* Shifts */}
          <Card>
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Configured Shifts ({shifts.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-1 space-y-2 text-xs">
              {shifts.length === 0 ? (
                <p className="text-muted-foreground text-[11px]">No active recurring shifts.</p>
              ) : (
                shifts.map((s) => (
                  <div key={s.id} className="p-2 rounded-lg bg-muted/40 border">
                    <p className="font-semibold text-foreground">{s.doctor_name}</p>
                    <p className="text-muted-foreground text-[11px]">
                      {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][s.day_of_week]}: {s.start_time} - {s.end_time}
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {s.slot_duration_minutes} min slots
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Leaves & Unavailabilities */}
          <Card>
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Doctor Leaves ({unavailabilities.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-1 space-y-2 text-xs">
              {unavailabilities.length === 0 ? (
                <p className="text-muted-foreground text-[11px]">No doctor leaves in this period.</p>
              ) : (
                unavailabilities.map((u) => (
                  <div key={u.id} className="p-2 rounded-lg bg-amber-50/60 border border-amber-200">
                    <p className="font-semibold text-amber-900">{u.doctor_name}</p>
                    <p className="text-amber-800 text-[11px]">{u.reason}</p>
                    <p className="text-[10px] text-amber-700 mt-0.5">{u.notes}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default ClinicCalendarPage;
