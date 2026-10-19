import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Calendar,
  Clock,
  Building2,
  MapPin,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  CreditCard,
  ShieldCheck,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCreateAppointment } from "./hooks";
import type { PublicClinicLocation, PublicDoctor, AvailabilitySlot } from "@/features/discovery/types";

interface BookingReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  doctor: PublicDoctor;
  clinicLocation: PublicClinicLocation;
  selectedDate: string;
  selectedSlot: AvailabilitySlot;
  onBookingSuccess?: (appointmentId: string) => void;
  onSlotConflict?: () => void;
}

export function BookingReviewModal({
  isOpen,
  onClose,
  doctor,
  clinicLocation,
  selectedDate,
  selectedSlot,
  onBookingSuccess,
  onSlotConflict,
}: BookingReviewModalProps) {
  const navigate = useNavigate();
  const [patientNote, setPatientNote] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { mutate: createAppointment, isPending } = useCreateAppointment();

  // Generate unique idempotency key when modal opens
  useEffect(() => {
    if (isOpen) {
      setIdempotencyKey(crypto.randomUUID());
      setErrorMessage(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    setErrorMessage(null);

    // Format start_at ISO timestamp
    const startAtUtc = selectedSlot.start_datetime_utc;

    createAppointment(
      {
        payload: {
          clinic_id: clinicLocation.clinic_id,
          doctor_id: doctor.id,
          start_at: startAtUtc,
          patient_note: patientNote.trim(),
        },
        idempotencyKey,
      },
      {
        onSuccess: (data) => {
          onClose();
          if (onBookingSuccess) {
            onBookingSuccess(data.id);
          } else {
            navigate(`/appointments/${data.id}`);
          }
        },
        onError: (err: unknown) => {
          const axiosErr = err as {
            response?: {
              status?: number;
              data?: { message?: string; detail?: string };
            };
            message?: string;
          };
          const status = axiosErr?.response?.status;
          const detail =
            axiosErr?.response?.data?.message ||
            axiosErr?.response?.data?.detail ||
            axiosErr?.message ||
            "Unable to confirm booking. Please try again.";

          setErrorMessage(detail);

          if (status === 409) {
            // Trigger availability refresh on parent
            if (onSlotConflict) {
              onSlotConflict();
            }
          }
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl transition-all">
        {/* Close Button */}
        <button
          onClick={onClose}
          disabled={isPending}
          className="absolute right-4 top-4 rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Modal Header */}
        <div className="space-y-1">
          <Badge variant="outline" className="text-primary border-primary/30">
            Booking Review
          </Badge>
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Confirm Your Appointment
          </h2>
          <p className="text-xs text-muted-foreground">
            Please review the doctor, clinic, and schedule details before finalizing your booking.
          </p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mt-4 flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-3.5 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold">Booking Conflict / Notice</p>
              <p className="leading-relaxed">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Appointment Summary Card */}
        <div className="mt-5 space-y-4 rounded-xl border border-border/70 bg-muted/30 p-4">
          {/* Doctor Info */}
          <div className="flex items-center gap-3 border-b border-border/50 pb-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 font-bold text-primary text-base">
              {doctor.full_name.charAt(0)}
            </div>
            <div>
              <div className="text-sm font-bold text-foreground">{doctor.full_name}</div>
              <div className="text-xs text-muted-foreground">{doctor.specialization}</div>
            </div>
          </div>

          {/* Clinic Info */}
          <div className="space-y-1 border-b border-border/50 pb-3 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-foreground">
              <Building2 className="h-3.5 w-3.5 text-primary" />
              <span>{clinicLocation.clinic_name}</span>
            </div>
            <div className="flex items-start gap-1.5 text-muted-foreground pl-5">
              <MapPin className="h-3 w-3 mt-0.5 flex-shrink-0" />
              <span>
                {clinicLocation.address_line_1}, {clinicLocation.city}, {clinicLocation.state} - {clinicLocation.pincode}
              </span>
            </div>
          </div>

          {/* Date & Time Slot */}
          <div className="grid grid-cols-2 gap-3 text-xs border-b border-border/50 pb-3">
            <div className="space-y-0.5">
              <span className="text-muted-foreground flex items-center gap-1">
                <Calendar className="h-3 w-3 text-primary" /> Date
              </span>
              <span className="font-bold text-foreground">{selectedDate}</span>
            </div>

            <div className="space-y-0.5">
              <span className="text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3 text-primary" /> Time Slot
              </span>
              <span className="font-bold text-foreground">
                {selectedSlot.start_time} – {selectedSlot.end_time} ({clinicLocation.timezone || "Asia/Kolkata"})
              </span>
            </div>
          </div>

          {/* Consultation Fee */}
          <div className="flex items-center justify-between text-xs pt-1">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <CreditCard className="h-3.5 w-3.5 text-emerald-600" />
              <span>Consultation Fee</span>
            </div>
            <div className="text-base font-extrabold text-emerald-600 dark:text-emerald-400">
              ₹{clinicLocation.consultation_fee}
            </div>
          </div>
        </div>

        {/* Patient Note Field */}
        <div className="mt-4 space-y-1.5">
          <label className="text-xs font-semibold text-foreground flex items-center gap-1">
            <FileText className="h-3 w-3 text-muted-foreground" /> Note for the Doctor (Optional)
          </label>
          <textarea
            value={patientNote}
            onChange={(e) => setPatientNote(e.target.value)}
            maxLength={1000}
            rows={2}
            placeholder="Brief reason for consultation or symptoms..."
            disabled={isPending}
            className="w-full rounded-xl border border-input bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
          />
        </div>

        {/* Security / No Platform Fee Trust Badge */}
        <div className="mt-4 flex items-center gap-2 text-[11px] text-muted-foreground">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />
          <span>Payable at the clinic upon arrival. No additional platform booking fee.</span>
        </div>

        {/* Modal Action Buttons */}
        <div className="mt-6 flex items-center justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={isPending}
          >
            Cancel
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={handleConfirm}
            disabled={isPending}
            className="gap-2 font-bold"
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Reserving Slot...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                <span>Confirm Booking</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
