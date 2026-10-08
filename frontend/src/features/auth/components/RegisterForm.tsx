import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRegister } from "../hooks";
import { AlertCircle, CheckCircle2, Loader2, Lock, Mail, Phone, Stethoscope, User, Building2 } from "lucide-react";

type RegisterRole = "PATIENT" | "CLINIC_OWNER" | "DOCTOR";

export function RegisterForm() {
  const [role, setRole] = useState<RegisterRole>("PATIENT");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  const registerMutation = useRegister();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);

    if (!firstName.trim() || !lastName.trim() || !email.trim() || !password) {
      setClientError("Please fill out all required fields.");
      return;
    }

    if (password.length < 8) {
      setClientError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setClientError("Passwords do not match.");
      return;
    }

    registerMutation.mutate({
      role,
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      email: email.trim(),
      phone: phone.trim() || undefined,
      password,
    });
  };

  if (registerMutation.isSuccess) {
    return (
      <Card className="w-full shadow-lg">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold">Registration Successful</CardTitle>
          <CardDescription>
            We have sent a verification email to <strong className="text-foreground">{email}</strong>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground text-center">
          <p>
            Please check your inbox and verify your email address to activate all features of your healthcare account.
          </p>
        </CardContent>
        <CardFooter className="flex flex-col space-y-2">
          <Link to="/login" className="w-full">
            <Button className="w-full">Proceed to Sign In</Button>
          </Link>
          <Link to="/verify-email" className="text-xs text-primary hover:underline text-center">
            Enter verification code manually
          </Link>
        </CardFooter>
      </Card>
    );
  }

  const serverError =
    registerMutation.error &&
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ((registerMutation.error as any).response?.data?.message ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (registerMutation.error as any).response?.data?.errors?.email?.[0] ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (registerMutation.error as any).response?.data?.errors?.password?.[0] ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (registerMutation.error as any).response?.data?.errors?.non_field_errors?.[0] ||
      "Registration failed. Please check your details.");

  return (
    <Card className="w-full shadow-lg">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight text-center">Create an account</CardTitle>
        <CardDescription className="text-center text-sm">
          Select your account type to get started
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {/* Role selector tabs */}
          <div className="grid grid-cols-3 gap-2 p-1 bg-muted rounded-xl">
            <button
              type="button"
              onClick={() => setRole("PATIENT")}
              className={`flex flex-col items-center justify-center p-2 rounded-lg text-xs font-medium transition-all ${
                role === "PATIENT"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <User className="h-4 w-4 mb-1" />
              Patient
            </button>
            <button
              type="button"
              onClick={() => setRole("DOCTOR")}
              className={`flex flex-col items-center justify-center p-2 rounded-lg text-xs font-medium transition-all ${
                role === "DOCTOR"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Stethoscope className="h-4 w-4 mb-1" />
              Doctor
            </button>
            <button
              type="button"
              onClick={() => setRole("CLINIC_OWNER")}
              className={`flex flex-col items-center justify-center p-2 rounded-lg text-xs font-medium transition-all ${
                role === "CLINIC_OWNER"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Building2 className="h-4 w-4 mb-1" />
              Clinic Owner
            </button>
          </div>

          {(clientError || serverError) && (
            <div className="flex items-center space-x-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{clientError || serverError}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="firstName">
                First Name
              </label>
              <Input
                id="firstName"
                placeholder="John"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="lastName">
                Last Name
              </label>
              <Input
                id="lastName"
                placeholder="Doe"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium" htmlFor="regEmail">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="regEmail"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-9"
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium" htmlFor="regPhone">
              Phone Number (Optional)
            </label>
            <div className="relative">
              <Phone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="regPhone"
                type="tel"
                placeholder="9876543210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium" htmlFor="regPassword">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="regPassword"
                type="password"
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pl-9"
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Repeat password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="pl-9"
                required
              />
            </div>
          </div>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button
            type="submit"
            className="w-full"
            disabled={registerMutation.isPending}
          >
            {registerMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating account...
              </>
            ) : (
              `Register as ${role === "CLINIC_OWNER" ? "Clinic Owner" : role === "DOCTOR" ? "Doctor" : "Patient"}`
            )}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-primary hover:underline">
              Sign In
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}

export default RegisterForm;
