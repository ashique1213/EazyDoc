import { Link, Outlet } from "react-router-dom";
import {
  Stethoscope,
  Building2,
  UserCircle,
  LayoutDashboard,
  ArrowLeft,
  LogOut,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  Calendar,
  Users,
  CreditCard,
  Percent,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore, useLogout } from "@/features/auth";

interface DashboardLayoutProps {
  roleTitle?: string;
}

export function DashboardLayout({ roleTitle = "Dashboard" }: DashboardLayoutProps) {
  const { user } = useAuthStore();
  const logoutMutation = useLogout();

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  const initials = user?.first_name && user?.last_name
    ? `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    : user?.email
    ? user.email[0].toUpperCase()
    : "U";

  return (
    <div className="flex min-h-screen bg-muted/20">
      {/* Sidebar shell */}
      <aside className="hidden w-64 flex-col border-r bg-card p-4 md:flex">
        <Link to="/" className="mb-8 flex items-center space-x-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Stethoscope className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold text-foreground">
            Eazy<span className="text-primary">Doc</span>
          </span>
        </Link>

        <div className="mb-4 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {roleTitle}
        </div>

        <nav className="flex-1 space-y-1">
          {user?.role === "CLINIC_OWNER" || user?.role === "STAFF" ? (
            <>
              <Link
                to="/clinic/dashboard"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
              >
                <LayoutDashboard className="h-4 w-4 text-primary" />
                <span>Dashboard</span>
              </Link>
              <Link
                to="/clinic/appointments"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Calendar className="h-4 w-4 text-blue-600" />
                <span>Appointments Desk</span>
              </Link>
              <Link
                to="/clinic/calendar"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Calendar className="h-4 w-4 text-emerald-600" />
                <span>Master Calendar</span>
              </Link>
              <Link
                to="/clinic/doctors"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Stethoscope className="h-4 w-4 text-indigo-600" />
                <span>Doctors & Fees</span>
              </Link>
              {user?.role === "CLINIC_OWNER" && (
                <Link
                  to="/clinic/staff"
                  className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  <Users className="h-4 w-4 text-purple-600" />
                  <span>Clinic Staff</span>
                </Link>
              )}
              <Link
                to="/clinic/finance"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <CreditCard className="h-4 w-4 text-emerald-600" />
                <span>Finance & Ledger</span>
              </Link>
              <Link
                to="/clinic/settings"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Building2 className="h-4 w-4 text-amber-600" />
                <span>Clinic Settings</span>
              </Link>
              <div className="pt-2 mt-2 border-t text-[11px] font-semibold text-muted-foreground px-3 uppercase tracking-wider">
                Clinics Overview
              </div>
              <Link
                to="/clinic/my-clinics"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Building2 className="h-4 w-4" />
                <span>My Clinics</span>
              </Link>
              {user?.role === "CLINIC_OWNER" && (
                <Link
                  to="/clinic/register"
                  className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  <Building2 className="h-4 w-4" />
                  <span>Register Clinic</span>
                </Link>
              )}
            </>
          ) : user?.role === "SUPER_ADMIN" ? (
            <>
              <Link
                to="/admin"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
              >
                <LayoutDashboard className="h-4 w-4 text-primary" />
                <span>Dashboard Overview</span>
              </Link>
              <Link
                to="/admin/clinics"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Building2 className="h-4 w-4 text-emerald-600" />
                <span>Clinics Oversight</span>
              </Link>
              <Link
                to="/admin/doctors"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Stethoscope className="h-4 w-4 text-blue-600" />
                <span>Doctors Verification</span>
              </Link>
              <Link
                to="/admin/users"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Users className="h-4 w-4 text-purple-600" />
                <span>User Accounts</span>
              </Link>
              <Link
                to="/admin/appointments"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Calendar className="h-4 w-4 text-indigo-600" />
                <span>Appointments Admin</span>
              </Link>
              <Link
                to="/admin/finance"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <CreditCard className="h-4 w-4 text-emerald-600" />
                <span>Finance & Payments</span>
              </Link>
              <Link
                to="/admin/settings/commission"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Percent className="h-4 w-4 text-amber-600" />
                <span>Commission Settings</span>
              </Link>
              <Link
                to="/admin/audit-logs"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <ShieldCheck className="h-4 w-4 text-primary" />
                <span>Audit Trail</span>
              </Link>
            </>
          ) : user?.role === "DOCTOR" ? (
            <>
              <Link
                to="/doctor"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
              >
                <LayoutDashboard className="h-4 w-4 text-primary" />
                <span>Overview</span>
              </Link>
              <Link
                to="/doctor/profile"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <UserCircle className="h-4 w-4" />
                <span>Doctor Profile</span>
              </Link>
              <Link
                to="/doctor/clinics"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Building2 className="h-4 w-4" />
                <span>Associated Clinics</span>
              </Link>
              <Link
                to="/doctor/schedules"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Calendar className="h-4 w-4 text-primary" />
                <span>Schedule & Leaves</span>
              </Link>
              <Link
                to="/doctor/verification"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <ShieldCheck className="h-4 w-4" />
                <span>Verification Status</span>
              </Link>
            </>
          ) : user?.role === "PATIENT" ? (
            <>
              <Link
                to="/patient"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
              >
                <LayoutDashboard className="h-4 w-4 text-primary" />
                <span>Overview</span>
              </Link>
              <Link
                to="/my-appointments"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Calendar className="h-4 w-4" />
                <span>My Appointments</span>
              </Link>
              <Link
                to="/doctors"
                className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <Stethoscope className="h-4 w-4" />
                <span>Find Doctors</span>
              </Link>
            </>
          ) : (
            <div className="flex items-center space-x-3 rounded-lg bg-primary/10 px-3 py-2 text-sm font-medium text-primary">
              <LayoutDashboard className="h-4 w-4" />
              <span>Overview</span>
            </div>
          )}
          <div className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent cursor-pointer transition-colors">
            <UserCircle className="h-4 w-4" />
            <span>Profile</span>
          </div>
        </nav>

        {/* User Card in Sidebar */}
        {user && (
          <div className="mb-4 rounded-xl border bg-muted/40 p-3 space-y-2">
            <div className="flex items-center space-x-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="truncate text-xs font-semibold text-foreground">
                  {user.first_name} {user.last_name}
                </p>
                <p className="truncate text-[10px] text-muted-foreground">
                  {user.email}
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-[10px] py-0">
                {user.role}
              </Badge>
              {user.is_verified ? (
                <span className="text-[10px] text-emerald-600 font-medium">Verified</span>
              ) : (
                <span className="text-[10px] text-amber-600 font-medium">Unverified</span>
              )}
            </div>
          </div>
        )}

        <div className="space-y-1 border-t pt-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
            className="w-full justify-start text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            {logoutMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <LogOut className="mr-2 h-4 w-4" />
            )}
            Sign Out
          </Button>

          <Link to="/">
            <Button variant="ghost" size="sm" className="w-full justify-start text-muted-foreground">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to Home
            </Button>
          </Link>
        </div>
      </aside>

      {/* Main dashboard content */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b bg-card px-6">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-muted-foreground">EazyDoc SaaS /</span>
            <span className="text-sm font-semibold text-foreground">{roleTitle}</span>
          </div>
          <div className="flex items-center space-x-3">
            {user && (
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-semibold text-foreground">
                  {user.first_name} {user.last_name}
                </span>
                <span className="text-[10px] text-muted-foreground">{user.email}</span>
              </div>
            )}
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">
              {initials}
            </div>
          </div>
        </header>

        {/* Verification banner if unverified */}
        {user && !user.is_verified && (
          <div className="bg-amber-500/10 border-b border-amber-500/20 px-6 py-2.5 flex items-center justify-between text-xs text-amber-800 dark:text-amber-300">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
              <span>
                Your email address is not verified yet. Please check your inbox or visit the verification page.
              </span>
            </div>
            <Link to="/verify-email" className="font-semibold underline hover:text-amber-900">
              Verify Now
            </Link>
          </div>
        )}

        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;
