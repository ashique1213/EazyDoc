import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Calendar,
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  History,
  Ban,
  X,
} from "lucide-react";
import {
  useAdminAppointmentHistory,
  useAdminAppointments,
  useAdminCancelAppointment,
  type AdminAppointment,
} from "@/features/admin";

export function AdminAppointmentsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  // Modals
  const [selectedAppointment, setSelectedAppointment] = useState<AdminAppointment | null>(null);
  const [historyAppointmentId, setHistoryAppointmentId] = useState<string | null>(null);
  const [cancelTarget, setCancelTarget] = useState<AdminAppointment | null>(null);
  const [cancelReason, setCancelReason] = useState<string>("");

  const { data, isLoading, refetch } = useAdminAppointments({
    status: statusFilter === "ALL" ? undefined : statusFilter,
    payment_status: paymentStatusFilter === "ALL" ? undefined : paymentStatusFilter,
    search: search.trim() || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
  });

  const { data: historyData, isLoading: isHistoryLoading } = useAdminAppointmentHistory(
    historyAppointmentId || ""
  );

  const cancelMutation = useAdminCancelAppointment();

  const handleCancelConfirm = async () => {
    if (!cancelTarget || !cancelReason.trim()) return;
    await cancelMutation.mutateAsync({
      appointmentId: cancelTarget.id,
      reason: cancelReason.trim(),
    });
    setCancelTarget(null);
    setCancelReason("");
    refetch();
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/admin" className="text-xs text-muted-foreground hover:underline">
              Dashboard
            </Link>
            <span className="text-xs text-muted-foreground">/</span>
            <span className="text-xs font-semibold text-foreground">Appointments</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2 mt-1">
            <Calendar className="h-6 w-6 text-indigo-600" />
            Platform Appointments Administration
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Monitor patient bookings, clinic schedules, cancellations, and state audit history.
          </p>
        </div>
      </div>

      {/* Filters Bar */}
      <Card className="border-muted/80 shadow-sm">
        <CardContent className="pt-5">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="relative lg:col-span-2">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search reference, patient, doctor, clinic..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-9 text-xs"
              />
            </div>

            <div>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="ALL">All Appointment Statuses</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="NO_SHOW">No Show</option>
                <option value="PENDING_CONFIRMATION">Pending</option>
              </select>
            </div>

            <div>
              <select
                value={paymentStatusFilter}
                onChange={(e) => {
                  setPaymentStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="ALL">All Payment Statuses</option>
                <option value="PAID">Paid</option>
                <option value="PENDING">Pending</option>
                <option value="FAILED">Failed</option>
                <option value="REFUNDED">Refunded</option>
              </select>
            </div>

            <div>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(1);
                }}
                className="text-xs h-9"
                title="Date From"
              />
            </div>

            <div>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPage(1);
                }}
                className="text-xs h-9"
                title="Date To"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Appointments List Table */}
      <Card className="border-muted/80 shadow-sm overflow-hidden">
        <CardHeader className="py-3.5 px-6 border-b bg-muted/20">
          <CardTitle className="text-sm font-semibold">
            Appointments Records ({data?.count ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-20 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              <span className="text-xs">Loading appointments...</span>
            </div>
          ) : data?.results && data.results.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-muted/40 text-muted-foreground font-semibold text-left">
                    <th className="py-3 px-4">Booking Ref</th>
                    <th className="py-3 px-4">Patient</th>
                    <th className="py-3 px-4">Doctor & Clinic</th>
                    <th className="py-3 px-4">Date & Slot</th>
                    <th className="py-3 px-4">Fee / Payment</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.results.map((appt) => (
                    <tr key={appt.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-semibold text-foreground">
                        {appt.booking_reference}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground">
                          {appt.patient
                            ? `${appt.patient.first_name} ${appt.patient.last_name}`
                            : "Patient"}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {appt.patient?.email}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-foreground">
                          {appt.doctor?.full_name || "Doctor"}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {appt.clinic?.name || "Clinic"}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium">
                          {new Date(appt.start_at).toLocaleDateString()}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {new Date(appt.start_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold">₹{appt.consultation_fee}</div>
                        <Badge
                          variant="outline"
                          className={`text-[9px] py-0 ${
                            appt.payment_status === "PAID"
                              ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/20"
                              : appt.payment_status === "FAILED"
                              ? "bg-destructive/10 text-destructive border-destructive/20"
                              : "text-amber-700"
                          }`}
                        >
                          {appt.payment_status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={
                            appt.status === "COMPLETED"
                              ? "default"
                              : appt.status === "CANCELLED"
                              ? "destructive"
                              : "secondary"
                          }
                          className="text-[10px]"
                        >
                          {appt.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedAppointment(appt)}
                            className="h-7 px-2 text-xs"
                            title="View details"
                          >
                            <Eye className="h-3.5 w-3.5 mr-1" /> View
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setHistoryAppointmentId(appt.id)}
                            className="h-7 px-2 text-xs"
                            title="Audit history"
                          >
                            <History className="h-3.5 w-3.5 mr-1" /> History
                          </Button>
                          {appt.status !== "CANCELLED" && appt.status !== "COMPLETED" && (
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => setCancelTarget(appt)}
                              className="h-7 px-2 text-[11px]"
                            >
                              <Ban className="h-3.5 w-3.5 mr-1" /> Cancel
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-16 text-center text-xs text-muted-foreground">
              No appointments found matching your filters.
            </div>
          )}

          {/* Pagination */}
          {data && data.count > 15 && (
            <div className="flex items-center justify-between p-4 border-t text-xs">
              <span className="text-muted-foreground">
                Showing page {page} of {Math.ceil(data.count / 15)}
              </span>
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="h-8"
                >
                  <ChevronLeft className="h-3.5 w-3.5 mr-1" /> Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!data.next}
                  onClick={() => setPage((p) => p + 1)}
                  className="h-8"
                >
                  Next <ChevronRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Appointment Detail Modal */}
      {selectedAppointment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-lg rounded-xl border shadow-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground">
                  Appointment Reference: {selectedAppointment.booking_reference}
                </h3>
                <p className="text-xs text-muted-foreground">Full booking inspection</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedAppointment(null)}
                className="h-7 w-7 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-muted-foreground">Patient Name:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {selectedAppointment.patient?.first_name} {selectedAppointment.patient?.last_name}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Patient Email:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {selectedAppointment.patient?.email}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Doctor:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {selectedAppointment.doctor?.full_name} ({selectedAppointment.doctor?.specialization})
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Clinic:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {selectedAppointment.clinic?.name} ({selectedAppointment.clinic?.city})
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Start Time:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {new Date(selectedAppointment.start_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">End Time:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {new Date(selectedAppointment.end_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Consultation Fee:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  ₹{selectedAppointment.consultation_fee}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Payment Status:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {selectedAppointment.payment_status}
                </p>
              </div>
            </div>

            {selectedAppointment.cancellation_reason && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-xs">
                <span className="font-semibold text-destructive">Cancellation Reason:</span>
                <p className="text-foreground mt-0.5">{selectedAppointment.cancellation_reason}</p>
                {selectedAppointment.cancelled_at && (
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Cancelled at: {new Date(selectedAppointment.cancelled_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button size="sm" variant="outline" onClick={() => setSelectedAppointment(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Audit History Modal */}
      {historyAppointmentId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-xl rounded-xl border shadow-xl overflow-hidden p-6 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground flex items-center gap-2">
                  <History className="h-4 w-4 text-primary" />
                  Appointment Audit & State History
                </h3>
                <p className="text-xs text-muted-foreground">
                  Chronological trail of status transitions and changes
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setHistoryAppointmentId(null)}
                className="h-7 w-7 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
              {isHistoryLoading ? (
                <div className="py-12 flex justify-center text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading history...
                </div>
              ) : historyData && historyData.length > 0 ? (
                historyData.map((h) => (
                  <div key={h.id} className="p-3 rounded-lg border bg-muted/20 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="text-[10px] font-mono">
                        {h.event_type}
                      </Badge>
                      <span className="text-[11px] text-muted-foreground">
                        {new Date(h.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-foreground">
                      <span className="font-semibold">{h.actor_email}</span> ({h.actor_role})
                    </div>
                    {h.previous_status && h.new_status && (
                      <div className="text-muted-foreground text-[11px]">
                        Status: <span className="font-mono">{h.previous_status}</span> ➔{" "}
                        <span className="font-mono font-semibold text-foreground">
                          {h.new_status}
                        </span>
                      </div>
                    )}
                    {h.reason && (
                      <div className="text-xs bg-card p-2 rounded border mt-1">
                        <span className="font-semibold text-foreground">Note: </span>
                        {h.reason}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-muted-foreground">
                  No historical entries recorded for this appointment.
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t">
              <Button size="sm" variant="outline" onClick={() => setHistoryAppointmentId(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Administrative Cancellation Modal */}
      {cancelTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-md rounded-xl border shadow-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
                <Ban className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-foreground">
                  Cancel Appointment Administratively
                </h3>
                <p className="text-xs text-muted-foreground">
                  Ref: {cancelTarget.booking_reference}
                </p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              This action will mark the appointment as CANCELLED, free doctor availability, and
              record your administrative identity and reason in the audit trail.
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Mandatory Reason for Cancellation:
              </label>
              <Input
                placeholder="e.g. Clinic operational emergency, patient safety exception..."
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                className="text-xs"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setCancelTarget(null);
                  setCancelReason("");
                }}
                disabled={cancelMutation.isPending}
              >
                Close
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleCancelConfirm}
                disabled={cancelMutation.isPending || cancelReason.trim().length < 5}
              >
                {cancelMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                )}
                Confirm Cancellation
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminAppointmentsPage;
