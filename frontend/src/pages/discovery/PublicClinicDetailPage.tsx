import { Link, useParams } from "react-router-dom";
import {
  Building2,
  MapPin,
  Phone,
  Mail,
  Clock,
  CheckCircle2,
  ArrowLeft,
  ArrowRight,
  Users,
  Briefcase,
  ShieldAlert,
  CalendarCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useClinicDetail } from "@/features/discovery";

export function PublicClinicDetailPage() {
  const { clinicId } = useParams<{ clinicId: string }>();
  const { data: clinic, isLoading, isError, error } = useClinicDetail(clinicId);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-12 sm:px-6">
        <div className="animate-pulse space-y-6">
          <div className="h-6 w-32 rounded bg-muted" />
          <div className="h-44 rounded-2xl bg-muted" />
          <div className="h-64 rounded-2xl bg-muted" />
        </div>
      </div>
    );
  }

  if (isError || !clinic) {
    return (
      <div className="container mx-auto px-4 py-16 sm:px-6">
        <div className="mx-auto max-w-lg rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <ShieldAlert className="mx-auto h-12 w-12 text-destructive" />
          <h2 className="mt-4 text-xl font-bold text-foreground">Clinic Not Found</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {error instanceof Error
              ? error.message
              : "This clinic profile is unavailable or currently not approved for public discovery."}
          </p>
          <Link to="/clinics">
            <Button variant="outline" className="mt-6 gap-2">
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Clinics</span>
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const doctors = clinic.doctors || [];

  return (
    <div className="min-h-screen bg-slate-50/50 py-8 text-foreground dark:bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Navigation Breadcrumb */}
        <div className="mb-6">
          <Link
            to="/clinics"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to all clinics</span>
          </Link>
        </div>

        {/* Clinic Header Banner Card */}
        <div className="rounded-3xl border border-border/80 bg-card p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
            {/* Logo */}
            <div className="relative flex-shrink-0">
              {clinic.logo ? (
                <img
                  src={clinic.logo}
                  alt={clinic.name}
                  className="h-24 w-24 rounded-2xl object-cover shadow-sm ring-1 ring-border sm:h-28 sm:w-28"
                />
              ) : (
                <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500/20 to-blue-500/20 text-teal-700 dark:text-teal-400 ring-1 ring-teal-500/30 sm:h-28 sm:w-28">
                  <Building2 className="h-12 w-12" />
                </div>
              )}
            </div>

            {/* Info */}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl text-foreground">
                  {clinic.name}
                </h1>
                <Badge variant="success" className="gap-1 px-2.5 py-0.5 text-xs font-semibold">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Approved Facility
                </Badge>
              </div>

              {/* Address */}
              <div className="mt-2 flex items-start gap-1.5 text-sm text-muted-foreground">
                <MapPin className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                <span>
                  {clinic.address_line_1}
                  {clinic.address_line_2 ? `, ${clinic.address_line_2}` : ""}, {clinic.city},{" "}
                  {clinic.state} - {clinic.pincode}, {clinic.country}
                </span>
              </div>

              {/* Public Contact */}
              <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                {clinic.phone && (
                  <div className="flex items-center gap-1.5">
                    <Phone className="h-3.5 w-3.5 text-primary" />
                    <span>{clinic.phone}</span>
                  </div>
                )}
                {clinic.email && (
                  <div className="flex items-center gap-1.5">
                    <Mail className="h-3.5 w-3.5 text-primary" />
                    <span>{clinic.email}</span>
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-primary" />
                  <span>Timezone: {clinic.timezone}</span>
                </div>
              </div>

              {/* Description */}
              {clinic.description && (
                <div className="mt-4 rounded-2xl bg-muted/30 p-4 text-sm leading-relaxed text-muted-foreground">
                  <h2 className="text-xs font-bold uppercase tracking-wider text-foreground">Facility Overview</h2>
                  <p className="mt-1">{clinic.description}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Associated Doctors Section */}
        <div className="mt-10">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-foreground">
                Practicing Specialists ({doctors.length})
              </h2>
              <p className="text-sm text-muted-foreground">
                Verified doctors actively providing consultations at {clinic.name}.
              </p>
            </div>
          </div>

          {doctors.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center">
              <Users className="mx-auto h-12 w-12 text-muted-foreground/50" />
              <h4 className="mt-3 text-base font-bold text-foreground">No doctors currently listed</h4>
              <p className="mt-1 text-xs text-muted-foreground">
                This clinic has not yet onboarded active practitioners for public appointment booking.
              </p>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {doctors.map((doc) => (
                <Card
                  key={doc.doctor_clinic_id}
                  className="group flex flex-col justify-between overflow-hidden rounded-2xl transition duration-200 hover:border-primary/50 hover:shadow-md"
                >
                  <CardContent className="flex flex-1 flex-col p-6">
                    {/* Doctor Info */}
                    <div className="flex items-start space-x-3.5">
                      {doc.profile_photo ? (
                        <img
                          src={doc.profile_photo}
                          alt={doc.full_name}
                          className="h-14 w-14 rounded-2xl object-cover ring-1 ring-border"
                        />
                      ) : (
                        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500/20 to-blue-500/20 text-lg font-bold text-teal-700 dark:text-teal-400 ring-1 ring-teal-500/30">
                          {doc.full_name
                            .replace(/^Dr\.\s*/i, "")
                            .split(" ")
                            .map((n) => n[0])
                            .slice(0, 2)
                            .join("")}
                        </div>
                      )}

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <h3 className="font-bold text-foreground transition group-hover:text-primary">
                            {doc.full_name}
                          </h3>
                        </div>
                        <p className="text-xs font-semibold text-primary">{doc.specialization}</p>
                        <p className="truncate text-xs text-muted-foreground">{doc.qualifications}</p>
                      </div>
                    </div>

                    {/* Experience & Languages */}
                    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Briefcase className="h-3.5 w-3.5" />
                        {doc.years_of_experience} yrs exp
                      </span>
                      {doc.languages && (
                        <>
                          <span>•</span>
                          <span>{doc.languages}</span>
                        </>
                      )}
                    </div>

                    {/* Fees & Slot Duration */}
                    <div className="mt-4 rounded-xl bg-muted/30 p-3 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Consultation Fee:</span>
                        <span className="font-bold text-emerald-600 dark:text-emerald-400">
                          ₹{doc.consultation_fee}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-muted-foreground">
                        <span>Duration:</span>
                        <span>{doc.appointment_duration_minutes} mins</span>
                      </div>
                    </div>

                    {/* Action Button */}
                    <div className="mt-5 border-t border-border/70 pt-4">
                      <Link
                        to={`/doctors/${doc.doctor_id}?clinicId=${clinic.id}`}
                        className="block w-full"
                      >
                        <Button className="w-full gap-2 text-xs shadow-sm">
                          <CalendarCheck className="h-3.5 w-3.5" />
                          <span>Check Available Slots</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PublicClinicDetailPage;
