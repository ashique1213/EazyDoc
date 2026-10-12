export type DoctorClinicStatus =
  | "INVITED"
  | "ACTIVE"
  | "REJECTED"
  | "REMOVED"
  | "SUSPENDED";

export interface DoctorSummary {
  id: string;
  full_name: string;
  specialization: string;
  qualifications: string;
  years_of_experience: number;
  registration_number: string;
  registration_council: string;
  profile_photo: string | null;
  is_verified: boolean;
}

export interface ClinicSummary {
  id: string;
  name: string;
  slug: string;
  email: string;
  phone: string;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  pincode: string;
  country: string;
  logo: string | null;
  status: string;
}

export interface DoctorClinic {
  id: string;
  doctor: DoctorSummary;
  clinic: ClinicSummary;
  status: DoctorClinicStatus;
  invited_by: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
  } | null;
  invitation_message: string;
  consultation_fee: string;
  follow_up_fee: string;
  appointment_duration_minutes: number;
  accepted_at: string | null;
  rejected_at: string | null;
  removed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DoctorClinicInvitationPayload {
  doctor_id: string;
  invitation_message?: string;
  consultation_fee?: number | string;
  follow_up_fee?: number | string;
  appointment_duration_minutes?: number;
}

export interface DoctorClinicSettingsPayload {
  consultation_fee?: number | string;
  follow_up_fee?: number | string;
  appointment_duration_minutes?: number;
}
