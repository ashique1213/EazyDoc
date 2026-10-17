import { useEffect, useState, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Search,
  MapPin,
  Building2,
  Users,
  Phone,
  ArrowRight,
  X,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { useCities, useClinicSearch } from "@/features/discovery";

export function ClinicSearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const searchQuery = searchParams.get("search") || "";
  const selectedCity = searchParams.get("city") || "";
  const areaQuery = searchParams.get("area") || "";
  const pageParam = parseInt(searchParams.get("page") || "1", 10);
  const orderingParam = searchParams.get("ordering") || "name";

  const [searchInput, setSearchInput] = useState(searchQuery);
  const [areaInput, setAreaInput] = useState(areaQuery);

  useEffect(() => {
    setSearchInput(searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    setAreaInput(areaQuery);
  }, [areaQuery]);

  const updateFilter = useCallback(
    (key: string, value: string, resetPage = true) => {
      const next = new URLSearchParams(searchParams);
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      if (resetPage) {
        next.set("page", "1");
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams]
  );

  // Debounced search text
  useEffect(() => {
    const handler = setTimeout(() => {
      if (searchInput !== searchQuery) {
        updateFilter("search", searchInput, true);
      }
    }, 400);
    return () => clearTimeout(handler);
  }, [searchInput, searchQuery, updateFilter]);

  // Debounced area text
  useEffect(() => {
    const handler = setTimeout(() => {
      if (areaInput !== areaQuery) {
        updateFilter("area", areaInput, true);
      }
    }, 400);
    return () => clearTimeout(handler);
  }, [areaInput, areaQuery, updateFilter]);

  const clearAllFilters = () => {
    setSearchInput("");
    setAreaInput("");
    setSearchParams(new URLSearchParams());
  };

  const { data: cities } = useCities();
  const { data, isLoading, isError, error } = useClinicSearch({
    search: searchQuery,
    city: selectedCity,
    area: areaQuery,
    ordering: orderingParam,
    page: pageParam,
  });

  const clinics = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = data?.total_pages || 1;

  const hasActiveFilters = Boolean(searchQuery || selectedCity || areaQuery);

  return (
    <div className="min-h-screen bg-slate-50/50 py-8 text-foreground dark:bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Breadcrumb & Title */}
        <div className="mb-8">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Link to="/" className="hover:text-foreground">Home</Link>
            <span>/</span>
            <span className="font-medium text-foreground">Find Clinics</span>
          </div>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl text-slate-900 dark:text-slate-100">
            Approved Healthcare Clinics & Hospitals
          </h1>
          <p className="mt-1.5 text-base text-muted-foreground">
            Explore verified partner clinics, medical facilities, operating hours, and associated specialist doctors.
          </p>
        </div>

        {/* Filter Card */}
        <div className="mb-8 rounded-2xl border border-border/80 bg-card p-5 shadow-sm">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search clinic by name..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="pl-9 pr-8"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => setSearchInput("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* City Dropdown */}
            <div>
              <select
                aria-label="Filter by city"
                value={selectedCity}
                onChange={(e) => updateFilter("city", e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="">All Cities</option>
                {cities?.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Area / Locality Search */}
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Area, Street or Pincode..."
                value={areaInput}
                onChange={(e) => setAreaInput(e.target.value)}
                className="pl-9 pr-8"
              />
              {areaInput && (
                <button
                  type="button"
                  onClick={() => setAreaInput("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Secondary Filter Row */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/50 pt-4 text-sm">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-medium text-muted-foreground">Sort Clinics:</span>
              <select
                aria-label="Sort order"
                value={orderingParam}
                onChange={(e) => updateFilter("ordering", e.target.value, false)}
                className="h-7 rounded border border-input bg-background px-2 text-xs"
              >
                <option value="name">Name (A–Z)</option>
                <option value="-name">Name (Z–A)</option>
                <option value="city">City (A–Z)</option>
              </select>
            </div>

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
                <span>Reset filters</span>
              </Button>
            )}
          </div>
        </div>

        {/* Results Header */}
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">
            {isLoading ? (
              "Finding clinics..."
            ) : (
              <>
                Showing <span className="font-semibold text-foreground">{clinics.length}</span> of{" "}
                <span className="font-semibold text-foreground">{totalCount}</span> approved clinics
              </>
            )}
          </p>
        </div>

        {/* Loading Skeletons */}
        {isLoading && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div
                key={n}
                className="animate-pulse rounded-2xl border border-border bg-card p-6 shadow-sm"
              >
                <div className="h-12 w-12 rounded-xl bg-muted" />
                <div className="mt-4 h-5 w-3/4 rounded bg-muted" />
                <div className="mt-2 h-4 w-1/2 rounded bg-muted" />
                <div className="mt-4 h-16 rounded bg-muted" />
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center text-destructive">
            <h3 className="text-lg font-bold">Failed to load clinics</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {error instanceof Error ? error.message : "A network error occurred. Please try again."}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
              className="mt-4"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !isError && clinics.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center shadow-sm">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Building2 className="h-7 w-7" />
            </div>
            <h3 className="mt-4 text-lg font-bold text-foreground">No clinics found</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              No approved clinics match your search query. Try searching with a broader location or clearing your filters.
            </p>
            {hasActiveFilters && (
              <Button onClick={clearAllFilters} className="mt-6" size="sm">
                Clear Filters
              </Button>
            )}
          </div>
        )}

        {/* Clinic Cards Grid */}
        {!isLoading && !isError && clinics.length > 0 && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {clinics.map((clinic) => (
              <Card
                key={clinic.id}
                className="group flex flex-col justify-between overflow-hidden rounded-2xl transition duration-200 hover:border-primary/50 hover:shadow-md"
              >
                <CardContent className="flex flex-1 flex-col p-6">
                  {/* Top: Branding & Title */}
                  <div className="flex items-start space-x-3.5">
                    {clinic.logo ? (
                      <img
                        src={clinic.logo}
                        alt={clinic.name}
                        className="h-12 w-12 rounded-xl object-cover ring-1 ring-border"
                      />
                    ) : (
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-400 ring-1 ring-teal-500/20">
                        <Building2 className="h-6 w-6" />
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <h2 className="text-lg font-bold text-foreground transition group-hover:text-primary">
                        {clinic.name}
                      </h2>
                      <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="truncate">
                          {clinic.city}, {clinic.state}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  {clinic.description && (
                    <p className="mt-4 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                      {clinic.description}
                    </p>
                  )}

                  {/* Location and Info */}
                  <div className="mt-4 space-y-2 border-t border-border/60 pt-3 text-xs text-muted-foreground">
                    <div className="flex items-start gap-1.5">
                      <MapPin className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
                      <span className="line-clamp-2">
                        {clinic.address_line_1}
                        {clinic.address_line_2 ? `, ${clinic.address_line_2}` : ""}, {clinic.pincode}
                      </span>
                    </div>

                    {clinic.phone && (
                      <div className="flex items-center gap-1.5">
                        <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>{clinic.phone}</span>
                      </div>
                    )}

                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                      <span>Operating TZ: {clinic.timezone}</span>
                    </div>
                  </div>

                  {/* Associated Doctors Badge & CTA */}
                  <div className="mt-5 flex items-center justify-between border-t border-border/80 pt-4">
                    <div className="inline-flex items-center gap-1.5 rounded-full bg-teal-500/10 px-2.5 py-1 text-xs font-semibold text-teal-700 dark:text-teal-400">
                      <Users className="h-3.5 w-3.5" />
                      <span>{clinic.doctor_count || 0} Doctors Available</span>
                    </div>

                    <Link to={`/clinics/${clinic.id}`}>
                      <Button variant="ghost" size="sm" className="gap-1 px-2 text-xs group-hover:text-primary">
                        <span>View Clinic</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Pagination */}
        {!isLoading && totalPages > 1 && (
          <div className="mt-8 flex items-center justify-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              disabled={pageParam <= 1}
              onClick={() => updateFilter("page", String(pageParam - 1), false)}
            >
              Previous
            </Button>
            <span className="px-3 text-sm text-muted-foreground">
              Page <span className="font-semibold text-foreground">{pageParam}</span> of{" "}
              <span className="font-semibold text-foreground">{totalPages}</span>
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={pageParam >= totalPages}
              onClick={() => updateFilter("page", String(pageParam + 1), false)}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ClinicSearchPage;
