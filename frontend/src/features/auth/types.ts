export type UserRole =
  | "SUPER_ADMIN"
  | "CLINIC_OWNER"
  | "STAFF"
  | "DOCTOR"
  | "PATIENT";

export type UserStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED";

export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  role: UserRole;
  status: UserStatus;
  is_verified: boolean;
  created_at?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
  role: "PATIENT" | "DOCTOR" | "CLINIC_OWNER";
}

export interface VerifyEmailPayload {
  token: string;
}

export interface ResendVerificationPayload {
  email: string;
}

export interface ForgotPasswordPayload {
  email: string;
}

export interface ResetPasswordPayload {
  token: string;
  password: string;
}

export interface AuthResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  errors?: Record<string, string[]>;
}

export interface LoginResponseData {
  user: AuthUser;
  tokens?: {
    access: string;
  };
}
