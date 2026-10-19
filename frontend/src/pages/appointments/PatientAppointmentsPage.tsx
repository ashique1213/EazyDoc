import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Calendar,
  Clock,
  Building2,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Search,
  CalendarDays,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useMyAppointments } from "@/features/appointments";
import type { AppointmentListItem, AppointmentStatus } from "@/features/appointments";

function StatusBadge({ status }: { status: AppointmentStatus }) {
  switch (status) {
    case "CONFIRMED":
      return (
        <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 font-semibold gap-1 py-0.5 px-2.5 text-xs">
          <CheckCircle2 className="h-3 w-3" />
          <span>Confirmed</span>
        </Badge>
      );
    case "COMPLETED":
      return (
        <Badge className="bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30 font-semibold gap-1 py-0.5 px-2.5 text-xs">
          <CheckCircle2 className="h-3 w-3" />
          <span>Completed</span>
        </Badge>
      );
    case "CANCELLED":
      return (
        <Badge className="bg-destructive/15 text-destructive border-destructive/30 font-semibold gap-1 py-0.5 px-2.5 text-xs">
          <AlertCircle className="h-3 w-3" />
          <span>Cancelled</span>
        </Badge>
      );
    case "NO_SHOW":
      return (
        <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 font-semibold gap-1 py-0.5 px-2.5 text-xs">
          <HelpCircle className="h-3 w-3" />
          <span>No Show</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-xs">
          {status}
        </Badge>
      );
  }
}

export function PatientAppointmentsPage() {
  const [activeTab, setActiveTab] = useState<"upcoming" | "past">("upcoming");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const { data, isLoading, isError, error } = useMyAppointments({
    filter: activeTab,
    status: statusFilter !== "ALL" ? statusFilter : undefined,
  });

  const appointments: AppointmentListItem[] = data?.results || [];

  return (
    <div className="container mx-auto max-w-4xl px-4 py-10 sm:px-6">
      {/* Page Title & Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <Badge variant="outline" className="text-primary border-primary/30 mb-1">
            Patient Portal
          </Badge>
          <h1 className="text-2xl font-black tracking-tight text-foreground sm:text-3xl">
            My Appointments
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Review your confirmed visits, schedule history, and consultation fees.
          </p>
        </div>

        <Link to="/doctors">
          <Button className="gap-2 font-bold shadow-sm">
            <Search className="h-4 w-4" />
            <span>Book New Appointment</span>
          </Button>
        </Link>
      </div>

      {/* Tabs and Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 border-b border-border pb-4 mb-6">
        <div className="flex items-center gap-2 bg-muted/40 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab("upcoming")}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-all ${
              activeTab === "upcoming"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Upcoming Consultations
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("past")}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-all ${
              activeTab === "past"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Past History
          </button>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-input bg-background px-3 py-1.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <option value="ALL">All Statuses</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="NO_SHOW">No Show</option>
          </select>
        </div>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-card p-5 h-36" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center text-xs text-destructive">
          <AlertCircle className="h-8 w-8 mx-auto mb-2 text-destructive" />
          <p className="font-bold text-sm">Failed to load appointments</p>
          <p className="text-muted-foreground mt-1">
            {error instanceof Error ? error.message : "Network error. Please try again."}
          </p>
        </div>
      ) : appointments.length === 0 ? (
        <div className="rounded-2xl border border-border/80 bg-muted/20 p-12 text-center">
          <CalendarDays className="h-12 w-12 mx-auto text-muted-foreground/60 mb-3" />
          <h3 className="text-base font-bold text-foreground">
            No {activeTab} appointments found
          </h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            {activeTab === "upcoming"
              ? "You do not have any upcoming doctor consultations booked right now."
              : "No historical appointments found matching your filter selection."}
          </p>
          <div className="mt-5">
            <Link to="/doctors">
              <Button size="sm" variant="outline" className="gap-2">
                <span>Explore Doctors & Clinics</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {appointments.map((appt) => {
            const startDate = new Date(appt.start_at);
            const endDate = new Date(appt.end_at);

            const dateStr = startDate.toLocaleDateString("en-IN", {
              weekday: "short",
              year: "numeric",
              month: "short",
              day: "numeric",
            });

            const timeStr = `${startDate.toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
              hour12: true,
            })} - ${endDate.toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
              hour12: true,
            })}`;

            return (
              <Card
                key={appt.id}
                className="rounded-2xl border border-border/80 shadow-sm hover:border-primary/40 transition-all overflow-hidden"
              >
                <CardContent className="p-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    {/* Left: Doctor & Clinic Info */}
                    <div className="flex items-start gap-4">
                      <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary font-bold text-base">
                        {appt.doctor_name.charAt(0)}
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="font-bold text-base text-foreground">
                            {appt.doctor_name}
                          </h4>
                          <span className="text-xs text-primary font-medium">
                            • {appt.specialization}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Building2 className="h-3 w-3 text-primary flex-shrink-0" />
                          <span>{appt.clinic_name}</span>
                          <span className="text-muted-foreground/60">({appt.clinic_city})</span>
                        </div>

                        <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3 text-primary" />
                            <span className="font-semibold text-foreground">{dateStr}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-primary" />
                            <span>{timeStr}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right: Fee, Status & Action */}
                    <div className="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 border-t sm:border-t-0 pt-3 sm:pt-0 border-border/50">
                      <div className="flex items-center gap-2 sm:flex-col sm:items-end">
                        <StatusBadge status={appt.status} />
                        <div className="text-sm font-black text-emerald-600 dark:text-emerald-400">
                          ₹{appt.consultation_fee}
                        </div>
                      </div>

                      <Link to={`/appointments/${appt.id}`}>
                        <Button size="sm" variant="outline" className="gap-1.5 text-xs font-semibold">
                          <span>Details</span>
                          <ArrowRight className="h-3 w-3" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default PatientAppointmentsPage;
