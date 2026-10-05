import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { systemApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  Building2,
  Stethoscope,
  Activity,
  CheckCircle2,
  Clock,
  ArrowRight,
} from "lucide-react";

export function HomePage() {
  const { data: health, isLoading, isError } = useQuery({
    queryKey: ["systemHealth"],
    queryFn: systemApi.checkHealth,
    retry: 1,
  });

  return (
    <div className="container mx-auto px-4 py-12 sm:px-8">
      {/* Hero Section */}
      <div className="mx-auto max-w-4xl text-center">
        <Badge variant="outline" className="mb-4 gap-1.5 px-3 py-1 text-sm font-medium">
          <Activity className="h-3.5 w-3.5 text-primary" /> Day 2 Foundation Active
        </Badge>
        <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-6xl">
          Multi-Clinic Doctor Appointments, <br />
          <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Simplified for Everyone
          </span>
        </h1>
        <p className="mt-6 text-lg leading-8 text-muted-foreground">
          EazyDoc connects patients, verified doctors, and clinics with real-time queue management,
          intelligent schedule conflict resolution, and integrated digital healthcare workflows.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link to="/patient">
            <Button size="lg" className="gap-2">
              Book Appointment <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link to="/clinic">
            <Button size="lg" variant="outline">
              Clinic Management
            </Button>
          </Link>
        </div>
      </div>

      {/* Backend Integration & Health Status Card */}
      <div className="mx-auto mt-14 max-w-2xl">
        <Card className="border-primary/20 shadow-md">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Backend API & System Health</CardTitle>
              {isLoading ? (
                <Badge variant="secondary">Checking...</Badge>
              ) : isError ? (
                <Badge variant="destructive">Offline (Check Backend)</Badge>
              ) : (
                <Badge variant="success" className="gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Operational
                </Badge>
              )}
            </div>
            <CardDescription>
              Real-time validation connecting React 19 + TanStack Query + Django REST API.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-muted/50 p-3">
                <div className="text-xs font-semibold text-muted-foreground uppercase">API Status</div>
                <div className="mt-1 text-sm font-bold text-foreground">
                  {health?.status || (isLoading ? "..." : "Offline")}
                </div>
              </div>
              <div className="rounded-lg bg-muted/50 p-3">
                <div className="text-xs font-semibold text-muted-foreground uppercase">Database</div>
                <div className="mt-1 text-sm font-bold text-foreground">
                  {health?.database || (isLoading ? "..." : "Offline")}
                </div>
              </div>
              <div className="rounded-lg bg-muted/50 p-3">
                <div className="text-xs font-semibold text-muted-foreground uppercase">Redis</div>
                <div className="mt-1 text-sm font-bold text-foreground">
                  {health?.redis || (isLoading ? "..." : "Offline")}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Portal Directory Cards */}
      <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="transition hover:border-primary/50 hover:shadow-md">
          <CardHeader>
            <Calendar className="h-8 w-8 text-primary" />
            <CardTitle className="mt-4">Patient Portal</CardTitle>
            <CardDescription>Search verified doctors, view clinic slots, and pay online.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/patient">
              <Button variant="ghost" size="sm" className="w-full justify-between">
                Visit Portal <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="transition hover:border-primary/50 hover:shadow-md">
          <CardHeader>
            <Building2 className="h-8 w-8 text-primary" />
            <CardTitle className="mt-4">Clinic SaaS</CardTitle>
            <CardDescription>Manage doctors, shifts, live receptionist queue, and revenues.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/clinic">
              <Button variant="ghost" size="sm" className="w-full justify-between">
                Visit Portal <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="transition hover:border-primary/50 hover:shadow-md">
          <CardHeader>
            <Stethoscope className="h-8 w-8 text-primary" />
            <CardTitle className="mt-4">Doctor Suite</CardTitle>
            <CardDescription>Multi-clinic roster, clinical consultations, and digital prescriptions.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/doctor">
              <Button variant="ghost" size="sm" className="w-full justify-between">
                Visit Portal <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="transition hover:border-primary/50 hover:shadow-md">
          <CardHeader>
            <Clock className="h-8 w-8 text-primary" />
            <CardTitle className="mt-4">Platform Admin</CardTitle>
            <CardDescription>Clinic verification, doctor credentialing, and commission controls.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/admin">
              <Button variant="ghost" size="sm" className="w-full justify-between">
                Visit Portal <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default HomePage;
