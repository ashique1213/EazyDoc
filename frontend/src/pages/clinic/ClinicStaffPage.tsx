import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Users,
  UserPlus,
  Shield,
  Edit2,
  Trash2,
  AlertTriangle,
  ArrowLeft,
  Mail,
  UserCheck,
  UserX,
  Info,
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
  useClinicStaff,
  useCreateClinicStaff,
  useUpdateClinicStaff,
  useDeleteClinicStaff,
} from "@/features/clinicOperations";
import type {
  ClinicStaffMember,
  ClinicStaffPermission,
  ClinicStaffCreatePayload,
} from "@/features/clinicOperations/types";

const ALL_PERMISSIONS: { key: ClinicStaffPermission; label: string; description: string }[] = [
  {
    key: "VIEW_APPOINTMENTS",
    label: "View Appointments",
    description: "View booked, completed, and cancelled clinic appointments",
  },
  {
    key: "MANAGE_APPOINTMENTS",
    label: "Manage Appointments",
    description: "Confirm, complete, mark no-show, reschedule, or cancel appointments",
  },
  {
    key: "VIEW_DOCTORS",
    label: "View Doctors",
    description: "Browse associated doctors and view their schedules",
  },
  {
    key: "MANAGE_DOCTOR_ASSOCIATIONS",
    label: "Manage Doctor Associations",
    description: "Invite verified doctors, adjust consultation fees, or remove associations",
  },
  {
    key: "MANAGE_SCHEDULES",
    label: "Manage Schedules",
    description: "Configure clinic working hours and manage doctor availability shifts",
  },
  {
    key: "VIEW_FINANCIAL_SUMMARY",
    label: "View Financial Summary",
    description: "Access gross revenues, commission breakdowns, and clinic share reports",
  },
  {
    key: "MANAGE_CLINIC_PROFILE",
    label: "Manage Clinic Profile",
    description: "Update clinic contact info, address, operating hours, and closures",
  },
  {
    key: "MANAGE_STAFF",
    label: "Manage Staff",
    description: "Invite, update permissions, or revoke staff members",
  },
];

