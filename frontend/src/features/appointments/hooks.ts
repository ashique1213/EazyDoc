import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { appointmentsApi } from "./api";
import type { BookAppointmentPayload, MyAppointmentsParams } from "./types";

export const appointmentKeys = {
  all: ["appointments"] as const,
  my: (params?: MyAppointmentsParams) => ["appointments", "my", params] as const,
  detail: (id?: string) => ["appointments", "detail", id] as const,
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
