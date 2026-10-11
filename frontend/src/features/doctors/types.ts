export type DoctorVerificationStatus =
  | "DRAFT"
  | "PENDING"
  | "VERIFIED"
  | "REJECTED"
  | "SUSPENDED";

export interface DoctorUserSummary {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

export interface DoctorDocument {
  id: string;
  document_type: "REGISTRATION_CERTIFICATE" | "DEGREE_CERTIFICATE" | "GOVERNMENT_ID" | "OTHER";
  document_type_display: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  uploaded_at: string;
}

export interface Doctor {
  id: string;
  user: DoctorUserSummary;
  registration_number: string;
  normalized_registration_number?: string;
  registration_council: string;
  normalized_registration_council?: string;
  registration_state: string;
  full_name: string;
  specialization: string;
  qualifications: string;
  years_of_experience: number;
  bio: string;
  languages: string;
  profile_photo: string | null;
  verification_status: DoctorVerificationStatus;
  is_verified: boolean;
  verification_notes: string;
  is_eligible_for_clinics: boolean;
  submitted_at: string | null;
  verified_at: string | null;
  verified_by: DoctorUserSummary | null;
  documents?: DoctorDocument[];
  created_at: string;
  updated_at: string;
}

export interface DoctorProfilePayload {
  registration_number: string;
  registration_council: string;
  registration_state?: string;
  full_name: string;
  specialization: string;
  qualifications: string;
  years_of_experience?: number;
  bio?: string;
  languages?: string;
  profile_photo?: File | null;
}

export interface Specialization {
  id: string;
  name: string;
  slug: string;
  description: string;
}

export interface AdminDoctorFilters {
  status?: string;
  search?: string;
  page?: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DoctorRegistrationLookupResult {
  found: boolean;
  doctor_id: string | null;
  full_name: string | null;
  specialization: string | null;
  registration_council: string | null;
  registration_number: string | null;
  is_verified: boolean;
  is_eligible_for_invitation: boolean;
  message?: string | null;
}
