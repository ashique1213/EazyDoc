import { useState } from "react";
import { Link } from "react-router-dom";
import { Search, ChevronLeft, ChevronRight, Eye, ShieldCheck, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ClinicStatusBadge, useAdminClinics } from "@/features/clinics";

export function AdminClinicsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  const { data, isLoading, isError, refetch } = useAdminClinics({
    status: statusFilter,
    search: searchQuery,
    page,
  });

  const clinics = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.ceil(totalCount / 15) || 1;

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    refetch();
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Super Admin — Clinic Oversight</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Review, credential, verify, and moderate healthcare clinics across the EazyDoc platform.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="inline-flex items-center gap-1.5 rounded-lg border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-sm">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Total: {totalCount} Clinics</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card className="border bg-card/60">
        <CardContent className="p-4">
          <form onSubmit={handleSearchSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search clinic name, city, or owner email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>

            {/* Status Tabs / Select */}
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
              {["ALL", "PENDING", "APPROVED", "REJECTED", "SUSPENDED", "DRAFT"].map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => {
                    setStatusFilter(st);
                    setPage(1);
                  }}
                  className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors shrink-0 ${
                    statusFilter === st
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted/40 text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}
                >
                  {st === "ALL" ? "All" : st.charAt(0) + st.slice(1).toLowerCase()}
                </button>
              ))}
            </div>

            <Button type="submit" size="sm" variant="secondary" className="shrink-0">
              Filter
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Table Container */}
      <Card className="border overflow-hidden">
        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-sm text-destructive">Failed to load clinics. Ensure you are signed in as Super Admin.</p>
            <Button size="sm" variant="outline" className="mt-4" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        ) : clinics.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-sm text-muted-foreground">No clinics match the current criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted/40 text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-semibold">Clinic Name</th>
                  <th className="px-4 py-3 font-semibold">Owner</th>
                  <th className="px-4 py-3 font-semibold">Location</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Created / Submitted</th>
                  <th className="px-4 py-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {clinics.map((clinic) => (
                  <tr key={clinic.id} className="hover:bg-accent/40 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-foreground text-sm">{clinic.name}</div>
                      <div className="font-mono text-[11px] text-muted-foreground">/{clinic.slug}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-foreground">
                        {clinic.owner.first_name} {clinic.owner.last_name}
                      </div>
                      <div className="text-[11px] text-muted-foreground">{clinic.owner.email}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div>{clinic.city}, {clinic.state}</div>
                      <div className="text-[11px] text-muted-foreground">{clinic.country}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <ClinicStatusBadge status={clinic.status} />
                    </td>
                    <td className="px-4 py-3.5 text-muted-foreground">
                      {new Date(clinic.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <Link to={`/admin/clinics/${clinic.id}`}>
                        <Button size="sm" variant="outline" className="h-7 px-2.5 text-xs gap-1">
                          <Eye className="h-3.5 w-3.5" />
                          Review
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {totalCount > 15 && (
          <div className="flex items-center justify-between border-t px-4 py-3 text-xs text-muted-foreground bg-muted/20">
            <span>
              Page {page} of {totalPages} ({totalCount} total records)
            </span>
            <div className="flex items-center space-x-1.5">
              <Button
                variant="outline"
                size="sm"
                className="h-7 w-7 p-0"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-7 w-7 p-0"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default AdminClinicsPage;
