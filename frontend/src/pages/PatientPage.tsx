import { Link } from "react-router-dom";
import {
  Calendar,
  FileText,
  Clock,
  Receipt,
  Search,
  ArrowRight,
  Building2,
  CalendarDays,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useMyAppointments } from "@/features/appointments";

export function PatientPage() {
  const { data: upcomingData, isLoading: loadingUpcoming } = useMyAppointments({
    filter: "upcoming",
  });
  const { data: pastData, isLoading: loadingPast } = useMyAppointments({
    filter: "past",
  });

  const upcomingCount = upcomingData?.count ?? 0;
  const pastCount = pastData?.count ?? 0;
  const recentUpcoming = upcomingData?.results?.slice(0, 3) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Patient Portal</h1>
          <p className="text-sm text-muted-foreground">
            Manage your doctor consultations, clinic visits, and health appointments.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/doctors">
            <Button size="sm" className="gap-2 font-bold shadow-sm">
              <Search className="h-4 w-4" />
              <span>Book Appointment</span>
            </Button>
          </Link>
          <Link to="/my-appointments">
            <Button size="sm" variant="outline" className="gap-2">
              <Calendar className="h-4 w-4" />
              <span>View All</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="rounded-2xl border border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Upcoming Visits
            </CardTitle>
            <Calendar className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-foreground">
              {loadingUpcoming ? "--" : upcomingCount}
            </div>
            <p className="text-xs text-muted-foreground">Active bookings</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Completed Visits
            </CardTitle>
            <Clock className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-foreground">
              {loadingPast ? "--" : pastCount}
            </div>
            <p className="text-xs text-muted-foreground">Past consultations</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Prescriptions
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-muted-foreground">0</div>
            <p className="text-xs text-muted-foreground">Coming in Day 11</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Invoices & Receipts
            </CardTitle>
            <Receipt className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-muted-foreground">0</div>
            <p className="text-xs text-muted-foreground">Coming in Day 10</p>
          </CardContent>
        </Card>
      </div>

      {/* Upcoming Consultations Widget */}
      <Card className="rounded-2xl border border-border shadow-sm">
        <CardHeader className="border-b border-border/60 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base font-bold">Next Upcoming Consultations</CardTitle>
              <CardDescription className="text-xs">
                Your closest confirmed visits with doctors and healthcare clinics.
              </CardDescription>
            </div>
            <Link to="/my-appointments">
              <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
                <span>View Full Schedule</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {loadingUpcoming ? (
            <div className="py-8 text-center text-xs text-muted-foreground animate-pulse">
              Loading schedule...
            </div>
          ) : recentUpcoming.length === 0 ? (
            <div className="py-10 text-center">
              <CalendarDays className="h-10 w-10 mx-auto text-muted-foreground/40 mb-2" />
              <p className="text-sm font-semibold text-foreground">No upcoming visits booked</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Ready to schedule a checkup or consult with a top specialist?
              </p>
              <div className="mt-4">
                <Link to="/doctors">
                  <Button size="sm" className="gap-2">
                    <Search className="h-3.5 w-3.5" />
                    <span>Find Doctors & Available Slots</span>
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {recentUpcoming.map((appt) => {
                const startDate = new Date(appt.start_at);
                const dateStr = startDate.toLocaleDateString("en-IN", {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                });
                const timeStr = startDate.toLocaleTimeString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: true,
                });

                return (
                  <div
                    key={appt.id}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3.5 rounded-xl border border-border/70 hover:border-primary/40 bg-card transition-all gap-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary font-bold flex items-center justify-center flex-shrink-0 text-sm">
                        {appt.doctor_name.charAt(0)}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-foreground">{appt.doctor_name}</div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <Building2 className="h-3 w-3 text-primary" />
                          <span>{appt.clinic_name}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-3 text-xs">
                      <div className="text-right">
                        <div className="font-semibold text-foreground">{dateStr} at {timeStr}</div>
                        <div className="text-emerald-600 font-bold">₹{appt.consultation_fee}</div>
                      </div>

                      <Link to={`/appointments/${appt.id}`}>
                        <Button size="sm" variant="outline" className="text-xs h-8">
                          Details
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
    </div>
  );
}

export default PatientPage;
