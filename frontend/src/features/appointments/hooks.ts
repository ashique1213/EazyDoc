import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { appointmentsApi } from "./api";
import type {
  BookAppointmentPayload,
  CancelAppointmentPayload,
  MyAppointmentsParams,
  ReportUnavailabilityPayload,
  RescheduleAppointmentPayload,
} from "./types";

export const appointmentKeys = {
  all: ["appointments"] as const,
  my: (params?: MyAppointmentsParams) => ["appointments", "my", params] as const,
  detail: (id?: string) => ["appointments", "detail", id] as const,
  history: (id?: string) => ["appointments", "history", id] as const,
  clinic: (clinicId?: string, params?: unknown) =>
    ["appointments", "clinic", clinicId, params] as const,
  doctor: (params?: unknown) => ["appointments", "doctor", params] as const,
};

export function useCreateAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: BookAppointmentPayload;
      idempotencyKey?: string;
    }) => appointmentsApi.createAppointment(payload, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      queryClient.invalidateQueries({ queryKey: ["discovery", "availability"] });
    },
  });
}

export function useCancelAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      appointmentId,
      payload,
    }: {
      appointmentId: string;
      payload?: CancelAppointmentPayload;
    }) => appointmentsApi.cancelAppointment(appointmentId, payload),
    onSuccess: (_, { appointmentId }) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.history(appointmentId) });
      queryClient.invalidateQueries({ queryKey: ["discovery", "availability"] });
    },
  });
}

export function useRescheduleAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      appointmentId,
      payload,
    }: {
      appointmentId: string;
      payload: RescheduleAppointmentPayload;
    }) => appointmentsApi.rescheduleAppointment(appointmentId, payload),
    onSuccess: (_, { appointmentId }) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.history(appointmentId) });
      queryClient.invalidateQueries({ queryKey: ["discovery", "availability"] });
    },
  });
}

export function useAppointmentHistory(appointmentId?: string) {
  return useQuery({
    queryKey: appointmentKeys.history(appointmentId),
    queryFn: () => {
      if (!appointmentId) throw new Error("Appointment ID is required");
      return appointmentsApi.getAppointmentHistory(appointmentId);
    },
    enabled: Boolean(appointmentId),
  });
}

export function useClinicCancelAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      clinicId,
      appointmentId,
      payload,
    }: {
      clinicId: string;
      appointmentId: string;
      payload?: CancelAppointmentPayload;
    }) => appointmentsApi.clinicCancelAppointment(clinicId, appointmentId, payload),
    onSuccess: (_, { appointmentId, clinicId }) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.history(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.clinic(clinicId) });
      queryClient.invalidateQueries({ queryKey: ["discovery", "availability"] });
    },
  });
}

export function useClinicRescheduleAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      clinicId,
      appointmentId,
      payload,
    }: {
      clinicId: string;
      appointmentId: string;
      payload: RescheduleAppointmentPayload;
    }) => appointmentsApi.clinicRescheduleAppointment(clinicId, appointmentId, payload),
    onSuccess: (_, { appointmentId, clinicId }) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.history(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.clinic(clinicId) });
      queryClient.invalidateQueries({ queryKey: ["discovery", "availability"] });
    },
  });
}

export function useDoctorReportUnavailability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      appointmentId,
      payload,
    }: {
      appointmentId: string;
      payload: ReportUnavailabilityPayload;
    }) => appointmentsApi.doctorReportUnavailability(appointmentId, payload),
    onSuccess: (_, { appointmentId }) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.history(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.doctor() });
      queryClient.invalidateQueries({ queryKey: ["discovery", "availability"] });
    },
  });
}

export function useClinicReportUnavailability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      clinicId,
      appointmentId,
      payload,
    }: {
      clinicId: string;
      appointmentId: string;
      payload: ReportUnavailabilityPayload;
    }) => appointmentsApi.clinicReportUnavailability(clinicId, appointmentId, payload),
    onSuccess: (_, { appointmentId, clinicId }) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.history(appointmentId) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.clinic(clinicId) });
      queryClient.invalidateQueries({ queryKey: ["discovery", "availability"] });
    },
  });
}

export function useMyAppointments(params?: MyAppointmentsParams) {
  return useQuery({
    queryKey: appointmentKeys.my(params),
    queryFn: () => appointmentsApi.getMyAppointments(params),
  });
}

export function useAppointmentDetail(appointmentId?: string) {
  return useQuery({
    queryKey: appointmentKeys.detail(appointmentId),
    queryFn: () => {
      if (!appointmentId) throw new Error("Appointment ID is required");
      return appointmentsApi.getAppointmentDetail(appointmentId);
    },
    enabled: Boolean(appointmentId),
  });
}

export function useClinicAppointments(
  clinicId?: string,
  params?: { doctor_id?: string; status?: string; filter?: string; page?: number }
) {
  return useQuery({
    queryKey: appointmentKeys.clinic(clinicId, params),
    queryFn: () => {
      if (!clinicId) throw new Error("Clinic ID is required");
      return appointmentsApi.getClinicAppointments(clinicId, params);
    },
    enabled: Boolean(clinicId),
  });
}

export function useDoctorAppointments(
  params?: { clinic_id?: string; status?: string; filter?: string; page?: number }
) {
  return useQuery({
    queryKey: appointmentKeys.doctor(params),
    queryFn: () => appointmentsApi.getDoctorAppointments(params),
  });
}

