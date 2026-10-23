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
  Users,
  Search,
  CheckCircle2,
  AlertTriangle,
  Ban,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  Stethoscope,
  Building2,
} from "lucide-react";
import {
  useAdminActivateUser,
  useAdminDeactivateUser,
  useAdminSuspendUser,
  useAdminUsers,
  type AdminUser,
} from "@/features/admin";
import { useAuthStore } from "@/features/auth";

export function AdminUsersPage() {
  const { user: currentUser } = useAuthStore();
  const [roleFilter, setRoleFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  // Modals state
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [actionUser, setActionUser] = useState<AdminUser | null>(null);
  const [actionType, setActionType] = useState<"ACTIVATE" | "DEACTIVATE" | "SUSPEND" | null>(null);
  const [reason, setReason] = useState<string>("");

  const { data, isLoading, refetch } = useAdminUsers({
    role: roleFilter === "ALL" ? undefined : roleFilter,
    status: statusFilter === "ALL" ? undefined : statusFilter,
    search: search.trim() || undefined,
    page,
  });

  const activateMutation = useAdminActivateUser();
  const deactivateMutation = useAdminDeactivateUser();
  const suspendMutation = useAdminSuspendUser();

  const handleActionConfirm = async () => {
    if (!actionUser || !actionType) return;

    if (actionType === "ACTIVATE") {
      await activateMutation.mutateAsync(actionUser.id);
    } else if (actionType === "DEACTIVATE") {
      await deactivateMutation.mutateAsync(actionUser.id);
    } else if (actionType === "SUSPEND") {
      await suspendMutation.mutateAsync({ userId: actionUser.id, reason });
    }

    setActionUser(null);
    setActionType(null);
    setReason("");
    refetch();
  };

  const isPendingAction =
    activateMutation.isPending || deactivateMutation.isPending || suspendMutation.isPending;

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/admin" className="text-xs text-muted-foreground hover:underline">
              Dashboard
            </Link>
            <span className="text-xs text-muted-foreground">/</span>
            <span className="text-xs font-semibold text-foreground">Users</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2 mt-1">
            <Users className="h-6 w-6 text-purple-600" />
            User Account Management
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Monitor identities, roles, account statuses, and manage access restrictions.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card className="border-muted/80 shadow-sm">
        <CardContent className="pt-5">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="relative md:col-span-2">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, email, or phone..."
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
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="ALL">All Roles</option>
                <option value="PATIENT">Patient</option>
                <option value="DOCTOR">Doctor</option>
                <option value="CLINIC_OWNER">Clinic Owner</option>
                <option value="STAFF">Clinic Staff</option>
                <option value="SUPER_ADMIN">Super Admin</option>
              </select>
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
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
                <option value="SUSPENDED">Suspended</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card className="border-muted/80 shadow-sm overflow-hidden">
        <CardHeader className="py-3.5 px-6 border-b bg-muted/20">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold">
              Platform Users ({data?.count ?? 0})
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-20 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              <span className="text-xs">Loading user accounts...</span>
            </div>
          ) : data?.results && data.results.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-muted/40 text-muted-foreground font-semibold text-left">
                    <th className="py-3 px-4">User</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Account Status</th>
                    <th className="py-3 px-4">Verification</th>
                    <th className="py-3 px-4">Joined Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.results.map((u) => {
                    const isSelf = currentUser?.id === u.id;
                    return (
                      <tr key={u.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-foreground">{u.full_name}</div>
                          <div className="text-[11px] text-muted-foreground">{u.email}</div>
                          {u.phone && <div className="text-[10px] text-muted-foreground">{u.phone}</div>}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="outline" className="text-[10px] font-mono">
                            {u.role}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          {u.status === "ACTIVE" ? (
                            <Badge className="bg-emerald-500/10 text-emerald-700 border-emerald-500/20 text-[10px]">
                              Active
                            </Badge>
                          ) : u.status === "SUSPENDED" ? (
                            <Badge variant="destructive" className="text-[10px]">
                              Suspended
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[10px]">
                              Inactive
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {u.is_verified ? (
                            <span className="text-emerald-600 font-medium flex items-center gap-1">
                              <CheckCircle2 className="h-3 w-3" /> Verified
                            </span>
                          ) : (
                            <span className="text-amber-600 font-medium">Unverified</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {new Date(u.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedUser(u)}
                              className="h-7 px-2 text-xs"
                            >
                              <Eye className="h-3.5 w-3.5 mr-1" /> View
                            </Button>

                            {u.status !== "ACTIVE" && (
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={isSelf}
                                onClick={() => {
                                  setActionUser(u);
                                  setActionType("ACTIVATE");
                                }}
                                className="h-7 px-2 text-[11px] text-emerald-700 hover:text-emerald-800"
                              >
                                Activate
                              </Button>
                            )}

                            {u.status === "ACTIVE" && (
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={isSelf}
                                onClick={() => {
                                  setActionUser(u);
                                  setActionType("DEACTIVATE");
                                }}
                                className="h-7 px-2 text-[11px] text-amber-700 hover:text-amber-800"
                              >
                                Deactivate
                              </Button>
                            )}

                            {u.status !== "SUSPENDED" && (
                              <Button
                                variant="destructive"
                                size="sm"
                                disabled={isSelf}
                                onClick={() => {
                                  setActionUser(u);
                                  setActionType("SUSPEND");
                                }}
                                className="h-7 px-2 text-[11px]"
                              >
                                Suspend
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-16 text-center text-xs text-muted-foreground">
              No user accounts found matching your search and filter criteria.
            </div>
          )}

          {/* Pagination Controls */}
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

      {/* User Details Modal */}
      {selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-lg rounded-xl border shadow-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground">User Account Profile</h3>
                <p className="text-xs text-muted-foreground">Sanitized administrative record</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedUser(null)}
                className="h-7 w-7 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-muted-foreground">Full Name:</span>
                <p className="font-semibold text-foreground mt-0.5">{selectedUser.full_name}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Email:</span>
                <p className="font-semibold text-foreground mt-0.5">{selectedUser.email}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Phone:</span>
                <p className="font-semibold text-foreground mt-0.5">{selectedUser.phone || "—"}</p>
              </div>
              <div>
                <span className="text-muted-foreground">System Role:</span>
                <p className="font-semibold text-foreground mt-0.5">{selectedUser.role}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Status:</span>
                <p className="font-semibold text-foreground mt-0.5">{selectedUser.status}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Email Verified:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {selectedUser.is_verified ? "Yes" : "No"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Joined:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {new Date(selectedUser.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Last Login:</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {selectedUser.last_login ? new Date(selectedUser.last_login).toLocaleString() : "Never"}
                </p>
              </div>
            </div>

            {selectedUser.role === "DOCTOR" && (
              <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 p-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                  <Stethoscope className="h-4 w-4" />
                  <span>Has associated Doctor Practitioner profile</span>
                </div>
                {selectedUser.doctor_profile_id && (
                  <Link to={`/admin/doctors/${selectedUser.doctor_profile_id}`}>
                    <Button size="sm" variant="outline" className="h-7 text-[11px]">
                      View Credentials
                    </Button>
                  </Link>
                )}
              </div>
            )}

            {selectedUser.role === "CLINIC_OWNER" && (
              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                  <Building2 className="h-4 w-4" />
                  <span>Owns {selectedUser.owned_clinics_count} clinic facilities</span>
                </div>
                <Link to="/admin/clinics">
                  <Button size="sm" variant="outline" className="h-7 text-[11px]">
                    Inspect Clinics
                  </Button>
                </Link>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button size="sm" variant="outline" onClick={() => setSelectedUser(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Action Confirmation Modal */}
      {actionUser && actionType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-md rounded-xl border shadow-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div
                className={`h-10 w-10 rounded-full flex items-center justify-center ${
                  actionType === "SUSPEND"
                    ? "bg-destructive/10 text-destructive"
                    : actionType === "DEACTIVATE"
                    ? "bg-amber-500/10 text-amber-600"
                    : "bg-emerald-500/10 text-emerald-600"
                }`}
              >
                {actionType === "SUSPEND" ? (
                  <Ban className="h-5 w-5" />
                ) : actionType === "DEACTIVATE" ? (
                  <AlertTriangle className="h-5 w-5" />
                ) : (
                  <CheckCircle2 className="h-5 w-5" />
                )}
              </div>
              <div>
                <h3 className="font-bold text-base text-foreground">
                  Confirm {actionType.charAt(0) + actionType.slice(1).toLowerCase()} User
                </h3>
                <p className="text-xs text-muted-foreground">{actionUser.email}</p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Are you sure you want to {actionType.toLowerCase()} this account? This action takes
              effect immediately and will be logged in the immutable security audit trail.
            </p>

            {actionType === "SUSPEND" && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Suspension Reason (Mandatory):
                </label>
                <Input
                  placeholder="e.g. Terms violation, credential audit pending..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="text-xs"
                />
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActionUser(null);
                  setActionType(null);
                  setReason("");
                }}
                disabled={isPendingAction}
              >
                Cancel
              </Button>
              <Button
                variant={actionType === "SUSPEND" ? "destructive" : "default"}
                size="sm"
                onClick={handleActionConfirm}
                disabled={isPendingAction || (actionType === "SUSPEND" && !reason.trim())}
              >
                {isPendingAction && <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />}
                Confirm {actionType}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminUsersPage;
