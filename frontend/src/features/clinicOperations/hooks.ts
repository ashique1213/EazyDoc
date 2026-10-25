import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  completeClinicAppointment,
  confirmClinicAppointment,
  createClinicClosure,
  createClinicStaff,
  deleteClinicClosure,
  deleteClinicStaff,
  getClinicAppointmentDetail,
  getClinicAppointments,
  getClinicCalendar,
  getClinicClosures,
  getClinicDashboardSummary,
  getClinicDashboardTrends,
  getClinicFinancePayments,
  getClinicFinanceSummary,
  getClinicManagementProfile,
  getClinicStaff,
  markNoShowClinicAppointment,
  previewClinicClosure,
  updateClinicManagementProfile,
  updateClinicStaff,
} from "./api";
import type {
  ClinicClosureCreatePayload,
  ClinicStaffCreatePayload,
  ClinicStaffUpdatePayload,
} from "./types";
import type { ClinicUpdatePayload } from "@/features/clinics";

// Dashboard Overview
export const useClinicDashboardSummary = (
  clinicId: string,
  params?: { period?: string; from_date?: string; to_date?: string }
) => {
  return useQuery({
    queryKey: ["clinic-dashboard-summary", clinicId, params],
    queryFn: () => getClinicDashboardSummary(clinicId, params),
    enabled: !!clinicId,
  });
};

export const useClinicDashboardTrends = (
  clinicId: string,
  params?: { period?: string; from_date?: string; to_date?: string }
) => {
  return useQuery({
    queryKey: ["clinic-dashboard-trends", clinicId, params],
    queryFn: () => getClinicDashboardTrends(clinicId, params),
    enabled: !!clinicId,
  });
};

// Clinic Management Profile
export const useClinicManagementProfile = (clinicId: string) => {
  return useQuery({
    queryKey: ["clinic-management-profile", clinicId],
    queryFn: () => getClinicManagementProfile(clinicId),
    enabled: !!clinicId,
  });
};

export const useUpdateClinicManagementProfile = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClinicUpdatePayload) => updateClinicManagementProfile(clinicId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-management-profile", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["my-clinics"] });
    },
  });
};

// Staff
export const useClinicStaff = (clinicId: string) => {
  return useQuery({
    queryKey: ["clinic-staff", clinicId],
    queryFn: () => getClinicStaff(clinicId),
    enabled: !!clinicId,
  });
};

export const useCreateClinicStaff = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClinicStaffCreatePayload) => createClinicStaff(clinicId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-staff", clinicId] });
    },
  });
};

export const useUpdateClinicStaff = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ staffId, payload }: { staffId: string; payload: ClinicStaffUpdatePayload }) =>
      updateClinicStaff(clinicId, staffId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-staff", clinicId] });
    },
  });
};

export const useDeleteClinicStaff = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (staffId: string) => deleteClinicStaff(clinicId, staffId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-staff", clinicId] });
    },
  });
};

// Closures
export const useClinicClosures = (clinicId: string) => {
  return useQuery({
    queryKey: ["clinic-closures", clinicId],
    queryFn: () => getClinicClosures(clinicId),
    enabled: !!clinicId,
  });
};

export const usePreviewClinicClosure = (clinicId: string) => {
  return useMutation({
    mutationFn: (payload: { start_date: string; end_date: string; reason?: string }) =>
      previewClinicClosure(clinicId, payload),
  });
};

export const useCreateClinicClosure = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClinicClosureCreatePayload) => createClinicClosure(clinicId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-closures", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic-calendar", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic-appointments", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic-dashboard-summary", clinicId] });
    },
  });
};

export const useDeleteClinicClosure = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (closureId: string) => deleteClinicClosure(clinicId, closureId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-closures", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic-calendar", clinicId] });
    },
  });
};

// Calendar
export const useClinicCalendar = (
  clinicId: string,
  params?: { start_date?: string; end_date?: string; doctor_id?: string }
) => {
  return useQuery({
    queryKey: ["clinic-calendar", clinicId, params],
    queryFn: () => getClinicCalendar(clinicId, params),
    enabled: !!clinicId,
  });
};

// Clinic Appointments
export const useClinicAppointments = (
  clinicId: string,
  params?: {
    doctor_id?: string;
    status?: string;
    date?: string;
    from_date?: string;
    to_date?: string;
    filter?: string;
    requires_attention?: boolean;
    search?: string;
    page?: number;
  }
) => {
  return useQuery({
    queryKey: ["clinic-appointments", clinicId, params],
    queryFn: () => getClinicAppointments(clinicId, params),
    enabled: !!clinicId,
  });
};

export const useClinicAppointmentDetail = (clinicId: string, appointmentId: string) => {
  return useQuery({
    queryKey: ["clinic-appointment-detail", clinicId, appointmentId],
    queryFn: () => getClinicAppointmentDetail(clinicId, appointmentId),
    enabled: !!clinicId && !!appointmentId,
  });
};

export const useConfirmClinicAppointment = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: string) => confirmClinicAppointment(clinicId, appointmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-appointments", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic-dashboard-summary", clinicId] });
    },
  });
};

export const useCompleteClinicAppointment = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: string) => completeClinicAppointment(clinicId, appointmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-appointments", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic-dashboard-summary", clinicId] });
    },
  });
};

export const useMarkNoShowClinicAppointment = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: string) => markNoShowClinicAppointment(clinicId, appointmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinic-appointments", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinic-dashboard-summary", clinicId] });
    },
  });
};

// Finance
export const useClinicFinanceSummary = (
  clinicId: string,
  params?: { period?: string; from_date?: string; to_date?: string }
) => {
  return useQuery({
    queryKey: ["clinic-finance-summary", clinicId, params],
    queryFn: () => getClinicFinanceSummary(clinicId, params),
    enabled: !!clinicId,
  });
};

export const useClinicFinancePayments = (
  clinicId: string,
  params?: { status?: string; search?: string; page?: number; page_size?: number }
) => {
  return useQuery({
    queryKey: ["clinic-finance-payments", clinicId, params],
    queryFn: () => getClinicFinancePayments(clinicId, params),
    enabled: !!clinicId,
  });
};
