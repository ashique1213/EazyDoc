import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Percent,
  Building2,
  History,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Info,
  ShieldCheck,
  Edit2,
  X,
} from "lucide-react";
import {
  useAdminCommissionSettings,
  useUpdateAdminCommissionSettings,
} from "@/features/admin";

export function AdminCommissionSettingsPage() {
  const { data, isLoading, refetch } = useAdminCommissionSettings();
  const updateMutation = useUpdateAdminCommissionSettings();

  // Form states
  const [defaultRateInput, setDefaultRateInput] = useState<string>("");
  const [defaultReason, setDefaultReason] = useState<string>("");
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Clinic override modal
  const [editingClinic, setEditingClinic] = useState<{
    clinic_id: string;
    clinic_name: string;
    current_override: string | null;
  } | null>(null);
  const [clinicRateInput, setClinicRateInput] = useState<string>("");
  const [clinicReason, setClinicReason] = useState<string>("");

  const handleUpdateDefaultRate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSuccess(null);
    setFormError(null);

    const num = parseFloat(defaultRateInput);
    if (isNaN(num) || num < 0 || num > 100) {
      setFormError("Commission percentage must be between 0.00% and 100.00%.");
      return;
    }

    try {
      await updateMutation.mutateAsync({
        default_rate: num,
        reason: defaultReason.trim() || "Global default commission rate update",
      });
      setFormSuccess("Platform default commission rate updated successfully.");
      setDefaultRateInput("");
      setDefaultReason("");
      refetch();
    } catch {
      setFormError("Failed to update platform commission rate. Check permissions.");
    }
  };

  const handleUpdateClinicOverride = async () => {
    if (!editingClinic) return;
    setFormSuccess(null);
    setFormError(null);

    const val = clinicRateInput.trim();
    let num: number | null = null;
    if (val !== "") {
      num = parseFloat(val);
      if (isNaN(num) || num < 0 || num > 100) {
        setFormError("Clinic override percentage must be between 0.00% and 100.00%.");
        return;
      }
    }

    try {
      await updateMutation.mutateAsync({
        clinic_id: editingClinic.clinic_id,
        clinic_rate: num,
        reason: clinicReason.trim() || "Clinic commercial terms modification",
      });
      setEditingClinic(null);
      setClinicRateInput("");
      setClinicReason("");
      refetch();
    } catch {
      setFormError("Failed to update clinic commission override.");
    }
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
            <Link to="/admin/finance" className="text-xs text-muted-foreground hover:underline">
              Finance
            </Link>
            <span className="text-xs text-muted-foreground">/</span>
            <span className="text-xs font-semibold text-foreground">Commission Settings</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2 mt-1">
            <Percent className="h-6 w-6 text-primary" />
            Platform & Clinic Commission Configuration
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Configure global default SaaS revenue rates and manage clinic-specific commercial agreements.
          </p>
        </div>
      </div>

      {/* Business Policy Alert */}
      <div className="rounded-xl border bg-muted/30 p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
          <Info className="h-4 w-4 text-primary" />
          <span>Established Platform Commission Rules:</span>
        </div>
        <ul className="text-xs text-muted-foreground list-disc list-inside space-y-1">
          <li>The standard platform default commission rate is applied to clinics without custom overrides.</li>
          <li>A clinic-specific rate override takes absolute precedence when explicitly configured.</li>
          <li>Commission updates take effect for future eligible transactions only. Historical records are immutable.</li>
          <li>All changes are permanently logged to the administrative security audit trail with recorded justification.</li>
        </ul>
      </div>

      {formSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 text-xs rounded-lg flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {formSuccess}
        </div>
      )}

      {formError && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-lg flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {formError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column: Global Default Configuration Card */}
        <Card className="border-muted/80 shadow-sm lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              Global Default Rate
            </CardTitle>
            <CardDescription className="text-xs">
              Applies to all standard bookings across platform facilities.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 text-center space-y-1">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Current Effective Default
              </span>
              <div className="text-4xl font-extrabold text-primary">
                {isLoading ? "—" : `${data?.default_rate ?? "5.00"}%`}
              </div>
            </div>

            <form onSubmit={handleUpdateDefaultRate} className="space-y-3 pt-2 border-t">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  New Default Rate Percentage (%):
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  placeholder="e.g. 5.50"
                  value={defaultRateInput}
                  onChange={(e) => setDefaultRateInput(e.target.value)}
                  className="text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Reason for Adjustment:
                </label>
                <Input
                  placeholder="e.g. Q4 Platform policy update"
                  value={defaultReason}
                  onChange={(e) => setDefaultReason(e.target.value)}
                  className="text-xs"
                />
              </div>

              <Button
                type="submit"
                size="sm"
                className="w-full text-xs"
                disabled={updateMutation.isPending || !defaultRateInput}
              >
                {updateMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                )}
                Save Platform Default Rate
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Right Column: Clinic Specific Overrides Table */}
        <Card className="border-muted/80 shadow-sm lg:col-span-2 overflow-hidden">
          <CardHeader className="bg-muted/20 border-b">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-emerald-600" />
                  Clinic Facility Commission Overrides
                </CardTitle>
                <CardDescription className="text-xs">
                  Review and customize commercial commission terms per healthcare establishment.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="py-20 flex justify-center text-muted-foreground text-xs">
                <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading clinic agreements...
              </div>
            ) : data?.clinics && data.clinics.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b bg-muted/40 text-muted-foreground font-semibold text-left">
                      <th className="py-3 px-4">Clinic Facility</th>
                      <th className="py-3 px-4">Location</th>
                      <th className="py-3 px-4">Agreement Status</th>
                      <th className="py-3 px-4">Effective Rate</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.clinics.map((c) => (
                      <tr key={c.clinic_id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-4 font-medium text-foreground">
                          {c.clinic_name}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">{c.city}</td>
                        <td className="py-3 px-4">
                          {c.has_override ? (
                            <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-700 border-amber-500/20 font-mono">
                              Custom {c.override_rate}%
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[10px]">
                              Default
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 px-4 font-bold text-foreground">
                          {c.effective_rate}%
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setEditingClinic({
                                clinic_id: c.clinic_id,
                                clinic_name: c.clinic_name,
                                current_override: c.override_rate,
                              });
                              setClinicRateInput(c.override_rate || "");
                            }}
                            className="h-7 px-2 text-xs"
                          >
                            <Edit2 className="h-3 w-3 mr-1" /> Edit Terms
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-16 text-center text-xs text-muted-foreground">
                No approved clinics registered yet.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Audit History of Commission Adjustments */}
      <Card className="border-muted/80 shadow-sm overflow-hidden">
        <CardHeader className="bg-muted/20 border-b">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            Commission Rate Adjustment Audit Trail
          </CardTitle>
          <CardDescription className="text-xs">
            Permanent record of administrator identities, timestamps, and justifications.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {data?.history && data.history.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-muted/40 text-muted-foreground font-semibold text-left">
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Admin Actor</th>
                    <th className="py-3 px-4">Rate Details</th>
                    <th className="py-3 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.history.map((h) => (
                    <tr key={h.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-semibold">
                        <Badge variant="outline" className="text-[10px]">
                          {h.action}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-foreground">{h.actor_email}</td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-muted-foreground">
                          {JSON.stringify(h.details)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(h.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-muted-foreground">
              No commission rate adjustments recorded in the audit trail.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Clinic Override Modal */}
      {editingClinic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card w-full max-w-md rounded-xl border shadow-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground">
                  Custom Commission Override
                </h3>
                <p className="text-xs text-muted-foreground">{editingClinic.clinic_name}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditingClinic(null)}
                className="h-7 w-7 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              Configure a clinic-specific platform commission percentage. Leave blank to clear the
              override and restore the platform default rate.
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Custom Commission Percentage (%):
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                max="100"
                placeholder="Leave blank for platform default"
                value={clinicRateInput}
                onChange={(e) => setClinicRateInput(e.target.value)}
                className="text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Commercial Justification / Reason:
              </label>
              <Input
                placeholder="e.g. High-volume enterprise partner tier"
                value={clinicReason}
                onChange={(e) => setClinicReason(e.target.value)}
                className="text-xs"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditingClinic(null)}
                disabled={updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleUpdateClinicOverride}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                )}
                Save Override
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminCommissionSettingsPage;
