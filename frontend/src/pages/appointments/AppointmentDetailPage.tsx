import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CheckCircle2,
  Calendar,
  Clock,
  Building2,
  MapPin,
  Phone,
  Mail,
  Copy,
  Check,
  CreditCard,
  FileText,
  Printer,
  ArrowRight,
  ShieldAlert,
  AlertCircle,
  HelpCircle,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useAppointmentDetail } from "@/features/appointments";
import type { AppointmentStatus } from "@/features/appointments";

function StatusBadge({ status }: { status: AppointmentStatus }) {
  switch (status) {
    case "CONFIRMED":
      return (
        <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 font-semibold gap-1.5 py-1 px-3">
          <CheckCircle2 className="h-3.5 w-3.5" />
          <span>Confirmed</span>
        </Badge>
      );
    case "COMPLETED":
      return (
        <Badge className="bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30 font-semibold gap-1.5 py-1 px-3">
          <CheckCircle2 className="h-3.5 w-3.5" />
          <span>Completed</span>
        </Badge>
      );
    case "CANCELLED":
      return (
        <Badge className="bg-destructive/15 text-destructive border-destructive/30 font-semibold gap-1.5 py-1 px-3">
          <AlertCircle className="h-3.5 w-3.5" />
          <span>Cancelled</span>
        </Badge>
      );
    case "NO_SHOW":
      return (
        <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 font-semibold gap-1.5 py-1 px-3">
          <HelpCircle className="h-3.5 w-3.5" />
          <span>No Show</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="font-semibold gap-1.5 py-1 px-3">
          <span>{status}</span>
        </Badge>
      );
  }
}

