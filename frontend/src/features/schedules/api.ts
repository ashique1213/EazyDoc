import { apiClient } from "@/services/api";
import type {
  AvailabilityResponse,
  BlockedSlot,
  BlockedSlotPayload,
  ConflictCheckPayload,
  ConflictCheckResponse,
  DoctorMasterScheduleResponse,
  DoctorSchedule,
  DoctorUnavailability,
  SchedulePayload,
  UnavailabilityPayload,
} from "./types";

// ==========================================
// Recurring Schedules API
// ==========================================

export const getSchedules = async (params?: {
  clinic_id?: string;
  doctor_clinic_id?: string;
  doctor_id?: string;
  day_of_week?: number;
  is_active?: boolean;
}): Promise<DoctorSchedule[]> => {
  const response = await apiClient.get<DoctorSchedule[]>("/schedules/", { params });
  return response.data;
};

export const createSchedule = async (payload: SchedulePayload): Promise<DoctorSchedule> => {
  const response = await apiClient.post<DoctorSchedule>("/schedules/", payload);
  return response.data;
};

export const updateSchedule = async (
  scheduleId: string,
  payload: Partial<SchedulePayload>
): Promise<DoctorSchedule> => {
  const response = await apiClient.put<DoctorSchedule>(`/schedules/${scheduleId}/`, payload);
  return response.data;
};

export const deactivateSchedule = async (
  scheduleId: string
): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete<{ success: boolean; message: string }>(
    `/schedules/${scheduleId}/`
  );
  return response.data;
};

export const checkScheduleConflict = async (
  payload: ConflictCheckPayload
): Promise<ConflictCheckResponse> => {
  const response = await apiClient.post<ConflictCheckResponse>("/schedules/check-conflict/", payload);
  return response.data;
};

// ==========================================
// Doctor Leaves / Unavailability API
// ==========================================

export const getDoctorUnavailabilities = async (params?: {
  doctor_id?: string;
  clinic_id?: string;
}): Promise<DoctorUnavailability[]> => {
  const response = await apiClient.get<DoctorUnavailability[]>("/schedules/unavailability/", { params });
  return response.data;
};

export const createDoctorUnavailability = async (
  payload: UnavailabilityPayload
): Promise<DoctorUnavailability> => {
  const response = await apiClient.post<DoctorUnavailability>("/schedules/unavailability/", payload);
  return response.data;
};

export const deleteDoctorUnavailability = async (
  id: string
): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete<{ success: boolean; message: string }>(
    `/schedules/unavailability/${id}/`
  );
  return response.data;
};

// ==========================================
// Blocked Slots API
// ==========================================

export const getBlockedSlots = async (params?: {
  doctor_clinic_id?: string;
  date?: string;
}): Promise<BlockedSlot[]> => {
  const response = await apiClient.get<BlockedSlot[]>("/schedules/blocked-slots/", { params });
  return response.data;
};

export const createBlockedSlot = async (
  payload: BlockedSlotPayload
): Promise<BlockedSlot> => {
  const response = await apiClient.post<BlockedSlot>("/schedules/blocked-slots/", payload);
  return response.data;
};

export const deleteBlockedSlot = async (
  id: string
): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete<{ success: boolean; message: string }>(
    `/schedules/blocked-slots/${id}/`
  );
  return response.data;
};

// ==========================================
// Real-Time Availability & Slot Engine API
// ==========================================

export const getAvailabilitySlots = async (
  doctorClinicId: string,
  targetDate: string
): Promise<AvailabilityResponse> => {
  const response = await apiClient.get<AvailabilityResponse>("/schedules/availability/", {
    params: {
      doctor_clinic_id: doctorClinicId,
      date: targetDate,
    },
  });
  return response.data;
};

export const getDoctorMasterSchedule = async (): Promise<DoctorMasterScheduleResponse> => {
  const response = await apiClient.get<DoctorMasterScheduleResponse>("/schedules/master-schedule/");
  return response.data;
};
