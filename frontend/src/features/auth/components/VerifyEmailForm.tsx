import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useResendVerification, useVerifyEmail } from "../hooks";
import { AlertCircle, CheckCircle2, KeyRound, Loader2, Mail } from "lucide-react";

export function VerifyEmailForm() {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get("token") || "";

  const [mode, setMode] = useState<"verify" | "resend">("verify");
  const [token, setToken] = useState(tokenFromUrl);
  const [resendEmail, setResendEmail] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  const verifyMutation = useVerifyEmail();
  const resendMutation = useResendVerification();

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);

    if (!token.trim()) {
      setClientError("Please enter your verification code.");
      return;
    }

    verifyMutation.mutate({ token: token.trim() });
  };

  const handleResend = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);

    if (!resendEmail.trim()) {
      setClientError("Please enter your registered email address.");
      return;
    }

    resendMutation.mutate({ email: resendEmail.trim() });
  };

  if (verifyMutation.isSuccess) {
    return (
      <Card className="w-full shadow-lg">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold">Email Verified</CardTitle>
          <CardDescription>
            Your account is now verified and active.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center text-sm text-muted-foreground">
          Thank you for confirming your email. You have full access to your healthcare features.
        </CardContent>
        <CardFooter>
          <Link to="/login" className="w-full">
            <Button className="w-full">Sign In to Continue</Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  const serverError =
    verifyMutation.error &&
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ((verifyMutation.error as any).response?.data?.message ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (verifyMutation.error as any).response?.data?.errors?.token?.[0] ||
      "Invalid or expired verification code.");

  const resendServerError =
    resendMutation.error &&
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ((resendMutation.error as any).response?.data?.message ||
      "Failed to request verification email. Try again later.");

  return (
    <Card className="w-full shadow-lg">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight text-center">
          {mode === "verify" ? "Verify Email Address" : "Resend Verification Code"}
        </CardTitle>
        <CardDescription className="text-center text-sm">
          {mode === "verify"
            ? "Enter the code sent to your email to verify your account"
            : "Enter your registered email address to receive a new code"}
        </CardDescription>
      </CardHeader>

      <div className="px-6">
        <div className="grid grid-cols-2 gap-2 p-1 bg-muted rounded-xl mb-4">
          <button
            type="button"
            onClick={() => {
              setMode("verify");
              setClientError(null);
            }}
            className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
              mode === "verify"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Enter Code
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("resend");
              setClientError(null);
            }}
            className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
              mode === "resend"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Resend Email
          </button>
        </div>
      </div>

      {mode === "verify" ? (
        <form onSubmit={handleVerify}>
          <CardContent className="space-y-4">
            {(clientError || serverError) && (
              <div className="flex items-center space-x-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{clientError || serverError}</span>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium leading-none" htmlFor="verifyToken">
                Verification Code / Token
              </label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="verifyToken"
                  type="text"
                  placeholder="Paste verification token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  className="pl-9 font-mono text-sm"
                  required
                />
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full"
              disabled={verifyMutation.isPending}
            >
              {verifyMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                "Verify Email"
              )}
            </Button>

            <Link to="/login" className="text-sm text-center text-muted-foreground hover:text-foreground">
              Back to Sign In
            </Link>
          </CardFooter>
        </form>
      ) : (
        <form onSubmit={handleResend}>
          <CardContent className="space-y-4">
            {resendMutation.isSuccess && (
              <div className="flex items-center space-x-2 rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-600">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>If an account exists, a new verification link has been sent.</span>
              </div>
            )}

            {(clientError || resendServerError) && (
              <div className="flex items-center space-x-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{clientError || resendServerError}</span>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium leading-none" htmlFor="resendEmail">
                Registered Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="resendEmail"
                  type="email"
                  placeholder="name@example.com"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
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
              disabled={resendMutation.isPending}
            >
              {resendMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending link...
                </>
              ) : (
                "Send Verification Email"
              )}
            </Button>

            <button
              type="button"
              onClick={() => setMode("verify")}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Have a code already? Verify now
            </button>
          </CardFooter>
        </form>
      )}
    </Card>
  );
}

export default VerifyEmailForm;
