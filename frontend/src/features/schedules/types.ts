export type WeekdayNumber = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export const WEEKDAY_LABELS: Record<WeekdayNumber, string> = {
  0: "Monday",
  1: "Tuesday",
  2: "Wednesday",
  3: "Thursday",
  4: "Friday",
  5: "Saturday",
  6: "Sunday",
};

export const WEEKDAY_SHORT_LABELS: Record<WeekdayNumber, string> = {
  0: "Mon",
  1: "Tue",
  2: "Wed",
  3: "Thu",
  4: "Fri",
  5: "Sat",
  6: "Sun",
};

export interface DoctorSchedule {
  id: string;
  doctor_clinic: string;
  doctor_id: string;
  doctor_name: string;
  doctor_specialization: string;
  clinic_id: string;
  clinic_name: string;
  clinic_timezone: string;
  day_of_week: WeekdayNumber;
  weekday_name: string;
  start_time: string; // "HH:MM:SS" or "HH:MM"
  end_time: string;
  effective_from: string | null;
  effective_until: string | null;
  slot_duration_minutes: number | null;
  effective_slot_duration: number;
  buffer_minutes: number;
  max_patients_per_slot: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SchedulePayload {
  doctor_clinic: string;
  day_of_week: WeekdayNumber;
  start_time: string; // "HH:MM"
  end_time: string;   // "HH:MM"
  effective_from?: string | null;
  effective_until?: string | null;
  slot_duration_minutes?: number | null;
  buffer_minutes?: number;
  max_patients_per_slot?: number;
  is_active?: boolean;
}

export interface ConflictDetails {
  conflict_type: "SAME_CLINIC_OVERLAP" | "CROSS_CLINIC_OVERLAP" | "TRAVEL_BUFFER_VIOLATION" | "INVALID_INTERVAL";
  message: string;
  conflicting_clinic_id?: string;
  conflicting_clinic_name?: string;
  day_of_week?: WeekdayNumber;
  start_time?: string;
  end_time?: string;
  schedule_id?: string;
  required_buffer_minutes?: number;
  actual_gap_minutes?: number;
}

export interface ConflictCheckPayload {
  doctor_clinic: string;
  day_of_week: WeekdayNumber;
  start_time: string;
  end_time: string;
  buffer_minutes?: number;
  exclude_schedule_id?: string | null;
}

export interface ConflictCheckResponse {
  has_conflict: boolean;
  conflict: ConflictDetails | null;
}

export type UnavailabilityReason =
  | "SICK_LEAVE"
  | "EMERGENCY"
  | "CONFERENCE"
  | "PERSONAL"
  | "CLINIC_CLOSURE"
  | "OTHER";

export interface DoctorUnavailability {
  id: string;
  doctor: string;
  doctor_name: string;
  clinic: string | null;
  clinic_name: string | null;
  start_datetime: string;
  end_datetime: string;
  reason: UnavailabilityReason;
  reason_display: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface UnavailabilityPayload {
  doctor?: string;
  clinic?: string | null;
  start_datetime: string;
  end_datetime: string;
  reason: UnavailabilityReason;
  notes?: string;
}

export interface BlockedSlot {
  id: string;
  doctor_clinic: string;
  doctor_name: string;
  clinic_name: string;
  date: string;
  start_time: string;
  end_time: string | null;
  reason: string;
  created_at: string;
  updated_at: string;
}

export interface BlockedSlotPayload {
  doctor_clinic: string;
  date: string;
  start_time: string;
  end_time?: string;
  reason?: string;
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

export interface AvailabilityResponse {
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
  day_of_week: WeekdayNumber;
  day_name: string;
  is_eligible: boolean;
  eligibility_error: string | null;
  total_slots: number;
  available_slots_count: number;
  slots: AvailabilitySlot[];
}

export interface DayShiftsGroup {
  day_of_week: WeekdayNumber;
  day_name: string;
  shifts: DoctorSchedule[];
}

export interface DoctorMasterScheduleResponse {
  doctor: {
    id: string;
    full_name: string;
    specialization: string;
  };
  total_active_shifts: number;
  weekly_schedule: DayShiftsGroup[];
}
