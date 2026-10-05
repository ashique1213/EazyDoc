import { Link, Outlet } from "react-router-dom";
import { Stethoscope } from "lucide-react";

export function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 p-4">
      <div className="mb-6 flex items-center space-x-2.5">
        <Link to="/" className="flex items-center space-x-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow">
            <Stethoscope className="h-6 w-6" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-foreground">
            Eazy<span className="text-primary">Doc</span>
          </span>
        </Link>
      </div>
      <div className="w-full max-w-md">
        <Outlet />
      </div>
    </div>
  );
}

export default AuthLayout;
