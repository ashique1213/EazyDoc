export type ClinicStatus =
  | "DRAFT"
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "SUSPENDED";

export interface ClinicOwnerSummary {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

export interface Clinic {
  id: string;
  name: string;
  slug: string;
  description: string;
  owner: ClinicOwnerSummary;
  email: string;
  phone: string;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  pincode: string;
  country: string;
  logo: string | null;
  status: ClinicStatus;
  verification_notes: string | null;
  timezone: string;
  is_verified: boolean;
  is_publicly_bookable: boolean;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
  approved_by: ClinicOwnerSummary | null;
}

export interface ClinicCreatePayload {
  name: string;
  description?: string;
  email: string;
  phone: string;
  address_line_1: string;
  address_line_2?: string;
  city: string;
  state: string;
  pincode: string;
  country?: string;
  logo?: File | null;
  status?: "DRAFT" | "PENDING";
}

export interface ClinicUpdatePayload {
  name?: string;
  description?: string;
  email?: string;
  phone?: string;
  address_line_1?: string;
  address_line_2?: string;
  city?: string;
  state?: string;
  pincode?: string;
  country?: string;
  logo?: File | null;
  timezone?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AdminClinicFilters {
  status?: string;
  search?: string;
  page?: number;
}