export function AppointmentDetailPage() {
  const { appointmentId } = useParams<{ appointmentId: string }>();
  const { data: appointment, isLoading, isError, error } = useAppointmentDetail(appointmentId);
  const [copied, setCopied] = useState(false);

  const handleCopyReference = () => {
    if (appointment?.booking_reference) {
      navigator.clipboard.writeText(appointment.booking_reference);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <div className="animate-pulse space-y-6">
          <div className="h-10 w-48 rounded bg-muted" />
          <div className="h-64 rounded-2xl bg-muted" />
          <div className="h-48 rounded-2xl bg-muted" />
        </div>
      </div>
    );
  }

  if (isError || !appointment) {
    return (
      <div className="container mx-auto max-w-xl px-4 py-16 sm:px-6">
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <ShieldAlert className="mx-auto h-12 w-12 text-destructive" />
          <h2 className="mt-4 text-xl font-bold text-foreground">Appointment Not Found</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {error instanceof Error
              ? error.message
              : "This appointment does not exist or you do not have permission to view it."}
          </p>
          <div className="mt-6">
            <Link to="/my-appointments">
              <Button variant="outline" className="gap-2">
                <span>View My Appointments</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Format date and time
  const startDate = new Date(appointment.start_at);
  const endDate = new Date(appointment.end_at);

  const dateFormatted = startDate.toLocaleDateString("en-IN", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const timeFormatted = `${startDate.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  })} – ${endDate.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  })}`;

  return (
    <div className="container mx-auto max-w-3xl px-4 py-10 sm:px-6">
      {/* Success Top Banner */}
      {appointment.status === "CONFIRMED" && (
        <div className="mb-6 rounded-2xl border border-emerald-500/30 bg-emerald-50/60 p-6 text-center dark:bg-emerald-950/20">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <h1 className="mt-3 text-2xl font-black tracking-tight text-foreground sm:text-3xl">
            Appointment Confirmed!
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your consultation has been reserved. Please find your visit details below.
          </p>
        </div>
      )}

      {/* Main Appointment Details Card */}
      <Card className="rounded-2xl border border-border shadow-sm overflow-hidden">
        <CardHeader className="border-b border-border/60 bg-muted/20 pb-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Booking Reference
              </span>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xl font-mono font-extrabold text-foreground">
                  {appointment.booking_reference}
                </span>
                <button
                  type="button"
                  onClick={handleCopyReference}
                  title="Copy reference"
                  className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <StatusBadge status={appointment.status} />
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6 pt-6">
          {/* Doctor Details */}
          <div className="flex items-start gap-4 rounded-xl border border-border/60 bg-background p-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-xl font-black text-primary">
              {appointment.doctor.full_name.charAt(0)}
            </div>
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Healthcare Professional
              </span>
              <h3 className="text-lg font-bold text-foreground">{appointment.doctor.full_name}</h3>
              <p className="text-xs text-primary font-semibold">{appointment.doctor.specialization}</p>
              <p className="text-xs text-muted-foreground">{appointment.doctor.qualifications}</p>
            </div>
          </div>

          {/* Clinic & Location Details */}
          <div className="rounded-xl border border-border/60 bg-background p-4 space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Clinic & Location
            </span>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 font-bold text-foreground">
                <Building2 className="h-4 w-4 text-primary" />
                <span>{appointment.clinic.name}</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-muted-foreground pl-6">
                <MapPin className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                <span>
                  {appointment.clinic.address_line_1}
                  {appointment.clinic.address_line_2 ? `, ${appointment.clinic.address_line_2}` : ""},{" "}
                  {appointment.clinic.city}, {appointment.clinic.state} - {appointment.clinic.pincode}
                </span>
              </div>
              <div className="flex flex-wrap gap-4 pt-1 text-xs text-muted-foreground pl-6">
                {appointment.clinic.phone && (
                  <div className="flex items-center gap-1.5">
                    <Phone className="h-3 w-3" />
                    <span>{appointment.clinic.phone}</span>
                  </div>
                )}
                {appointment.clinic.email && (
                  <div className="flex items-center gap-1.5">
                    <Mail className="h-3 w-3" />
                    <span>{appointment.clinic.email}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Schedule Date & Time */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-xl border border-border/60 bg-background p-4 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-primary" /> Appointment Date
              </span>
              <div className="text-sm font-bold text-foreground pt-1">{dateFormatted}</div>
            </div>

            <div className="rounded-xl border border-border/60 bg-background p-4 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-primary" /> Scheduled Time Slot
              </span>
              <div className="text-sm font-bold text-foreground pt-1">{timeFormatted}</div>
              <p className="text-[11px] text-muted-foreground">
                ({appointment.clinic.timezone || "Asia/Kolkata"} Standard Time)
              </p>
            </div>
          </div>

          {/* Commercial Snapshot */}
          <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-50/30 p-4 dark:bg-emerald-950/10">
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                <CreditCard className="h-4 w-4 text-emerald-600" />
                <span>Consultation Fee (Snapshot)</span>
              </div>
              <div className="text-[11px] text-muted-foreground">
                Payable directly at the clinic. Locked at booking time.
              </div>
            </div>

            <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
              ₹{appointment.consultation_fee}
            </div>
          </div>

          {/* Patient Note */}
          {appointment.patient_note && (
            <div className="rounded-xl border border-border/60 bg-muted/20 p-4 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-primary" /> Patient Note
              </span>
              <p className="text-xs text-foreground italic pt-1">{appointment.patient_note}</p>
            </div>
          )}

          {/* Next Steps Advisory */}
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-primary">
              <Sparkles className="h-4 w-4" />
              <span>Important Instructions for Your Visit</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs text-muted-foreground">
              <li>Please arrive at {appointment.clinic.name} at least 15 minutes prior to {timeFormatted.split("–")[0].trim()}.</li>
              <li>Carry a valid photo ID and any previous medical prescriptions or lab reports.</li>
              <li>Present your booking reference <strong className="text-foreground">{appointment.booking_reference}</strong> at the clinic reception desk.</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Action Footer */}
      <div className="mt-8 flex flex-col-reverse sm:flex-row items-center justify-between gap-4">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => window.print()}
          className="gap-2 w-full sm:w-auto"
        >
          <Printer className="h-4 w-4" />
          <span>Print Confirmation</span>
        </Button>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Link to="/doctors" className="w-full sm:w-auto">
            <Button variant="outline" size="sm" className="w-full">
              Find More Doctors
            </Button>
          </Link>

          <Link to="/my-appointments" className="w-full sm:w-auto">
            <Button size="sm" className="w-full gap-2 font-bold">
              <span>My Appointments</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default AppointmentDetailPage;
