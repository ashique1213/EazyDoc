export type AppointmentStatus =
  | "PENDING_CONFIRMATION"
  | "CONFIRMED"
  | "CANCELLED"
  | "COMPLETED"
  | "NO_SHOW"
  | "RESCHEDULE_REQUIRED";

export interface AppointmentDoctorSummary {
  id: string;
  full_name: string;
  specialization: string;
  qualifications: string;
  profile_photo: string | null;
}

export interface AppointmentClinicSummary {
  id: string;
  name: string;
  slug: string;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  timezone: string;
}

export interface AppointmentPatientSummary {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
}

export interface Appointment {
  id: string;
  booking_reference: string;
  status: AppointmentStatus;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  consultation_fee: string;
  currency: string;
  patient_note: string;
  cancellation_reason?: string;
  cancelled_at?: string | null;
  reschedule_required?: boolean;
  cancellation_cutoff?: string | null;
  is_cancellable?: boolean;
  is_reschedulable?: boolean;
  doctor: AppointmentDoctorSummary;
  clinic: AppointmentClinicSummary;
  patient: AppointmentPatientSummary;
  created_at: string;
  updated_at: string;
}

export interface AppointmentListItem {
  id: string;
  booking_reference: string;
  status: AppointmentStatus;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  consultation_fee: string;
  currency: string;
  patient_note: string;
  cancellation_reason?: string;
  cancelled_at?: string | null;
  reschedule_required?: boolean;
  cancellation_cutoff?: string | null;
  is_cancellable?: boolean;
  is_reschedulable?: boolean;
  doctor_id: string;
  doctor_name: string;
  specialization: string;
  clinic_id: string;
  clinic_name: string;
  clinic_city: string;
  clinic_timezone: string;
  created_at: string;
}

export interface AppointmentHistoryItem {
  id: string;
  appointment_id: string;
  event_type: string;
  previous_status: string;
  new_status: string;
  previous_start_at: string | null;
  previous_end_at: string | null;
  new_start_at: string | null;
  new_end_at: string | null;
  actor_id: string | null;
  actor_name: string;
  actor_role: string;
  reason: string;
  is_exception: boolean;
  created_at: string;
}

export interface CancelAppointmentPayload {
  reason?: string;
}

export interface RescheduleAppointmentPayload {
  start_at?: string;
  date?: string;
  time?: string;
  reason?: string;
}

export interface ReportUnavailabilityPayload {
  reason: string;
  action?: "RESCHEDULE_REQUIRED" | "CANCEL";
}

export interface BookAppointmentPayload {
  clinic_id: string;
  doctor_id: string;
  start_at: string;
  patient_note?: string;
  idempotency_key?: string;
}

export interface MyAppointmentsParams {
  filter?: "upcoming" | "past";
  status?: string;
  date?: string;
  page?: number;
}

