import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useForgotPassword } from "../hooks";
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, Mail } from "lucide-react";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  const forgotMutation = useForgotPassword();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);

    if (!email.trim()) {
      setClientError("Please enter your email address.");
      return;
    }

    forgotMutation.mutate({ email: email.trim() });
  };

  if (forgotMutation.isSuccess) {
    return (
      <Card className="w-full shadow-lg">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold">Check Your Email</CardTitle>
          <CardDescription>
            If an account exists for <strong className="text-foreground">{email}</strong>, you will receive password reset instructions.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center text-sm text-muted-foreground">
          The reset link will expire in 1 hour. Be sure to check your spam folder if you do not see it within a few minutes.
        </CardContent>
        <CardFooter className="flex flex-col space-y-2">
          <Link to="/reset-password" className="w-full">
            <Button variant="outline" className="w-full">
              Enter Reset Code Directly
            </Button>
          </Link>
          <Link to="/login" className="w-full">
            <Button variant="ghost" className="w-full text-muted-foreground">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to Sign In
            </Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="w-full shadow-lg">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight text-center">Forgot password?</CardTitle>
        <CardDescription className="text-center text-sm">
          Enter your registered email address and we will send you a secure recovery link.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {clientError && (
            <div className="flex items-center space-x-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{clientError}</span>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="forgotEmail">
              Registered Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="forgotEmail"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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
            disabled={forgotMutation.isPending}
          >
            {forgotMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending link...
              </>
            ) : (
              "Send Reset Link"
            )}
          </Button>

          <Link to="/login" className="flex items-center text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Sign In
          </Link>
        </CardFooter>
      </form>
    </Card>
  );
}

export default ForgotPasswordForm;
