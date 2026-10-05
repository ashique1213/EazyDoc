export type UserRole =
  | "SUPER_ADMIN"
  | "CLINIC_OWNER"
  | "STAFF"
  | "DOCTOR"
  | "PATIENT";

export interface User {
  id: string;
  email: string;
  phone_number?: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  database: string;
  redis: string;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  meta?: {
    page: number;
    page_size: number;
    total_count: number;
  };
}
