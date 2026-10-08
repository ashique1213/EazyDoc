import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useResetPassword } from "../hooks";
import { AlertCircle, CheckCircle2, KeyRound, Loader2, Lock } from "lucide-react";

export function ResetPasswordForm() {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get("token") || "";

  const [token, setToken] = useState(tokenFromUrl);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  const resetMutation = useResetPassword();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);

    if (!token.trim()) {
      setClientError("Please provide the recovery token from your email.");
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

    resetMutation.mutate({ token: token.trim(), password });
  };

  if (resetMutation.isSuccess) {
    return (
      <Card className="w-full shadow-lg">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold">Password Reset Complete</CardTitle>
          <CardDescription>
            Your account password has been updated securely.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center text-sm text-muted-foreground">
          You can now use your new password to sign into your healthcare portal.
        </CardContent>
        <CardFooter>
          <Link to="/login" className="w-full">
            <Button className="w-full">Sign In with New Password</Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  const serverError =
    resetMutation.error &&
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ((resetMutation.error as any).response?.data?.message ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (resetMutation.error as any).response?.data?.errors?.token?.[0] ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (resetMutation.error as any).response?.data?.errors?.password?.[0] ||
      "Invalid or expired reset token. Please request a new link.");

  return (
    <Card className="w-full shadow-lg">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight text-center">Reset your password</CardTitle>
        <CardDescription className="text-center text-sm">
          Enter your recovery token and choose a new secure password.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {(clientError || serverError) && (
            <div className="flex items-center space-x-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{clientError || serverError}</span>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="resetToken">
              Recovery Token
            </label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="resetToken"
                type="text"
                placeholder="Paste code from email"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="pl-9 font-mono text-sm"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="newPassword">
              New Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="newPassword"
                type="password"
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pl-9"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="confirmNewPassword">
              Confirm New Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="confirmNewPassword"
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
            disabled={resetMutation.isPending}
          >
            {resetMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting password...
              </>
            ) : (
              "Update Password"
            )}
          </Button>

          <Link to="/login" className="text-center text-sm text-muted-foreground hover:text-foreground">
            Cancel and Return to Sign In
          </Link>
        </CardFooter>
      </form>
    </Card>
  );
}

export default ResetPasswordForm;
