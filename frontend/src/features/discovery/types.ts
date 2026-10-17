export interface PublicClinicLocation {
  doctor_clinic_id: string;
  clinic_id: string;
  clinic_name: string;
  clinic_slug: string;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  pincode: string;
  country: string;
  phone: string;
  email: string;
  logo: string | null;
  timezone: string;
  consultation_fee: string;
  follow_up_fee: string;
  appointment_duration_minutes: number;
}

export interface PublicDoctor {
  id: string;
  full_name: string;
  specialization: string;
  qualifications: string;
  years_of_experience: number;
  languages: string;
  bio: string;
  profile_photo: string | null;
  is_verified: boolean;
  practice_locations: PublicClinicLocation[];
  min_consultation_fee?: string | number | null;
}

export interface PublicClinicDoctor {
  doctor_id: string;
  doctor_clinic_id: string;
  full_name: string;
  specialization: string;
  qualifications: string;
  years_of_experience: number;
  languages: string;
  bio: string;
  profile_photo: string | null;
  is_verified: boolean;
  consultation_fee: string;
  follow_up_fee: string;
  appointment_duration_minutes: number;
}

export interface PublicClinic {
  id: string;
  name: string;
  slug: string;
  description: string;
  email: string;
  phone: string;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  pincode: string;
  country: string;
  logo: string | null;
  timezone: string;
  doctor_count?: number;
  doctors?: PublicClinicDoctor[];
}

export interface AvailabilitySlot {
  schedule_id: string;
  start_time: string;
  end_time: string;
  start_datetime_utc: string;
  end_datetime_utc: string;
  duration_minutes: number;
  is_available: boolean;
  reason: string | null;
}

export interface PublicAvailabilityResponse {
  clinic: {
    id: string;
    name: string;
    timezone: string;
    status: string;
  };
  doctor: {
    id: string;
    full_name: string;
    specialization: string;
    verification_status: string;
  };
  date: string;
  day_of_week: number;
  day_name: string;
  is_eligible: boolean;
  eligibility_error: string | null;
  total_slots: number;
  available_slots_count: number;
  slots: AvailabilitySlot[];
  pricing: {
    consultation_fee: string;
    follow_up_fee: string;
    appointment_duration_minutes: number;
  };
}

export interface Specialization {
  id: string;
  name: string;
  slug: string;
  description?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DoctorSearchParams {
  search?: string;
  specialization?: string;
  city?: string;
  area?: string;
  clinic?: string;
  date?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface ClinicSearchParams {
  search?: string;
  city?: string;
  area?: string;
  service?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}
