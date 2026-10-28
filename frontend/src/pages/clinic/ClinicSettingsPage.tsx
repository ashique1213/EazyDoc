import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Building2,
  Settings,
  CalendarX,
  AlertTriangle,
  CheckCircle2,
  Save,
  Plus,
  Trash2,
  ArrowLeft,
  AlertOctagon,
  Shield,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ClinicSwitcher,
  useActiveClinic,
  useClinicManagementProfile,
  useUpdateClinicManagementProfile,
  useClinicClosures,
  usePreviewClinicClosure,
  useCreateClinicClosure,
  useDeleteClinicClosure,
} from "@/features/clinicOperations";
import type { ClinicClosurePreviewResponse } from "@/features/clinicOperations/types";

const TIMEZONES = [
  "Asia/Kolkata",
  "UTC",
  "Asia/Dubai",
  "Asia/Singapore",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
];

export function ClinicSettingsPage() {
  const { activeClinic, activeClinicId, isLoading: isLoadingClinic } = useActiveClinic();

  // Queries
  const {
    data: clinicProfile,
    refetch: refetchProfile,
  } = useClinicManagementProfile(activeClinicId);

  const {
    data: closures = [],
    isLoading: isLoadingClosures,
    refetch: refetchClosures,
  } = useClinicClosures(activeClinicId);

  // Mutations
  const updateProfileMutation = useUpdateClinicManagementProfile(activeClinicId);
  const previewClosureMutation = usePreviewClinicClosure(activeClinicId);
  const createClosureMutation = useCreateClinicClosure(activeClinicId);
  const deleteClosureMutation = useDeleteClinicClosure(activeClinicId);

  // Profile Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [pincode, setPincode] = useState("");
  const [country, setCountry] = useState("India");
  const [timezone, setTimezone] = useState("Asia/Kolkata");

  const [profileSuccessMsg, setProfileSuccessMsg] = useState<string | null>(null);
  const [profileErrorMsg, setProfileErrorMsg] = useState<string | null>(null);

  // Sync profile data to form
  useEffect(() => {
    if (clinicProfile) {
      setName(clinicProfile.name || "");
      setDescription(clinicProfile.description || "");
      setEmail(clinicProfile.email || "");
      setPhone(clinicProfile.phone || "");
      setAddressLine1(clinicProfile.address_line_1 || "");
      setAddressLine2(clinicProfile.address_line_2 || "");
      setCity(clinicProfile.city || "");
      setState(clinicProfile.state || "");
      setPincode(clinicProfile.pincode || "");
      setCountry(clinicProfile.country || "India");
      setTimezone(clinicProfile.timezone || "Asia/Kolkata");
    }
  }, [clinicProfile]);

  // Closures state
  const [isClosureModalOpen, setIsClosureModalOpen] = useState(false);
  const [closureStartDate, setClosureStartDate] = useState("");
  const [closureEndDate, setClosureEndDate] = useState("");
  const [closureReason, setClosureReason] = useState("Public Holiday");
  const [closureNotes, setClosureNotes] = useState("");
  const [closurePreview, setClosurePreview] = useState<ClinicClosurePreviewResponse | null>(null);
  const [closureError, setClosureError] = useState<string | null>(null);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileSuccessMsg(null);
    setProfileErrorMsg(null);

    try {
      await updateProfileMutation.mutateAsync({
        name: name.trim(),
        description: description.trim(),
        email: email.trim(),
        phone: phone.trim(),
        address_line_1: addressLine1.trim(),
        address_line_2: addressLine2.trim(),
        city: city.trim(),
        state: state.trim(),
        pincode: pincode.trim(),
        country: country.trim(),
        timezone,
      });
      setProfileSuccessMsg("Clinic profile settings saved successfully.");
      refetchProfile();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; message?: string } } };
      setProfileErrorMsg(
        error.response?.data?.detail ||
          error.response?.data?.message ||
          "Failed to update clinic settings. Please review form entries."
      );
    }
  };

  const handleOpenClosureModal = () => {
    const today = new Date().toISOString().split("T")[0];
    setClosureStartDate(today);
    setClosureEndDate(today);
    setClosureReason("Public Holiday");
    setClosureNotes("");
    setClosurePreview(null);
    setClosureError(null);
    setIsClosureModalOpen(true);
  };

  const handlePreviewClosure = async () => {
    if (!closureStartDate || !closureEndDate) {
      setClosureError("Please select both start date and end date.");
      return;
    }
    setClosureError(null);
    try {
      const res = await previewClosureMutation.mutateAsync({
        start_date: closureStartDate,
        end_date: closureEndDate,
        reason: closureReason,
      });
      setClosurePreview(res);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setClosureError(error.response?.data?.detail || "Failed to inspect affected appointments.");
    }
  };

  const handleConfirmCreateClosure = async () => {
    setClosureError(null);
    try {
      await createClosureMutation.mutateAsync({
        start_date: closureStartDate,
        end_date: closureEndDate,
        reason: closureReason,
        notes: closureNotes,
        confirmed: true,
      });
      setIsClosureModalOpen(false);
      refetchClosures();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setClosureError(error.response?.data?.detail || "Failed to record closure.");
    }
  };

  const handleDeleteClosure = async (closureId: string) => {
    if (!confirm("Are you sure you want to delete this closure record and reopen clinic availability?")) {
      return;
    }
    try {
      await deleteClosureMutation.mutateAsync(closureId);
      refetchClosures();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      alert(error.response?.data?.detail || "Failed to remove closure.");
    }
  };

  if (isLoadingClinic) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!activeClinic) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Clinic Settings</h1>
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            No clinic selected or you do not have permission to manage this clinic.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              to="/clinic/dashboard"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              <ArrowLeft className="h-3 w-3" /> Dashboard
            </Link>
            <span className="text-xs text-muted-foreground">/</span>
            <span className="text-xs font-medium text-foreground">Clinic Profile & Operations</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Settings className="h-6 w-6 text-primary" />
              Clinic Settings & Operational Controls
            </h1>
            <Badge variant="outline" className="capitalize">
              {activeClinic.status.toLowerCase()}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Configure contact details, address, operational timezone, and schedule closure periods for{" "}
            <span className="font-semibold text-foreground">{activeClinic.name}</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <ClinicSwitcher />
        </div>
      </div>

      {/* Security & Verification Status Banner */}
      <Card className="border-border bg-muted/30">
        <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <Shield className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-foreground">
                Platform Verification Status:{" "}
                <span className={activeClinic.is_verified ? "text-emerald-600 font-bold" : "text-amber-600 font-bold"}>
                  {activeClinic.is_verified ? "Verified Official Clinic" : "Pending Official Verification"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Approval and verification statuses are strictly managed by Super Administrators. Clinic owners cannot self-approve or modify platform commission rates.
              </p>
            </div>
          </div>
          <Badge variant={activeClinic.status === "APPROVED" ? "default" : "secondary"}>
            Status: {activeClinic.status}
          </Badge>
        </CardContent>
      </Card>

      {/* Profile Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" />
            Clinic Public Profile
          </CardTitle>
          <CardDescription>
            Public details displayed to patients during appointment booking and doctor discovery.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleProfileSubmit} className="space-y-4">
            {profileSuccessMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm rounded flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                {profileSuccessMsg}
              </div>
            )}
            {profileErrorMsg && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
                {profileErrorMsg}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-foreground">Clinic Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground">Operational Timezone *</label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Used for doctor schedules, appointment slots, and date reporting.
                </p>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground">Public Description</label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                placeholder="Overview of specialties, facilities, and patient services..."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-foreground">Contact Email *</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">Phone Number *</label>
                <input
                  type="text"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                  placeholder="+91..."
                />
              </div>
            </div>

            <div className="pt-2">
              <label className="text-xs font-semibold text-foreground block mb-1">Clinic Address</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <input
                    type="text"
                    required
                    placeholder="Address Line 1 *"
                    value={addressLine1}
                    onChange={(e) => setAddressLine1(e.target.value)}
                    className="w-full px-3 py-2 text-sm border rounded-md bg-background"
                  />
                </div>
                <div>
                  <input
                    type="text"
                    placeholder="Address Line 2 (Optional)"
                    value={addressLine2}
                    onChange={(e) => setAddressLine2(e.target.value)}
                    className="w-full px-3 py-2 text-sm border rounded-md bg-background"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="text-xs font-semibold text-foreground">City *</label>
                <input
                  type="text"
                  required
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">State *</label>
                <input
                  type="text"
                  required
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">Postal Code *</label>
                <input
                  type="text"
                  required
                  value={pincode}
                  onChange={(e) => setPincode(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">Country</label>
                <input
                  type="text"
                  required
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={updateProfileMutation.isPending} className="flex items-center gap-2">
                <Save className="h-4 w-4" />
                {updateProfileMutation.isPending ? "Saving..." : "Save Profile Settings"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Clinic Closures & Operational Unavailability (Section 11) */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <CalendarX className="h-4 w-4 text-primary" />
                Clinic Closures & Unavailability
              </CardTitle>
              <CardDescription>
                Schedule facility closures (public holidays, emergency maintenance, renovations). Previews affected appointments before recording.
              </CardDescription>
            </div>
            <Button onClick={handleOpenClosureModal} variant="outline" size="sm" className="flex items-center gap-1">
              <Plus className="h-4 w-4" /> Add Clinic Closure
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoadingClosures ? (
            <div className="p-8 text-center text-muted-foreground">Loading closures...</div>
          ) : closures.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No closures or holiday periods currently scheduled for this clinic.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Dates</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {closures.map((closure) => (
                  <TableRow key={closure.id}>
                    <TableCell className="font-medium text-xs">
                      {closure.start_date === closure.end_date ? (
                        <span>{closure.start_date}</span>
                      ) : (
                        <span>
                          {closure.start_date} to {closure.end_date}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {closure.reason}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
                      {closure.notes || "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {closure.created_by_name}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClosure(closure.id)}
                        className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                        title="Delete Closure"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add Closure & Impact Preview Modal */}
      {isClosureModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="relative w-full max-w-xl rounded-2xl bg-card border shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b">
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <CalendarX className="h-5 w-5 text-primary" />
                  Schedule Clinic Closure
                </h3>
                <p className="text-xs text-muted-foreground">
                  Record dates when the clinic will be completely closed for consultations.
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setIsClosureModalOpen(false)} className="h-8 w-8 p-0">
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-4 py-2">
              {closureError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
                  {closureError}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-foreground">Start Date *</label>
                  <input
                    type="date"
                    required
                    value={closureStartDate}
                    onChange={(e) => {
                      setClosureStartDate(e.target.value);
                      setClosurePreview(null);
                    }}
                    className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground">End Date *</label>
                  <input
                    type="date"
                    required
                    value={closureEndDate}
                    onChange={(e) => {
                      setClosureEndDate(e.target.value);
                      setClosurePreview(null);
                    }}
                    className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground">Reason for Closure *</label>
                <select
                  value={closureReason}
                  onChange={(e) => setClosureReason(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                >
                  <option value="Public Holiday">Public Holiday</option>
                  <option value="Emergency Maintenance">Emergency Maintenance</option>
                  <option value="Facility Renovation">Facility Renovation</option>
                  <option value="Annual Closure">Annual Clinic Recess</option>
                  <option value="Other">Other Unscheduled Closure</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground">Internal Notes / Instructions</label>
                <textarea
                  rows={2}
                  value={closureNotes}
                  onChange={(e) => setClosureNotes(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background"
                  placeholder="Optional notes for staff and audit record..."
                />
              </div>

              {/* Affected Appointments Check / Preview */}
              <div className="border rounded-lg p-3 bg-muted/20 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-foreground">
                      Appointment Conflict Verification
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Check if any patient bookings exist during these closure dates.
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handlePreviewClosure}
                    disabled={previewClosureMutation.isPending}
                  >
                    {previewClosureMutation.isPending ? "Checking..." : "Inspect Affected Bookings"}
                  </Button>
                </div>

                {closurePreview && (
                  <div className="space-y-2 pt-2 border-t">
                    {closurePreview.affected_count > 0 ? (
                      <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs space-y-2">
                        <div className="flex items-center gap-1.5 font-semibold text-amber-900">
                          <AlertOctagon className="h-4 w-4 text-amber-600" />
                          {closurePreview.affected_count} Existing Appointment(s) Affected!
                        </div>
                        <p className="text-amber-800">
                          Recording this closure will flag these appointments as requiring administrative attention. They will need to be rescheduled or cancelled through the appointment desk.
                        </p>
                        <div className="max-h-36 overflow-y-auto space-y-1 mt-1">
                          {closurePreview.affected_appointments.map((app) => (
                            <div
                              key={app.id}
                              className="p-1.5 bg-white/80 dark:bg-black/20 rounded border flex justify-between items-center text-[11px]"
                            >
                              <span className="font-mono font-medium">{app.booking_reference}</span>
                              <span>{app.patient_name} with Dr. {app.doctor_name}</span>
                              <Badge variant="outline" className="text-[10px]">{app.status}</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-800 flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        Zero conflicting patient appointments found during this period.
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setIsClosureModalOpen(false)}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleConfirmCreateClosure}
                  disabled={createClosureMutation.isPending}
                  className={closurePreview && closurePreview.affected_count > 0 ? "bg-amber-600 hover:bg-amber-700" : ""}
                >
                  {createClosureMutation.isPending
                    ? "Saving Closure..."
                    : closurePreview && closurePreview.affected_count > 0
                    ? "Confirm & Record Closure"
                    : "Record Closure"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
