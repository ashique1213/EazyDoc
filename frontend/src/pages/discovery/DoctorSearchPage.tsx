import { useEffect, useState, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Search,
  MapPin,
  Calendar,
  CheckCircle2,
  X,
  Stethoscope,
  Building2,
  ArrowRight,
  Briefcase,
  Languages,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  useCities,
  useDoctorSearch,
  useSpecializations,
} from "@/features/discovery";

export function DoctorSearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Read URL params
  const searchQuery = searchParams.get("search") || "";
  const selectedSpec = searchParams.get("specialization") || "";
  const selectedCity = searchParams.get("city") || "";
  const areaQuery = searchParams.get("area") || "";
  const dateQuery = searchParams.get("date") || "";
  const pageParam = parseInt(searchParams.get("page") || "1", 10);
  const orderingParam = searchParams.get("ordering") || "name";

  // Local state for debounced search input
  const [searchInput, setSearchInput] = useState(searchQuery);
  const [areaInput, setAreaInput] = useState(areaQuery);

  // Sync state if URL changes externally
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

  // Debounce search text
  useEffect(() => {
    const handler = setTimeout(() => {
      if (searchInput !== searchQuery) {
        updateFilter("search", searchInput, true);
      }
    }, 400);
    return () => clearTimeout(handler);
  }, [searchInput, searchQuery, updateFilter]);

  // Debounce area text
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

  // Queries
  const { data: specializations } = useSpecializations();
  const { data: cities } = useCities();
  const { data, isLoading, isError, error } = useDoctorSearch({
    search: searchQuery,
    specialization: selectedSpec,
    city: selectedCity,
    area: areaQuery,
    date: dateQuery,
    ordering: orderingParam,
    page: pageParam,
  });

  const doctors = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = data?.total_pages || 1;

  const hasActiveFilters = Boolean(
    searchQuery || selectedSpec || selectedCity || areaQuery || dateQuery
  );

  return (
    <div className="min-h-screen bg-slate-50/50 py-8 text-foreground dark:bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Breadcrumb & Title */}
        <div className="mb-8">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Link to="/" className="hover:text-foreground">Home</Link>
            <span>/</span>
            <span className="font-medium text-foreground">Find Doctors</span>
          </div>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl text-slate-900 dark:text-slate-100">
            Find & Consult Verified Doctors
          </h1>
          <p className="mt-1.5 text-base text-muted-foreground">
            Search qualified medical specialists across top accredited clinics and view verified fees and open slots.
          </p>
        </div>

        {/* Filter Toolbar Card */}
        <div className="mb-8 rounded-2xl border border-border/80 bg-card p-5 shadow-sm">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Doctor name, clinic..."
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

            {/* Specialization Dropdown */}
            <div>
              <select
                aria-label="Filter by specialization"
                value={selectedSpec}
                onChange={(e) => updateFilter("specialization", e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="">All Specializations</option>
                {specializations?.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
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
                placeholder="Locality or Pincode..."
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

          {/* Secondary Filter Row: Date Selector & Clear Filters */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/50 pt-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground">Filter by Date:</span>
                <input
                  type="date"
                  aria-label="Filter by appointment date"
                  value={dateQuery}
                  onChange={(e) => updateFilter("date", e.target.value)}
                  className="rounded-md border border-input bg-background px-2.5 py-1 text-xs"
                />
                {dateQuery && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => updateFilter("date", "")}
                    className="h-7 px-2 text-xs"
                  >
                    Clear date
                  </Button>
                )}
              </div>

              {/* Sort selector */}
              <div className="flex items-center space-x-2">
                <span className="text-xs font-medium text-muted-foreground">Sort:</span>
                <select
                  aria-label="Sort order"
                  value={orderingParam}
                  onChange={(e) => updateFilter("ordering", e.target.value, false)}
                  className="h-7 rounded border border-input bg-background px-2 text-xs"
                >
                  <option value="name">Name (A–Z)</option>
                  <option value="-name">Name (Z–A)</option>
                  <option value="-experience">Experience (Highest)</option>
                  <option value="experience">Experience (Lowest)</option>
                </select>
              </div>
            </div>

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
                <span>Reset all filters</span>
              </Button>
            )}
          </div>
        </div>

        {/* Results Header */}
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">
            {isLoading ? (
              "Searching doctors..."
            ) : (
              <>
                Showing <span className="font-semibold text-foreground">{doctors.length}</span> of{" "}
                <span className="font-semibold text-foreground">{totalCount}</span> verified doctors
              </>
            )}
          </p>
        </div>

        {/* Loading Skeletons */}
        {isLoading && (
          <div className="space-y-4">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="animate-pulse rounded-xl border border-border bg-card p-6 shadow-sm"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start space-x-4">
                    <div className="h-16 w-16 rounded-full bg-muted" />
                    <div className="space-y-2">
                      <div className="h-5 w-40 rounded bg-muted" />
                      <div className="h-4 w-28 rounded bg-muted" />
                      <div className="h-3 w-56 rounded bg-muted" />
                    </div>
                  </div>
                  <div className="h-10 w-32 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center text-destructive">
            <h3 className="text-lg font-bold">Failed to load doctors</h3>
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

        {/* Empty Search State */}
        {!isLoading && !isError && doctors.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center shadow-sm">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Stethoscope className="h-7 w-7" />
            </div>
            <h3 className="mt-4 text-lg font-bold text-foreground">No verified doctors found</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              We couldn&apos;t find any doctors matching your current search criteria. Try modifying your filters or clearing them to explore all specialists.
            </p>
            {hasActiveFilters && (
              <Button onClick={clearAllFilters} className="mt-6" size="sm">
                Clear Filters
              </Button>
            )}
          </div>
        )}

        {/* Doctor Result Cards */}
        {!isLoading && !isError && doctors.length > 0 && (
          <div className="space-y-5">
            {doctors.map((doctor) => {
              const primaryLocation = doctor.practice_locations[0];
              return (
                <Card
                  key={doctor.id}
                  className="group overflow-hidden transition-all duration-200 hover:border-primary/50 hover:shadow-md"
                >
                  <CardContent className="p-6">
                    <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                      {/* Left: Avatar & Profile Info */}
                      <div className="flex flex-1 items-start space-x-4 sm:space-x-5">
                        {/* Avatar */}
                        <div className="relative flex-shrink-0">
                          {doctor.profile_photo ? (
                            <img
                              src={doctor.profile_photo}
                              alt={doctor.full_name}
                              className="h-20 w-20 rounded-2xl object-cover shadow-sm ring-1 ring-border"
                            />
                          ) : (
                            <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500/20 to-blue-500/20 text-xl font-bold text-teal-700 dark:text-teal-400 ring-1 ring-teal-500/30">
                              {doctor.full_name
                                .replace(/^Dr\.\s*/i, "")
                                .split(" ")
                                .map((n) => n[0])
                                .slice(0, 2)
                                .join("")}
                            </div>
                          )}
                          {doctor.is_verified && (
                            <span
                              className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white shadow-sm ring-2 ring-background"
                              title="Verified Doctor"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" />
                            </span>
                          )}
                        </div>

                        {/* Details */}
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h2 className="text-xl font-bold tracking-tight text-foreground transition group-hover:text-primary">
                              {doctor.full_name}
                            </h2>
                            <Badge variant="success" className="gap-1 text-[11px] font-semibold">
                              <CheckCircle2 className="h-3 w-3" /> Verified
                            </Badge>
                          </div>

                          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                            <span className="font-medium text-foreground">
                              {doctor.specialization}
                            </span>
                            <span>•</span>
                            <span>{doctor.qualifications}</span>
                            <span>•</span>
                            <span className="inline-flex items-center gap-1 font-medium text-foreground">
                              <Briefcase className="h-3.5 w-3.5 text-muted-foreground" />
                              {doctor.years_of_experience} yrs experience
                            </span>
                          </div>

                          {doctor.languages && (
                            <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                              <Languages className="h-3.5 w-3.5 text-muted-foreground" />
                              <span>Speaks: {doctor.languages}</span>
                            </div>
                          )}

                          {doctor.bio && (
                            <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
                              {doctor.bio}
                            </p>
                          )}

                          {/* Practice Locations Summary */}
                          <div className="mt-4 border-t border-border/60 pt-3">
                            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              Available at {doctor.practice_locations.length} Clinic
                              {doctor.practice_locations.length > 1 ? "s" : ""}:
                            </div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {doctor.practice_locations.map((loc) => (
                                <div
                                  key={loc.doctor_clinic_id}
                                  className="inline-flex items-center gap-2 rounded-lg border border-border/80 bg-muted/30 px-3 py-1.5 text-xs text-foreground"
                                >
                                  <Building2 className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
                                  <span className="font-semibold">{loc.clinic_name}</span>
                                  <span className="text-muted-foreground">({loc.city})</span>
                                  <span className="font-bold text-emerald-600 dark:text-emerald-400">
                                    ₹{loc.consultation_fee}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Right: Pricing & CTA */}
                      <div className="flex flex-row items-center justify-between border-t border-border pt-4 sm:border-0 sm:pt-0 lg:flex-col lg:items-end lg:justify-start lg:space-y-4">
                        <div className="text-left lg:text-right">
                          <span className="text-xs text-muted-foreground">Consultation Fee</span>
                          <div className="text-2xl font-extrabold text-foreground">
                            ₹
                            {doctor.min_consultation_fee
                              ? doctor.min_consultation_fee
                              : primaryLocation?.consultation_fee || "0"}
                          </div>
                          <span className="text-[11px] text-muted-foreground">per consultation</span>
                        </div>

                        <Link to={`/doctors/${doctor.id}`}>
                          <Button className="gap-2 shadow-sm" size="default">
                            <span>View Profile & Slots</span>
                            <ArrowRight className="h-4 w-4" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
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

export default DoctorSearchPage;
