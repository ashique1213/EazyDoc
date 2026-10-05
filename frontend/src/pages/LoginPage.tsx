import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function LoginPage() {
  return (
    <Card className="shadow-lg">
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl font-bold">Sign In</CardTitle>
          <Badge variant="secondary">Day 2 Foundation</Badge>
        </div>
        <CardDescription>
          Enter your email and password to access your EazyDoc account.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">Email Address</label>
          <Input type="email" placeholder="doctor@eazydoc.com" disabled />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">Password</label>
          <Input type="password" placeholder="••••••••" disabled />
        </div>
        <div className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
          Authentication and JWT session flow will be implemented in Day 3.
        </div>
      </CardContent>
      <CardFooter className="flex flex-col space-y-3">
        <Button className="w-full" disabled>
          Sign In (Available Day 3)
        </Button>
        <div className="text-center text-sm text-muted-foreground">
          Don't have an account?{" "}
          <Link to="/register" className="font-semibold text-primary hover:underline">
            Register here
          </Link>
        </div>
      </CardFooter>
    </Card>
  );
}

export default LoginPage;
