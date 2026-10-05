import { Link, Outlet } from "react-router-dom";
import { Stethoscope, Building2, UserCircle, LayoutDashboard, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DashboardLayoutProps {
  roleTitle?: string;
}

export function DashboardLayout({ roleTitle = "Dashboard" }: DashboardLayoutProps) {
  return (
    <div className="flex min-h-screen bg-muted/20">
      {/* Sidebar shell */}
      <aside className="hidden w-64 flex-col border-r bg-card p-4 md:flex">
        <Link to="/" className="mb-8 flex items-center space-x-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
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
          <div className="flex items-center space-x-3 rounded-lg bg-primary/10 px-3 py-2 text-sm font-medium text-primary">
            <LayoutDashboard className="h-4 w-4" />
            <span>Overview</span>
          </div>
          <div className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent">
            <Building2 className="h-4 w-4" />
            <span>Clinics</span>
          </div>
          <div className="flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent">
            <UserCircle className="h-4 w-4" />
            <span>Profile</span>
          </div>
        </nav>

        <div className="border-t pt-4">
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
            <div className="h-8 w-8 rounded-full bg-primary/20 text-center leading-8 font-semibold text-primary">
              U
            </div>
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;
