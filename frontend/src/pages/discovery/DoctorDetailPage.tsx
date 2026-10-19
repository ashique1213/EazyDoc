import { useState, useMemo, useEffect } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  Building2,
  MapPin,
  Calendar,
  Clock,
  Phone,
  Mail,
  Briefcase,
  Languages,
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  Info,
  CalendarCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useDoctorAvailability, useDoctorDetail } from "@/features/discovery";
import { useAuthStore } from "@/features/auth";
import { BookingReviewModal } from "@/features/appointments/BookingReviewModal";

export function DoctorDetailPage() {
  const { doctorId } = useParams<{ doctorId: string }>();
  const [searchParams] = useSearchParams();
  const initialClinicId = searchParams.get("clinicId") || "";

  const { data: doctor, isLoading, isError, error } = useDoctorDetail(doctorId);
  const { isAuthenticated, user } = useAuthStore();

  // Selected Clinic
  const locations = useMemo(() => doctor?.practice_locations || [], [doctor?.practice_locations]);
  const [selectedClinicId, setSelectedClinicId] = useState<string>("");

  // Sync selected clinic once doctor data is loaded
  useEffect(() => {
    if (locations.length > 0) {
      if (initialClinicId && locations.some((loc) => loc.clinic_id === initialClinicId)) {
        setSelectedClinicId(initialClinicId);
      } else if (!selectedClinicId) {
        setSelectedClinicId(locations[0].clinic_id);
      }
    }
  }, [locations, initialClinicId, selectedClinicId]);

  // Selected Date (defaults to today's date formatted as YYYY-MM-DD in local time)
  const todayStr = useMemo(() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }, []);

  const [selectedDate, setSelectedDate] = useState<string>(todayStr);

  // Selected Slot
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [isBookingModalOpen, setIsBookingModalOpen] = useState<boolean>(false);

  // Active clinic object
  const activeLocation = locations.find((l) => l.clinic_id === selectedClinicId) || locations[0];

  // Availability Query
  const {
    data: availability,
    isLoading: isLoadingSlots,
    isError: isSlotsError,
    refetch: refetchAvailability,
  } = useDoctorAvailability(
    activeLocation?.clinic_id,
    doctor?.id,
    selectedDate
  );

  // Group slots into time periods (Morning, Afternoon, Evening)
  const groupedSlots = useMemo(() => {
    if (!availability?.slots) return { morning: [], afternoon: [], evening: [] };

    const morning: typeof availability.slots = [];
    const afternoon: typeof availability.slots = [];
    const evening: typeof availability.slots = [];

    availability.slots.forEach((slot) => {
      const hour = parseInt(slot.start_time.split(":")[0], 10);
      if (hour < 12) {
        morning.push(slot);
      } else if (hour < 17) {
        afternoon.push(slot);
      } else {
        evening.push(slot);
      }
    });

    return { morning, afternoon, evening };
  }, [availability]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-12 sm:px-6">
        <div className="animate-pulse space-y-6">
          <div className="h-6 w-32 rounded bg-muted" />
          <div className="h-48 rounded-2xl bg-muted" />
          <div className="h-64 rounded-2xl bg-muted" />
        </div>
      </div>
    );
  }

  if (isError || !doctor) {
    return (
      <div className="container mx-auto px-4 py-16 sm:px-6">
        <div className="mx-auto max-w-lg rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <ShieldAlert className="mx-auto h-12 w-12 text-destructive" />
          <h2 className="mt-4 text-xl font-bold text-foreground">Doctor Not Found</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {error instanceof Error
              ? error.message
              : "This doctor profile is unavailable or currently ineligible for public discovery."}
          </p>
          <Link to="/doctors">
            <Button variant="outline" className="mt-6 gap-2">
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Doctors</span>
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/50 py-8 text-foreground dark:bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb & Navigation */}
        <div className="mb-6">
          <Link
            to="/doctors"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to search results</span>
          </Link>
        </div>

        {/* Doctor Profile Banner Card */}
        <div className="rounded-3xl border border-border/80 bg-card p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
            {/* Photo / Avatar */}
            <div className="relative flex-shrink-0">
              {doctor.profile_photo ? (
                <img
                  src={doctor.profile_photo}
                  alt={doctor.full_name}
                  className="h-28 w-28 rounded-3xl object-cover shadow-sm ring-1 ring-border sm:h-32 sm:w-32"
                />
              ) : (
                <div className="flex h-28 w-28 items-center justify-center rounded-3xl bg-gradient-to-br from-teal-500/20 to-blue-500/20 text-3xl font-extrabold text-teal-700 dark:text-teal-400 ring-1 ring-teal-500/30 sm:h-32 sm:w-32">
                  {doctor.full_name
                    .replace(/^Dr\.\s*/i, "")
                    .split(" ")
                    .map((n) => n[0])
                    .slice(0, 2)
                    .join("")}
                </div>
              )}
              {doctor.is_verified && (
                <span
                  className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 text-white shadow ring-2 ring-background"
                  title="Super Admin Verified"
                >
                  <CheckCircle2 className="h-4 w-4" />
                </span>
              )}
            </div>

            {/* Core Info */}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl text-foreground">
                  {doctor.full_name}
                </h1>
                <Badge variant="success" className="gap-1 px-2.5 py-0.5 text-xs font-semibold">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Verified Practitioner
                </Badge>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span className="font-semibold text-primary">{doctor.specialization}</span>
                <span>•</span>
                <span>{doctor.qualifications}</span>
                <span>•</span>
                <span className="inline-flex items-center gap-1 font-medium text-foreground">
                  <Briefcase className="h-4 w-4 text-muted-foreground" />
                  {doctor.years_of_experience} years clinical experience
                </span>
              </div>

              {doctor.languages && (
                <div className="mt-2.5 flex items-center gap-2 text-xs text-muted-foreground">
                  <Languages className="h-4 w-4 text-muted-foreground" />
                  <span>Languages Spoken: <strong className="text-foreground">{doctor.languages}</strong></span>
                </div>
              )}

              {doctor.bio && (
                <div className="mt-4 rounded-2xl bg-muted/30 p-4 text-sm leading-relaxed text-muted-foreground">
                  <h2 className="text-xs font-bold uppercase tracking-wider text-foreground">About the Doctor</h2>
                  <p className="mt-1">{doctor.bio}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Practice Locations & Schedule Grid */}
        <div className="mt-8 grid gap-8 lg:grid-cols-3">
          {/* Left Column: Practice Locations Selector */}
          <div className="space-y-4 lg:col-span-1">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Affiliated Clinics</h2>
              <span className="text-xs text-muted-foreground">{locations.length} Location{locations.length > 1 ? "s" : ""}</span>
            </div>

            <div className="space-y-3">
              {locations.map((loc) => {
                const isSelected = loc.clinic_id === selectedClinicId;
                return (
                  <button
                    key={loc.doctor_clinic_id}
                    type="button"
                    onClick={() => {
                      setSelectedClinicId(loc.clinic_id);
                      setSelectedSlot(null);
                    }}
                    className={`w-full rounded-2xl border p-4 text-left transition-all ${
                      isSelected
                        ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary"
                        : "border-border bg-card hover:border-primary/40 hover:bg-muted/20"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2.5">
                        <div
                          className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                            isSelected
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          <Building2 className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="text-sm font-bold text-foreground">{loc.clinic_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {loc.city}, {loc.state}
                          </div>
                        </div>
                      </div>
                      {isSelected && (
                        <Badge variant="default" className="text-[10px]">
                          Selected
                        </Badge>
                      )}
                    </div>

                    <div className="mt-3 flex items-start gap-1.5 text-xs text-muted-foreground">
                      <MapPin className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
                      <span className="line-clamp-1">{loc.address_line_1}</span>
                    </div>

                    <div className="mt-3 flex items-center justify-between border-t border-border/50 pt-2.5 text-xs">
                      <div>
                        <span className="text-muted-foreground">Consultation Fee:</span>{" "}
                        <span className="font-bold text-emerald-600 dark:text-emerald-400">
                          ₹{loc.consultation_fee}
                        </span>
                      </div>
                      <div className="text-muted-foreground">
                        {loc.appointment_duration_minutes} min slot
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Selected Clinic Details Card */}
            {activeLocation && (
              <Card className="border-border/80 bg-card shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold">Clinic Contact Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Phone className="h-3.5 w-3.5 text-primary" />
                    <span>{activeLocation.phone}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Mail className="h-3.5 w-3.5 text-primary" />
                    <span>{activeLocation.email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-3.5 w-3.5 text-primary" />
                    <span>Timezone: {activeLocation.timezone}</span>
                  </div>
                  <div className="pt-2">
                    <Link
                      to={`/clinics/${activeLocation.clinic_id}`}
                      className="text-xs font-semibold text-primary hover:underline"
                    >
                      View Clinic Page →
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column: Date & Slot Booking Section */}
          <div className="space-y-6 lg:col-span-2">
            <Card className="rounded-3xl border-border/80 shadow-sm">
              <CardHeader className="border-b border-border/60 pb-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <CardTitle className="text-xl font-bold">Select Date & Time Slot</CardTitle>
                    <CardDescription className="mt-1">
                      Showing real-time availability at{" "}
                      <strong className="text-foreground">{activeLocation?.clinic_name}</strong>
                    </CardDescription>
                  </div>

                  {/* Date Input */}
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-4 w-4 text-primary" />
                    <input
                      type="date"
                      aria-label="Appointment Date"
                      min={todayStr}
                      value={selectedDate}
                      onChange={(e) => {
                        setSelectedDate(e.target.value);
                        setSelectedSlot(null);
                      }}
                      className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm font-medium shadow-sm"
                    />
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-6">
                {/* Slots Loading State */}
                {isLoadingSlots && (
                  <div className="py-12 text-center">
                    <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <p className="mt-3 text-sm text-muted-foreground">Checking available clinic slots...</p>
                  </div>
                )}

                {/* Slots Error State */}
                {isSlotsError && (
                  <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-6 text-center text-sm text-destructive">
                    <p className="font-semibold">Unable to fetch appointment slots for this date.</p>
                    <p className="mt-1 text-xs text-muted-foreground">Please choose another date or check back later.</p>
                  </div>
                )}

                {/* Available Slots Display */}
                {!isLoadingSlots && !isSlotsError && availability && (
                  <div className="space-y-6">
                    {/* Status header banner */}
                    <div className="flex flex-wrap items-center justify-between rounded-xl bg-muted/40 px-4 py-2.5 text-xs">
                      <div className="flex items-center space-x-2">
                        <CalendarCheck className="h-4 w-4 text-teal-600 dark:text-teal-400" />
                        <span className="font-medium text-foreground">
                          {availability.day_name}, {availability.date}
                        </span>
                      </div>
                      <div className="font-semibold text-foreground">
                        {availability.available_slots_count > 0 ? (
                          <span className="text-emerald-600 dark:text-emerald-400">
                            {availability.available_slots_count} slots open
                          </span>
                        ) : (
                          <span className="text-muted-foreground">No open slots on this date</span>
                        )}
                      </div>
                    </div>

                    {availability.total_slots === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border p-8 text-center">
                        <Clock className="mx-auto h-10 w-10 text-muted-foreground/60" />
                        <h4 className="mt-3 text-sm font-bold text-foreground">Doctor has no scheduled shifts on this day</h4>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Dr. {doctor.full_name} does not practice at {activeLocation?.clinic_name} on {availability.day_name}s.
                          Try picking another day of the week.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-5">
                        {/* Morning Slots */}
                        {groupedSlots.morning.length > 0 && (
                          <div>
                            <div className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                              Morning Shifts (Before 12:00 PM)
                            </div>
                            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
                              {groupedSlots.morning.map((slot) => {
                                const isSelected = selectedSlot === slot.start_time;
                                return (
                                  <button
                                    key={slot.start_time}
                                    type="button"
                                    disabled={!slot.is_available}
                                    onClick={() => setSelectedSlot(slot.start_time)}
                                    title={slot.reason || (slot.is_available ? "Available" : "Unavailable")}
                                    className={`rounded-xl border px-3 py-2 text-center text-xs font-medium transition-all ${
                                      isSelected
                                        ? "border-primary bg-primary text-primary-foreground shadow-sm ring-2 ring-primary ring-offset-2"
                                        : slot.is_available
                                        ? "border-emerald-500/40 bg-emerald-50/50 text-emerald-900 hover:border-emerald-600 hover:bg-emerald-100 dark:bg-emerald-950/20 dark:text-emerald-300"
                                        : "cursor-not-allowed border-border/40 bg-muted/30 text-muted-foreground/50 line-through"
                                    }`}
                                  >
                                    {slot.start_time}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* Afternoon Slots */}
                        {groupedSlots.afternoon.length > 0 && (
                          <div>
                            <div className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                              Afternoon Shifts (12:00 PM – 5:00 PM)
                            </div>
                            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
                              {groupedSlots.afternoon.map((slot) => {
                                const isSelected = selectedSlot === slot.start_time;
                                return (
                                  <button
                                    key={slot.start_time}
                                    type="button"
                                    disabled={!slot.is_available}
                                    onClick={() => setSelectedSlot(slot.start_time)}
                                    title={slot.reason || (slot.is_available ? "Available" : "Unavailable")}
                                    className={`rounded-xl border px-3 py-2 text-center text-xs font-medium transition-all ${
                                      isSelected
                                        ? "border-primary bg-primary text-primary-foreground shadow-sm ring-2 ring-primary ring-offset-2"
                                        : slot.is_available
                                        ? "border-emerald-500/40 bg-emerald-50/50 text-emerald-900 hover:border-emerald-600 hover:bg-emerald-100 dark:bg-emerald-950/20 dark:text-emerald-300"
                                        : "cursor-not-allowed border-border/40 bg-muted/30 text-muted-foreground/50 line-through"
                                    }`}
                                  >
                                    {slot.start_time}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* Evening Slots */}
                        {groupedSlots.evening.length > 0 && (
                          <div>
                            <div className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                              Evening Shifts (After 5:00 PM)
                            </div>
                            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
                              {groupedSlots.evening.map((slot) => {
                                const isSelected = selectedSlot === slot.start_time;
                                return (
                                  <button
                                    key={slot.start_time}
                                    type="button"
                                    disabled={!slot.is_available}
                                    onClick={() => setSelectedSlot(slot.start_time)}
                                    title={slot.reason || (slot.is_available ? "Available" : "Unavailable")}
                                    className={`rounded-xl border px-3 py-2 text-center text-xs font-medium transition-all ${
                                      isSelected
                                        ? "border-primary bg-primary text-primary-foreground shadow-sm ring-2 ring-primary ring-offset-2"
                                        : slot.is_available
                                        ? "border-emerald-500/40 bg-emerald-50/50 text-emerald-900 hover:border-emerald-600 hover:bg-emerald-100 dark:bg-emerald-950/20 dark:text-emerald-300"
                                        : "cursor-not-allowed border-border/40 bg-muted/30 text-muted-foreground/50 line-through"
                                    }`}
                                  >
                                    {slot.start_time}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Booking Call to Action Banner */}
                {selectedSlot && (
                  <div className="mt-8 rounded-2xl border border-primary/30 bg-primary/5 p-5">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-primary" />
                          <span className="text-sm font-bold text-foreground">Selected Appointment Slot</span>
                        </div>
                        <div className="mt-1 text-sm text-muted-foreground">
                          {selectedDate} at <strong className="text-foreground">{selectedSlot}</strong> at{" "}
                          <strong className="text-foreground">{activeLocation?.clinic_name}</strong>
                        </div>
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          Fee: <strong className="text-emerald-600 dark:text-emerald-400">₹{activeLocation?.consultation_fee}</strong> (Payable upon confirmation)
                        </div>
                      </div>

                      {isAuthenticated && user?.role === "PATIENT" ? (
                        <Button
                          size="lg"
                          onClick={() => setIsBookingModalOpen(true)}
                          className="w-full gap-2 font-bold sm:w-auto"
                        >
                          <CalendarCheck className="h-4 w-4" />
                          <span>Review & Book Slot</span>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      ) : (
                        <Link to={`/login?redirect=/doctors/${doctor.id}?clinicId=${activeLocation?.clinic_id}`}>
                          <Button size="lg" className="w-full gap-2 sm:w-auto">
                            <span>Sign in to Book</span>
                            <ArrowRight className="h-4 w-4" />
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                )}

                {/* Booking Review Modal */}
                {isBookingModalOpen && activeLocation && selectedSlot && (
                  (() => {
                    const slotObj = availability?.slots.find((s) => s.start_time === selectedSlot);
                    if (!slotObj) return null;
                    return (
                      <BookingReviewModal
                        isOpen={isBookingModalOpen}
                        onClose={() => setIsBookingModalOpen(false)}
                        doctor={doctor}
                        clinicLocation={activeLocation}
                        selectedDate={selectedDate}
                        selectedSlot={slotObj}
                        onSlotConflict={() => {
                          refetchAvailability();
                        }}
                      />
                    );
                  })()
                )}
              </CardContent>
            </Card>

            {/* Public Scope Notice */}
            <div className="flex items-start gap-2.5 rounded-xl border border-border/70 bg-muted/20 p-4 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-4 w-4 text-primary flex-shrink-0" />
              <span>
                <strong>Discovery Mode:</strong> Slots shown are real-time candidates computed from recurring shift schedules and live leave calendars. Selecting a slot does not create a reservation until confirmed in the patient booking flow.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DoctorDetailPage;
