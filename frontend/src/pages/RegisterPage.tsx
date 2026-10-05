import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function RegisterPage() {
  return (
    <Card className="shadow-lg">
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl font-bold">Create Account</CardTitle>
          <Badge variant="secondary">Day 2 Foundation</Badge>
        </div>
        <CardDescription>
          Join EazyDoc as a Patient, Clinic Owner, or Medical Practitioner.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <label className="text-sm font-medium">First Name</label>
            <Input placeholder="John" disabled />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Last Name</label>
            <Input placeholder="Doe" disabled />
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Email Address</label>
          <Input type="email" placeholder="john@example.com" disabled />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Mobile Phone</label>
          <Input type="tel" placeholder="+91 98765 43210" disabled />
        </div>
        <div className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
          Registration, role selection, and OTP verification scheduled for Day 3.
        </div>
      </CardContent>
      <CardFooter className="flex flex-col space-y-3">
        <Button className="w-full" disabled>
          Register (Available Day 3)
        </Button>
        <div className="text-center text-sm text-muted-foreground">
          Already registered?{" "}
          <Link to="/login" className="font-semibold text-primary hover:underline">
            Sign In
          </Link>
        </div>
      </CardFooter>
    </Card>
  );
}

export default RegisterPage;
