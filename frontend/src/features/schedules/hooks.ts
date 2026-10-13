import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  checkScheduleConflict,
  createBlockedSlot,
  createDoctorUnavailability,
  createSchedule,
  deactivateSchedule,
  deleteBlockedSlot,
  deleteDoctorUnavailability,
  getAvailabilitySlots,
  getBlockedSlots,
  getDoctorMasterSchedule,
  getDoctorUnavailabilities,
  getSchedules,
  updateSchedule,
} from "./api";
import type {
  BlockedSlotPayload,
  ConflictCheckPayload,
  SchedulePayload,
  UnavailabilityPayload,
} from "./types";

export const SCHEDULE_KEYS = {
  all: ["schedules"] as const,
  lists: () => [...SCHEDULE_KEYS.all, "list"] as const,
  list: (filters: Record<string, unknown>) => [...SCHEDULE_KEYS.lists(), filters] as const,
  master: () => [...SCHEDULE_KEYS.all, "master"] as const,
  unavailability: (filters?: Record<string, unknown>) => ["unavailability", filters] as const,
  blockedSlots: (filters?: Record<string, unknown>) => ["blocked-slots", filters] as const,
  availability: (dcId: string, date: string) => ["availability", dcId, date] as const,
};

// ==========================================
// Schedule Query & Mutation Hooks
// ==========================================

export const useSchedules = (params?: {
  clinic_id?: string;
  doctor_clinic_id?: string;
  doctor_id?: string;
  day_of_week?: number;
  is_active?: boolean;
}) => {
  return useQuery({
    queryKey: SCHEDULE_KEYS.list(params || {}),
    queryFn: () => getSchedules(params),
  });
};

export const useCreateSchedule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SchedulePayload) => createSchedule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SCHEDULE_KEYS.all });
    },
  });
};

export const useUpdateSchedule = (scheduleId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<SchedulePayload>) => updateSchedule(scheduleId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SCHEDULE_KEYS.all });
    },
  });
};

export const useDeactivateSchedule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scheduleId: string) => deactivateSchedule(scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SCHEDULE_KEYS.all });
    },
  });
};

export const useCheckConflict = () => {
  return useMutation({
    mutationFn: (payload: ConflictCheckPayload) => checkScheduleConflict(payload),
  });
};

// ==========================================
// Doctor Leaves / Unavailability Hooks
// ==========================================

export const useDoctorUnavailabilities = (params?: { doctor_id?: string; clinic_id?: string }) => {
  return useQuery({
    queryKey: SCHEDULE_KEYS.unavailability(params),
    queryFn: () => getDoctorUnavailabilities(params),
  });
};

export const useCreateUnavailability = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UnavailabilityPayload) => createDoctorUnavailability(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unavailability"] });
      queryClient.invalidateQueries({ queryKey: ["availability"] });
    },
  });
};

export const useDeleteUnavailability = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDoctorUnavailability(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unavailability"] });
      queryClient.invalidateQueries({ queryKey: ["availability"] });
    },
  });
};

// ==========================================
// Blocked Slots Hooks
// ==========================================

export const useBlockedSlots = (params?: { doctor_clinic_id?: string; date?: string }) => {
  return useQuery({
    queryKey: SCHEDULE_KEYS.blockedSlots(params),
    queryFn: () => getBlockedSlots(params),
  });
};

export const useCreateBlockedSlot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BlockedSlotPayload) => createBlockedSlot(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["blocked-slots"] });
      queryClient.invalidateQueries({ queryKey: ["availability"] });
    },
  });
};

export const useDeleteBlockedSlot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteBlockedSlot(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["blocked-slots"] });
      queryClient.invalidateQueries({ queryKey: ["availability"] });
    },
  });
};

// ==========================================
// Availability Engine Hooks
// ==========================================

export const useAvailabilitySlots = (doctorClinicId: string, date: string, enabled = true) => {
  return useQuery({
    queryKey: SCHEDULE_KEYS.availability(doctorClinicId, date),
    queryFn: () => getAvailabilitySlots(doctorClinicId, date),
    enabled: Boolean(doctorClinicId && date && enabled),
  });
};

export const useDoctorMasterSchedule = () => {
  return useQuery({
    queryKey: SCHEDULE_KEYS.master(),
    queryFn: () => getDoctorMasterSchedule(),
  });
};
