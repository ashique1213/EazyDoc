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
  ShieldCheck,
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  FileCode,
} from "lucide-react";
import { useAdminAuditLogs, type AdminAuditLog } from "@/features/admin";

export function AdminAuditLogsPage() {
  const [actionFilter, setActionFilter] = useState<string>("ALL");
  const [resourceFilter, setResourceFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  const [selectedLog, setSelectedLog] = useState<AdminAuditLog | null>(null);

  const { data, isLoading } = useAdminAuditLogs({
    action: actionFilter === "ALL" ? undefined : actionFilter,
    resource_type: resourceFilter === "ALL" ? undefined : resourceFilter,
    search: search.trim() || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
  });

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
            <span className="text-xs font-semibold text-foreground">Audit Trail</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2 mt-1">
            <ShieldCheck className="h-6 w-6 text-emerald-600" />
            Centralized Administrative Audit Logs
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Immutable security audit trail capturing verification transitions, account actions, and financial changes.
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
                placeholder="Search action, resource, actor..."
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
                value={actionFilter}
                onChange={(e) => {
                  setActionFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="ALL">All Event Actions</option>
                <option value="CLINIC_APPROVED">Clinic Approved</option>
                <option value="CLINIC_REJECTED">Clinic Rejected</option>
                <option value="CLINIC_SUSPENDED">Clinic Suspended</option>
                <option value="CLINIC_REACTIVATED">Clinic Reactivated</option>
                <option value="DOCTOR_VERIFIED">Doctor Verified</option>
                <option value="DOCTOR_SUSPENDED">Doctor Suspended</option>
                <option value="USER_ACTIVATED">User Activated</option>
                <option value="USER_DEACTIVATED">User Deactivated</option>
                <option value="USER_SUSPENDED">User Suspended</option>
                <option value="UPDATE_PLATFORM_COMMISSION_RATE">Update Default Commission</option>
                <option value="UPDATE_CLINIC_COMMISSION_RATE">Update Clinic Commission</option>
                <option value="ADMIN_CANCEL_APPOINTMENT">Admin Cancel Appointment</option>
              </select>
            </div>

            <div>
              <select
                value={resourceFilter}
                onChange={(e) => {
                  setResourceFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="ALL">All Target Resources</option>
                <option value="Clinic">Clinic</option>
                <option value="Doctor">Doctor</option>
                <option value="USER">User</option>
                <option value="APPOINTMENT">Appointment</option>
                <option value="PLATFORM_SETTING">Platform Setting</option>
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

      {/* Audit Logs Table */}
      <Card className="border-muted/80 shadow-sm overflow-hidden">
        <CardHeader className="py-3.5 px-6 border-b bg-muted/20">
          <CardTitle className="text-sm font-semibold">
            Audit Records ({data?.count ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-20 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              <span className="text-xs">Loading audit trail...</span>
            </div>
          ) : data?.results && data.results.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-muted/40 text-muted-foreground font-semibold text-left">
                    <th className="py-3 px-4">Event Action</th>
                    <th className="py-3 px-4">Resource Target</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">IP Address</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.results.map((log) => (
                    <tr key={log.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4">
                        <Badge
                          variant="outline"
                          className="font-mono text-[10px] bg-primary/5 text-primary border-primary/20"
                        >
                          {log.action}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground">{log.resource_type}</div>
                        <div className="text-[10px] font-mono text-muted-foreground truncate max-w-[120px]">
                          {log.resource_id || "—"}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-foreground">{log.actor_name}</div>
                        <div className="text-[10px] text-muted-foreground">{log.actor_email}</div>
                      </td>
                      <td className="py-3 px-4 font-mono text-muted-foreground text-[11px]">
                        {log.ip_address || "Internal"}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedLog(log)}
                          className="h-7 px-2 text-xs"
                        >
                          <Eye className="h-3.5 w-3.5 mr-1" /> View JSON
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-16 text-center text-xs text-muted-foreground">
              No audit logs found matching your filters.
            </div>
          )}

          {/* Pagination */}
          {data && data.count > 20 && (
            <div className="flex items-center justify-between p-4 border-t text-xs">
              <span className="text-muted-foreground">
                Showing page {page} of {Math.ceil(data.count / 20)}
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

      {/* JSON Payload Inspector Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-xl rounded-xl border shadow-xl overflow-hidden p-6 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground flex items-center gap-2">
                  <FileCode className="h-4 w-4 text-primary" />
                  Audit Event Details [{selectedLog.action}]
                </h3>
                <p className="text-xs text-muted-foreground">
                  Timestamp: {new Date(selectedLog.created_at).toLocaleString()}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedLog(null)}
                className="h-7 w-7 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-muted/20 p-3 rounded-lg border">
              <div>
                <span className="text-muted-foreground">Action:</span>
                <p className="font-mono font-semibold text-foreground">{selectedLog.action}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Target Resource:</span>
                <p className="font-mono font-semibold text-foreground">
                  {selectedLog.resource_type}: {selectedLog.resource_id}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Actor:</span>
                <p className="font-semibold text-foreground">
                  {selectedLog.actor_name} ({selectedLog.actor_email})
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Actor Role:</span>
                <p className="font-semibold text-foreground">{selectedLog.actor_role}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Client IP:</span>
                <p className="font-mono text-foreground">{selectedLog.ip_address || "Internal"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">User Agent:</span>
                <p className="text-foreground truncate" title={selectedLog.user_agent}>
                  {selectedLog.user_agent || "N/A"}
                </p>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1.5">
              <span className="text-xs font-semibold text-foreground">Sanitized Event Payload:</span>
              <pre className="p-3 bg-muted/60 rounded-lg text-[11px] font-mono text-foreground overflow-x-auto border">
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2 border-t">
              <Button size="sm" variant="outline" onClick={() => setSelectedLog(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminAuditLogsPage;
