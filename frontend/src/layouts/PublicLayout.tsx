import { Link, Outlet } from "react-router-dom";
import { Stethoscope, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-8">
          <Link to="/" className="flex items-center space-x-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Stethoscope className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold tracking-tight text-foreground">
              Eazy<span className="text-primary">Doc</span>
            </span>
          </Link>

          <nav className="hidden items-center space-x-6 text-sm font-medium md:flex">
            <Link to="/" className="text-muted-foreground transition hover:text-foreground">
              Find Doctors
            </Link>
            <Link to="/clinic" className="text-muted-foreground transition hover:text-foreground">
              For Clinics
            </Link>
            <Link to="/doctor" className="text-muted-foreground transition hover:text-foreground">
              For Doctors
            </Link>
            <Link to="/admin" className="text-muted-foreground transition hover:text-foreground">
              Platform Admin
            </Link>
          </nav>

          <div className="flex items-center space-x-3">
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link to="/register">
              <Button size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t bg-muted/40 py-8 text-sm text-muted-foreground">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-8">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>&copy; {new Date().getFullYear()} EazyDoc Healthcare SaaS. All rights reserved.</span>
          </div>
          <div className="flex space-x-6">
            <Link to="/" className="hover:underline">Privacy Policy</Link>
            <Link to="/" className="hover:underline">Terms of Service</Link>
            <Link to="/" className="hover:underline">Support</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default PublicLayout;
