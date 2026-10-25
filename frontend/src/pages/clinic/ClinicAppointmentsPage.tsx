import { useState } from "react";
import {
  CalendarDays,
  Search,
  Eye,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ClinicSwitcher,
  useActiveClinic,
  useClinicAppointments,
  useClinicAppointmentDetail,
  useConfirmClinicAppointment,
  useCompleteClinicAppointment,
  useMarkNoShowClinicAppointment,
} from "@/features/clinicOperations";
import {
  AppointmentCancelDialog,
  AppointmentRescheduleModal,
  ReportUnavailabilityModal,
} from "@/features/appointments";
import type { Appointment } from "@/features/appointments/types";

export function ClinicAppointmentsPage() {
  const { activeClinic, activeClinicId } = useActiveClinic();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [timeFilter, setTimeFilter] = useState<string>("all");
  const [requiresAttention, setRequiresAttention] = useState<boolean>(false);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  // Modal states
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<string | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [showRescheduleModal, setShowRescheduleModal] = useState(false);
  const [showUnavailModal, setShowUnavailModal] = useState(false);
  const [activeApptObject, setActiveApptObject] = useState<Appointment | null>(null);

  const queryParams = {
    search: search.trim() || undefined,
    status: statusFilter !== "ALL" ? statusFilter : undefined,
    filter: timeFilter !== "all" ? timeFilter : undefined,
    requires_attention: requiresAttention || undefined,
    from_date: fromDate || undefined,
    to_date: toDate || undefined,
  };

  const {
    data: appointmentsData,
    isLoading: isLoadingAppts,
    refetch,
  } = useClinicAppointments(activeClinicId, queryParams);

  const { data: detailData } = useClinicAppointmentDetail(
    activeClinicId,
    selectedAppointmentId || ""
  );

  const confirmMutation = useConfirmClinicAppointment(activeClinicId);
  const completeMutation = useCompleteClinicAppointment(activeClinicId);
  const noShowMutation = useMarkNoShowClinicAppointment(activeClinicId);

  const appointments: Appointment[] = appointmentsData?.results || [];

  const handleConfirm = async (id: string) => {
    try {
      await confirmMutation.mutateAsync(id);
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const handleComplete = async (id: string) => {
    if (confirm("Are you sure you want to mark this appointment as Completed?")) {
      try {
        await completeMutation.mutateAsync(id);
        refetch();
      } catch (err) {
        console.error(err);
      }
    }
  };

  const handleNoShow = async (id: string) => {
    if (confirm("Are you sure you want to mark this patient as No-Show?")) {
      try {
        await noShowMutation.mutateAsync(id);
        refetch();
      } catch (err) {
        console.error(err);
      }
    }
  };

  const openActionModal = (
    appt: Appointment,
    type: "detail" | "cancel" | "reschedule" | "unavail"
  ) => {
    setSelectedAppointmentId(appt.id);
    setActiveApptObject(appt);
    if (type === "detail") setShowDetailModal(true);
    if (type === "cancel") setShowCancelModal(true);
    if (type === "reschedule") setShowRescheduleModal(true);
    if (type === "unavail") setShowUnavailModal(true);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CONFIRMED":
        return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200">Confirmed</Badge>;
      case "COMPLETED":
        return <Badge className="bg-purple-100 text-purple-800 border-purple-200">Completed</Badge>;
      case "CANCELLED":
        return <Badge className="bg-rose-100 text-rose-800 border-rose-200">Cancelled</Badge>;
      case "NO_SHOW":
        return <Badge className="bg-gray-100 text-gray-800 border-gray-200">No Show</Badge>;
      case "RESCHEDULE_REQUIRED":
        return <Badge className="bg-amber-100 text-amber-800 border-amber-200">Reschedule Needed</Badge>;
      case "PENDING_CONFIRMATION":
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200">Pending</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between bg-card p-5 rounded-2xl border shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <CalendarDays className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Appointment Desk</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Monitor and manage consultation queue for {activeClinic?.name || "your clinic"}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <ClinicSwitcher />
          <Button size="sm" variant="outline" onClick={() => refetch()} className="gap-1 text-xs">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card>
        <CardContent className="p-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            {/* Search Input */}
            <div className="relative md:col-span-2">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search by booking reference, patient name, phone, or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border bg-background"
              />
            </div>

            {/* Status Select */}
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full py-1.5 px-2 text-xs rounded-lg border bg-background"
              >
                <option value="ALL">All Statuses</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="NO_SHOW">No Show</option>
                <option value="RESCHEDULE_REQUIRED">Reschedule Required</option>
                <option value="PENDING_CONFIRMATION">Pending Confirmation</option>
              </select>
            </div>

            {/* Time Filter */}
            <div>
              <select
                value={timeFilter}
                onChange={(e) => setTimeFilter(e.target.value)}
                className="w-full py-1.5 px-2 text-xs rounded-lg border bg-background"
              >
                <option value="all">All Dates</option>
                <option value="upcoming">Upcoming Only</option>
                <option value="past">Past Consultations</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t text-xs">
            <div className="flex items-center space-x-4">
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresAttention}
                  onChange={(e) => setRequiresAttention(e.target.checked)}
                  className="rounded text-primary h-3.5 w-3.5"
                />
                <span className="font-medium text-amber-900 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  ⚠️ Requiring Attention Only
                </span>
              </label>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-muted-foreground">Date interval:</span>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="h-7 text-xs rounded border bg-background px-2"
              />
              <span className="text-muted-foreground">to</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="h-7 text-xs rounded border bg-background px-2"
              />
              {(fromDate || toDate || search || statusFilter !== "ALL" || requiresAttention) && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setSearch("");
                    setStatusFilter("ALL");
                    setTimeFilter("all");
                    setRequiresAttention(false);
                    setFromDate("");
                    setToDate("");
                  }}
                  className="h-7 text-xs px-2 text-muted-foreground"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Appointment Table */}
      <Card>
        <CardHeader className="p-4 pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold">
              Appointments ({appointments.length})
            </CardTitle>
            <span className="text-xs text-muted-foreground font-mono">
              Operating Timezone: {activeClinic?.timezone}
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingAppts ? (
            <div className="p-12 text-center text-xs text-muted-foreground">
              Loading appointment queue...
            </div>
          ) : appointments.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <CalendarDays className="h-8 w-8 text-muted-foreground/60 mx-auto" />
              <p className="text-sm font-medium">No appointments match the criteria.</p>
              <p className="text-xs text-muted-foreground">
                Try clearing filters or adjusting your date range.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 border-y text-muted-foreground uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Booking Ref</th>
                    <th className="py-2.5 px-3">Patient</th>
                    <th className="py-2.5 px-3">Doctor</th>
                    <th className="py-2.5 px-3">Date & Time</th>
                    <th className="py-2.5 px-3">Fee / Payment</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {appointments.map((appt) => {
                    const startLocal = new Date(appt.start_at).toLocaleString("en-IN", {
                      timeZone: activeClinic?.timezone || "Asia/Kolkata",
                      dateStyle: "medium",
                      timeStyle: "short",
                    });

                    return (
                      <tr key={appt.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-2.5 px-3 font-mono font-semibold">
                          <div className="flex items-center space-x-1">
                            <span>{appt.booking_reference}</span>
                            {appt.reschedule_required && (
                              <span title="Action Required: Rescheduling Needed">⚠️</span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-foreground">
                            {appt.patient?.first_name} {appt.patient?.last_name}
                          </div>
                          <div className="text-[10px] text-muted-foreground">{appt.patient?.phone}</div>
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="font-medium">{appt.doctor?.full_name}</div>
                          <div className="text-[10px] text-muted-foreground">{appt.doctor?.specialization}</div>
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="font-medium">{startLocal}</div>
                          <div className="text-[10px] text-muted-foreground">{appt.duration_minutes || 15} mins</div>
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="font-medium">₹{appt.consultation_fee}</div>
                          <span className={`text-[10px] font-semibold ${appt.payment_status === "PAID" ? "text-emerald-600" : "text-amber-600"}`}>
                            {appt.payment_status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          {getStatusBadge(appt.status)}
                        </td>
                        <td className="py-2.5 px-3 text-right space-x-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openActionModal(appt, "detail")}
                            className="h-6 px-1.5 text-xs text-primary"
                            title="View Full Details"
                          >
                            <Eye className="h-3.5 w-3.5 mr-1" /> View
                          </Button>

                          {appt.status === "PENDING_CONFIRMATION" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleConfirm(appt.id)}
                              className="h-6 px-2 text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                            >
                              Confirm
                            </Button>
                          )}

                          {appt.status === "CONFIRMED" && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleComplete(appt.id)}
                                className="h-6 px-2 text-[10px] bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100"
                              >
                                Done
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleNoShow(appt.id)}
                                className="h-6 px-1.5 text-[10px] text-muted-foreground hover:text-foreground"
                              >
                                No-Show
                              </Button>
                            </>
                          )}

                          {appt.status !== "CANCELLED" && appt.status !== "COMPLETED" && (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openActionModal(appt, "reschedule")}
                                className="h-6 px-1.5 text-[10px] text-blue-600 hover:bg-blue-50"
                              >
                                Reschedule
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openActionModal(appt, "cancel")}
                                className="h-6 px-1.5 text-[10px] text-rose-600 hover:bg-rose-50"
                              >
                                Cancel
                              </Button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Appointment Detail Modal */}
      {showDetailModal && detailData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-2xl rounded-2xl border shadow-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b">
              <div>
                <h3 className="text-base font-bold text-foreground">
                  Appointment Details: {detailData.booking_reference}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Scheduled consultation overview and immutable audit history
                </p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowDetailModal(false)}
                className="h-8 w-8 p-0"
              >
                ✕
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 text-xs">
              <div className="p-3 rounded-lg bg-muted/40 space-y-1">
                <p className="font-semibold text-foreground">Patient Information</p>
                <p>{detailData.patient?.first_name} {detailData.patient?.last_name}</p>
                <p className="text-muted-foreground">{detailData.patient?.email}</p>
                <p className="text-muted-foreground">{detailData.patient?.phone}</p>
              </div>

              <div className="p-3 rounded-lg bg-muted/40 space-y-1">
                <p className="font-semibold text-foreground">Doctor Information</p>
                <p>{detailData.doctor?.full_name}</p>
                <p className="text-muted-foreground">{detailData.doctor?.specialization}</p>
                <p className="text-muted-foreground">Fee Snapshot: ₹{detailData.consultation_fee}</p>
              </div>
            </div>

            <div className="p-3 rounded-lg border text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Current Status:</span>
                <div>{getStatusBadge(detailData.status)}</div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Payment Status:</span>
                <span className="font-semibold text-emerald-600">{detailData.payment_status}</span>
              </div>
              {detailData.patient_note && (
                <div className="pt-2">
                  <span className="font-semibold">Patient Note:</span>
                  <p className="text-muted-foreground italic mt-0.5">{detailData.patient_note}</p>
                </div>
              )}
            </div>

            {/* Audit History Timeline */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Audit Trail & Event History
              </h4>
              {detailData.history && detailData.history.length > 0 ? (
                <div className="space-y-2 border rounded-lg p-3 max-h-48 overflow-y-auto">
                  {detailData.history.map((h: any) => (
                    <div key={h.id} className="text-xs border-b last:border-b-0 pb-1.5 last:pb-0">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-primary">{h.event_type}</span>
                        <span className="text-[10px] text-muted-foreground">{new Date(h.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-muted-foreground text-[11px]">{h.reason || "Action performed"}</p>
                      <p className="text-[10px] text-muted-foreground">By: {h.actor?.first_name || h.actor_role}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No historical events recorded.</p>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <Button size="sm" onClick={() => setShowDetailModal(false)}>Close</Button>
            </div>
          </div>
        </div>
      )}

      {/* Action Modals */}
      {showCancelModal && activeApptObject && (
        <AppointmentCancelDialog
          appointment={activeApptObject}
          isOpen={showCancelModal}
          onClose={() => {
            setShowCancelModal(false);
            setActiveApptObject(null);
            refetch();
          }}
          onSuccess={() => {
            setShowCancelModal(false);
            setActiveApptObject(null);
            refetch();
          }}
        />
      )}

      {showRescheduleModal && activeApptObject && (
        <AppointmentRescheduleModal
          appointment={activeApptObject}
          isOpen={showRescheduleModal}
          onClose={() => {
            setShowRescheduleModal(false);
            setActiveApptObject(null);
            refetch();
          }}
          onSuccess={() => {
            setShowRescheduleModal(false);
            setActiveApptObject(null);
            refetch();
          }}
        />
      )}

      {showUnavailModal && activeApptObject && (
        <ReportUnavailabilityModal
          appointment={activeApptObject}
          isOpen={showUnavailModal}
          clinicScope={true}
          onClose={() => {
            setShowUnavailModal(false);
            setActiveApptObject(null);
            refetch();
          }}
          onSuccess={() => {
            setShowUnavailModal(false);
            setActiveApptObject(null);
            refetch();
          }}
        />
      )}
    </div>
  );
}

export default ClinicAppointmentsPage;