export function ClinicStaffPage() {
  const { activeClinic, activeClinicId, isLoading: isLoadingClinic } = useActiveClinic();
  const { data: staffList = [], isLoading: isLoadingStaff, refetch } = useClinicStaff(activeClinicId);

  const createStaffMutation = useCreateClinicStaff(activeClinicId);
  const updateStaffMutation = useUpdateClinicStaff(activeClinicId);
  const deleteStaffMutation = useDeleteClinicStaff(activeClinicId);

  // Modal states
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState<ClinicStaffMember | null>(null);
  const [deletingStaff, setDeletingStaff] = useState<ClinicStaffMember | null>(null);

  // Form states for Add
  const [newEmail, setNewEmail] = useState("");
  const [newFirstName, setNewFirstName] = useState("");
  const [newLastName, setNewLastName] = useState("");
  const [newRoleTitle, setNewRoleTitle] = useState("Receptionist");
  const [newPassword, setNewPassword] = useState("");
  const [newPermissions, setNewPermissions] = useState<ClinicStaffPermission[]>([
    "VIEW_APPOINTMENTS",
    "MANAGE_APPOINTMENTS",
  ]);
  const [formError, setFormError] = useState<string | null>(null);

  // Form states for Edit
  const [editRoleTitle, setEditRoleTitle] = useState("");
  const [editPermissions, setEditPermissions] = useState<ClinicStaffPermission[]>([]);
  const [editIsActive, setEditIsActive] = useState(true);

  const handleOpenAdd = () => {
    setNewEmail("");
    setNewFirstName("");
    setNewLastName("");
    setNewRoleTitle("Receptionist");
    setNewPassword("");
    setNewPermissions(["VIEW_APPOINTMENTS", "MANAGE_APPOINTMENTS"]);
    setFormError(null);
    setIsAddOpen(true);
  };

  const handleOpenEdit = (staff: ClinicStaffMember) => {
    setEditingStaff(staff);
    setEditRoleTitle(staff.role_title || "");
    setEditPermissions([...staff.permissions]);
    setEditIsActive(staff.is_active);
    setFormError(null);
  };

  const toggleNewPermission = (perm: ClinicStaffPermission) => {
    if (newPermissions.includes(perm)) {
      setNewPermissions(newPermissions.filter((p) => p !== perm));
    } else {
      setNewPermissions([...newPermissions, perm]);
    }
  };

  const toggleEditPermission = (perm: ClinicStaffPermission) => {
    if (editPermissions.includes(perm)) {
      setEditPermissions(editPermissions.filter((p) => p !== perm));
    } else {
      setEditPermissions([...editPermissions, perm]);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!newEmail || !newFirstName || !newLastName) {
      setFormError("Please fill out all required fields.");
      return;
    }

    try {
      const payload: ClinicStaffCreatePayload = {
        email: newEmail.trim(),
        first_name: newFirstName.trim(),
        last_name: newLastName.trim(),
        role_title: newRoleTitle.trim(),
        permissions: newPermissions,
        password: newPassword.trim() || undefined,
      };
      await createStaffMutation.mutateAsync(payload);
      setIsAddOpen(false);
      refetch();
    } catch (err: unknown) {
      const errorMsg = (err as { response?: { data?: { detail?: string; message?: string } } })?.response?.data;
      setFormError(errorMsg?.detail || errorMsg?.message || "Failed to create staff member.");
    }
  };

  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStaff) return;
    setFormError(null);

    try {
      await updateStaffMutation.mutateAsync({
        staffId: editingStaff.id,
        payload: {
          role_title: editRoleTitle.trim(),
          permissions: editPermissions,
          is_active: editIsActive,
        },
      });
      setEditingStaff(null);
      refetch();
    } catch (err: unknown) {
      const errorMsg = (err as { response?: { data?: { detail?: string; message?: string } } })?.response?.data;
      setFormError(errorMsg?.detail || errorMsg?.message || "Failed to update staff member.");
    }
  };

  const handleDeleteSubmit = async () => {
    if (!deletingStaff) return;
    try {
      await deleteStaffMutation.mutateAsync(deletingStaff.id);
      setDeletingStaff(null);
      refetch();
    } catch (err: unknown) {
      const errorMsg = (err as { response?: { data?: { detail?: string; message?: string } } })?.response?.data;
      alert(errorMsg?.detail || "Failed to revoke staff access.");
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
        <h1 className="text-2xl font-bold tracking-tight">Clinic Staff</h1>
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            No clinic selected or you do not have permission to manage clinics.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
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
            <span className="text-xs font-medium text-foreground">Staff & Permissions</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Users className="h-6 w-6 text-primary" />
              Clinic Staff Management
            </h1>
            <Badge variant="outline">{staffList.length} Staff Member{staffList.length === 1 ? "" : "s"}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Manage authorized staff accounts, role designations, and operational privileges for{" "}
            <span className="font-semibold text-foreground">{activeClinic.name}</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <ClinicSwitcher />
          <Button onClick={handleOpenAdd} className="flex items-center gap-2">
            <UserPlus className="h-4 w-4" />
            Add Staff Member
          </Button>
        </div>
      </div>

      {/* Info notice about scoping & security */}
      <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-900/50">
        <CardContent className="p-4 flex items-start gap-3">
          <Info className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-300 space-y-1">
            <p className="font-semibold">Security & Access Control Enforcement</p>
            <p className="text-xs text-blue-800 dark:text-blue-400">
              Staff permissions are strictly scoped to this clinic. Staff accounts cannot escalate their own privileges, cannot access Super Admin functionality, cannot change global doctor verification statuses, and cannot alter platform commission settings. All permission modifications take effect immediately.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Staff Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            Authorized Personnel
          </CardTitle>
          <CardDescription>
            List of users with explicit role-based permissions to operate this clinic desk.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingStaff ? (
            <div className="p-8 text-center text-muted-foreground">Loading staff list...</div>
          ) : staffList.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Users className="h-10 w-10 text-muted-foreground mx-auto opacity-50" />
              <p className="font-semibold text-foreground">No Staff Members Added Yet</p>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                Invite receptionists, appointment managers, and clinic coordinators to help operate daily bookings.
              </p>
              <Button onClick={handleOpenAdd} variant="outline" size="sm" className="mt-2">
                <UserPlus className="h-4 w-4 mr-1" /> Add First Staff Member
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Staff Member</TableHead>
                  <TableHead>Role Title</TableHead>
                  <TableHead>Granted Permissions</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {staffList.map((staff) => (
                  <TableRow key={staff.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-foreground">{staff.user.full_name}</div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <Mail className="h-3 w-3" /> {staff.user.email}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="font-normal">
                        {staff.role_title || "Staff"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1 max-w-md">
                        {staff.permissions.map((perm) => (
                          <Badge key={perm} variant="outline" className="text-[10px] px-1.5 py-0 font-mono">
                            {perm.replace(/_/g, " ")}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      {staff.is_active ? (
                        <Badge variant="default" className="bg-emerald-600 hover:bg-emerald-700 text-xs flex items-center gap-1 w-fit">
                          <UserCheck className="h-3 w-3" /> Active
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="text-xs flex items-center gap-1 w-fit">
                          <UserX className="h-3 w-3" /> Inactive
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEdit(staff)}
                          className="h-8 w-8 p-0"
                          title="Edit Permissions"
                        >
                          <Edit2 className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeletingStaff(staff)}
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                          title="Revoke Access"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add Staff Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="relative w-full max-w-2xl rounded-2xl bg-card border shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b">
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <UserPlus className="h-5 w-5 text-primary" />
                  Add Clinic Staff Member
                </h3>
                <p className="text-xs text-muted-foreground">
                  Assign a staff member and grant explicit, clinic-scoped permissions.
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setIsAddOpen(false)} className="h-8 w-8 p-0">
                <X className="h-4 w-4" />
              </Button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-4 py-2">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-foreground">First Name *</label>
                  <input
                    type="text"
                    required
                    value={newFirstName}
                    onChange={(e) => setNewFirstName(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                    placeholder="e.g. Sarah"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground">Last Name *</label>
                  <input
                    type="text"
                    required
                    value={newLastName}
                    onChange={(e) => setNewLastName(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                    placeholder="e.g. Jenkins"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-foreground">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                    placeholder="staff@example.com"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground">Role Title</label>
                  <input
                    type="text"
                    value={newRoleTitle}
                    onChange={(e) => setNewRoleTitle(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                    placeholder="e.g. Front Desk Officer"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground">Initial Password (Optional)</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                  placeholder="Leave blank to auto-generate temporary credentials"
                />
                <p className="text-[11px] text-muted-foreground mt-1">
                  If the user already exists in the system, they will be attached with staff privileges.
                </p>
              </div>

              {/* Permission Checkboxes */}
              <div className="pt-2">
                <label className="text-xs font-semibold text-foreground block mb-2">
                  Operational Privileges ({newPermissions.length} selected)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 border rounded-lg p-3 bg-muted/20">
                  {ALL_PERMISSIONS.map((perm) => {
                    const checked = newPermissions.includes(perm.key);
                    return (
                      <div
                        key={perm.key}
                        onClick={() => toggleNewPermission(perm.key)}
                        className={`flex items-start gap-2 p-2 rounded cursor-pointer border text-xs transition-colors ${
                          checked
                            ? "bg-primary/10 border-primary/40 text-foreground font-medium"
                            : "bg-background border-border text-muted-foreground hover:bg-muted/50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {}}
                          className="mt-0.5 pointer-events-none"
                        />
                        <div>
                          <div>{perm.label}</div>
                          <div className="text-[10px] text-muted-foreground leading-tight">{perm.description}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setIsAddOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createStaffMutation.isPending}>
                  {createStaffMutation.isPending ? "Creating..." : "Add Staff Member"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Staff Modal */}
      {editingStaff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="relative w-full max-w-2xl rounded-2xl bg-card border shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b">
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <Edit2 className="h-5 w-5 text-primary" />
                  Edit Staff Privileges: {editingStaff.user.full_name}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Update operational permissions for {editingStaff.user.email}.
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setEditingStaff(null)} className="h-8 w-8 p-0">
                <X className="h-4 w-4" />
              </Button>
            </div>

            <form onSubmit={handleUpdateSubmit} className="space-y-4 py-2">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
                  {formError}
                </div>
              )}

              <div>
                <label className="text-xs font-semibold text-foreground">Role Title</label>
                <input
                  type="text"
                  value={editRoleTitle}
                  onChange={(e) => setEditRoleTitle(e.target.value)}
                  className="w-full mt-1 px-3 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="editIsActive"
                  checked={editIsActive}
                  onChange={(e) => setEditIsActive(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <label htmlFor="editIsActive" className="text-sm font-medium text-foreground cursor-pointer">
                  Account Active (Unchecking disables staff access immediately)
                </label>
              </div>

              <div className="pt-2">
                <label className="text-xs font-semibold text-foreground block mb-2">
                  Granted Privileges ({editPermissions.length} selected)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 border rounded-lg p-3 bg-muted/20">
                  {ALL_PERMISSIONS.map((perm) => {
                    const checked = editPermissions.includes(perm.key);
                    return (
                      <div
                        key={perm.key}
                        onClick={() => toggleEditPermission(perm.key)}
                        className={`flex items-start gap-2 p-2 rounded cursor-pointer border text-xs transition-colors ${
                          checked
                            ? "bg-primary/10 border-primary/40 text-foreground font-medium"
                            : "bg-background border-border text-muted-foreground hover:bg-muted/50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {}}
                          className="mt-0.5 pointer-events-none"
                        />
                        <div>
                          <div>{perm.label}</div>
                          <div className="text-[10px] text-muted-foreground leading-tight">{perm.description}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setEditingStaff(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateStaffMutation.isPending}>
                  {updateStaffMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete/Revoke Staff Modal */}
      {deletingStaff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="relative w-full max-w-md rounded-2xl bg-card border shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              <h3 className="text-base font-bold">Revoke Staff Access</h3>
            </div>
            <p className="text-sm text-foreground">
              Are you sure you want to revoke clinic staff access for{" "}
              <strong>{deletingStaff.user.full_name}</strong> ({deletingStaff.user.email})?
            </p>
            <div className="text-xs text-muted-foreground">
              This action immediately terminates their staff permissions for {activeClinic.name}. Their historical records and user account will remain intact.
            </div>
            <div className="flex items-center justify-end gap-3 pt-3 border-t">
              <Button variant="outline" onClick={() => setDeletingStaff(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteSubmit}
                disabled={deleteStaffMutation.isPending}
              >
                {deleteStaffMutation.isPending ? "Revoking..." : "Revoke Access"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
