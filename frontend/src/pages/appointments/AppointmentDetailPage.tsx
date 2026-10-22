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
  RotateCcw,
  Ban,
  History,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  useAppointmentDetail,
  AppointmentCancelDialog,
  AppointmentRescheduleModal,
  AppointmentHistoryTimeline,
  ReportUnavailabilityModal,
} from "@/features/appointments";
import type { AppointmentStatus } from "@/features/appointments";
import { AppointmentPaymentCard } from "@/features/payments";
import { useAuthStore } from "@/features/auth";

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
    case "RESCHEDULE_REQUIRED":
      return (
        <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 font-semibold gap-1.5 py-1 px-3">
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Requires Rescheduling</span>
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
  const { data: appointment, isLoading, isError, error, refetch } = useAppointmentDetail(appointmentId);
  const { user } = useAuthStore();
  const [copied, setCopied] = useState(false);

  // Modals state
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [isRescheduleOpen, setIsRescheduleOpen] = useState(false);
  const [isUnavailOpen, setIsUnavailOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(true);

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

  const isPatient = user?.role === "PATIENT";
  const isDoctor = user?.role === "DOCTOR";
  const isClinicStaff = user?.role === "CLINIC_OWNER" || user?.role === "STAFF";

  const isEligibleToCancel = appointment.is_cancellable || appointment.reschedule_required;
  const isEligibleToReschedule = appointment.is_reschedulable || appointment.reschedule_required;
  const canModify = appointment.status === "CONFIRMED" || appointment.status === "PENDING_CONFIRMATION" || appointment.status === "RESCHEDULE_REQUIRED";

  return (
    <div className="container mx-auto max-w-3xl px-4 py-10 sm:px-6 space-y-6">
      {/* Top Banner based on status */}
      {appointment.status === "CONFIRMED" && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-50/60 p-6 text-center dark:bg-emerald-950/20">
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

      {appointment.status === "RESCHEDULE_REQUIRED" && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-50/70 p-6 text-center dark:bg-amber-950/20 space-y-2">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-black text-amber-900 dark:text-amber-200">
            Doctor Unavailability Reported — Rescheduling Required
          </h2>
          <p className="text-xs text-amber-800/80 dark:text-amber-300/80 max-w-md mx-auto">
            {appointment.cancellation_reason || "The doctor or clinic reported an unexpected schedule conflict."}
          </p>
          <div className="pt-2">
            <Button
              onClick={() => setIsRescheduleOpen(true)}
              className="gap-2 font-bold bg-amber-600 hover:bg-amber-700 text-white"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Choose Replacement Slot Now</span>
            </Button>
          </div>
        </div>
      )}

      {appointment.status === "CANCELLED" && (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-6 text-center space-y-2">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-destructive/15 text-destructive">
            <AlertCircle className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-black text-destructive">
            Appointment Cancelled
          </h2>
          {appointment.cancellation_reason && (
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Reason: "{appointment.cancellation_reason}"
            </p>
          )}
          {appointment.cancelled_at && (
            <p className="text-[11px] text-muted-foreground font-mono">
              Cancelled on: {new Date(appointment.cancelled_at).toLocaleString("en-IN")}
            </p>
          )}
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

            <div className="flex items-center gap-2">
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

          {/* Payment & Fee Card */}
          {appointment.status !== "CANCELLED" && isPatient ? (
            <AppointmentPaymentCard
              appointmentId={appointment.id}
              doctorName={appointment.doctor.full_name}
              clinicName={appointment.clinic.name}
              appointmentDateTime={`${dateFormatted} at ${timeFormatted}`}
              consultationFee={appointment.consultation_fee}
              currency={appointment.currency}
              initialPaymentStatus={appointment.payment_status || "PENDING"}
              patientName={user ? `${user.first_name || ""} ${user.last_name || ""}`.trim() : undefined}
              patientEmail={user?.email}
              patientPhone={user?.phone || undefined}
              onPaymentSuccess={() => {
                refetch();
              }}
            />
          ) : (
            <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-50/30 p-4 dark:bg-emerald-950/10">
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                  <CreditCard className="h-4 w-4 text-emerald-600" />
                  <span>Consultation Fee (Snapshot)</span>
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {appointment.payment_status === "PAID"
                    ? "Paid securely via Razorpay."
                    : "Locked at booking time."}
                </div>
              </div>

              <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                ₹{appointment.consultation_fee}
              </div>
            </div>
          )}

          {/* Policy & Cutoff Card */}
          {canModify && (
            <div className="rounded-xl border border-border bg-muted/10 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Cancellation & Rescheduling Eligibility
                </span>
                <Badge variant="outline" className="text-[10px]">
                  TZ: {appointment.clinic.timezone || "Asia/Kolkata"}
                </Badge>
              </div>

              <div className="text-xs text-muted-foreground space-y-1">
                {appointment.reschedule_required ? (
                  <p className="text-amber-700 dark:text-amber-300 font-semibold">
                    Authorized Exception: You may reschedule or cancel freely without cutoff limits.
                  </p>
                ) : isEligibleToCancel ? (
                  <p>
                    Eligible for cancellation & rescheduling until{" "}
                    <strong>11:59:59 PM</strong> on the day before the appointment in the clinic's local timezone.
                  </p>
                ) : (
                  <p className="text-destructive font-semibold">
                    Cutoff has passed for patient self-service modifications. Changes require authorized staff resolution.
                  </p>
                )}
              </div>

              {/* Action Buttons for Patient */}
              {isPatient && (
                <div className="flex flex-wrap gap-2 pt-2 border-t border-border/40">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setIsRescheduleOpen(true)}
                    disabled={!isEligibleToReschedule}
                    className="gap-1.5 text-xs font-bold"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    <span>Reschedule Visit</span>
                  </Button>

                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setIsCancelOpen(true)}
                    disabled={!isEligibleToCancel}
                    className="gap-1.5 text-xs text-destructive hover:bg-destructive/10 border-destructive/30"
                  >
                    <Ban className="h-3.5 w-3.5" />
                    <span>Cancel Appointment</span>
                  </Button>
                </div>
              )}

              {/* Action Buttons for Doctor or Clinic Staff */}
              {(isDoctor || isClinicStaff) && (
                <div className="flex flex-wrap gap-2 pt-2 border-t border-border/40">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setIsUnavailOpen(true)}
                    className="gap-1.5 text-xs font-bold text-amber-700 dark:text-amber-300 border-amber-500/40 hover:bg-amber-500/10"
                  >
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>Report Doctor / Clinic Unavailability</span>
                  </Button>

                  {isClinicStaff && (
                    <>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => setIsRescheduleOpen(true)}
                        className="gap-1.5 text-xs font-bold"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                        <span>Staff Override Reschedule</span>
                      </Button>

                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => setIsCancelOpen(true)}
                        className="gap-1.5 text-xs text-destructive hover:bg-destructive/10"
                      >
                        <Ban className="h-3.5 w-3.5" />
                        <span>Staff Override Cancel</span>
                      </Button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Patient Note */}
          {appointment.patient_note && (
            <div className="rounded-xl border border-border/60 bg-muted/20 p-4 space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-primary" /> Patient Note
              </span>
              <p className="text-xs text-foreground italic pt-1">{appointment.patient_note}</p>
            </div>
          )}

          {/* Audit History Timeline */}
          <div className="pt-2">
            <div className="flex items-center justify-between pb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Lifecycle & Audit Trail
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
                className="text-xs h-7 gap-1"
              >
                <History className="h-3.5 w-3.5" />
                <span>{showHistory ? "Hide History" : "Show History"}</span>
              </Button>
            </div>

            {showHistory && (
              <AppointmentHistoryTimeline appointmentId={appointment.id} />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Footer */}
      <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-2">
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

      {/* Cancellation Dialog */}
      <AppointmentCancelDialog
        isOpen={isCancelOpen}
        onClose={() => setIsCancelOpen(false)}
        appointment={appointment}
        onSuccess={() => refetch()}
      />

      {/* Reschedule Modal */}
      <AppointmentRescheduleModal
        isOpen={isRescheduleOpen}
        onClose={() => setIsRescheduleOpen(false)}
        appointment={appointment}
        onSuccess={() => refetch()}
      />

      {/* Doctor / Clinic Unavailability Modal */}
      <ReportUnavailabilityModal
        isOpen={isUnavailOpen}
        onClose={() => setIsUnavailOpen(false)}
        appointment={appointment}
        clinicScope={isClinicStaff}
        onSuccess={() => refetch()}
      />
    </div>
  );
}

export default AppointmentDetailPage;
