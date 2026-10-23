import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "./api";

export const ADMIN_QUERY_KEYS = {
  dashboardSummary: (params?: Record<string, unknown>) => ["admin", "dashboard", "summary", params] as const,
  appointmentsTrend: (params?: Record<string, unknown>) => ["admin", "dashboard", "appointments-trend", params] as const,
  financialSummary: (params?: Record<string, unknown>) => ["admin", "dashboard", "financial-summary", params] as const,
  users: (params?: Record<string, unknown>) => ["admin", "users", params] as const,
  userDetail: (id: string) => ["admin", "users", id] as const,
  appointments: (params?: Record<string, unknown>) => ["admin", "appointments", params] as const,
  appointmentDetail: (id: string) => ["admin", "appointments", id] as const,
  appointmentHistory: (id: string) => ["admin", "appointments", id, "history"] as const,
  payments: (params?: Record<string, unknown>) => ["admin", "payments", params] as const,
  commissions: (params?: Record<string, unknown>) => ["admin", "commissions", params] as const,
  commissionSettings: () => ["admin", "settings", "commission"] as const,
  auditLogs: (params?: Record<string, unknown>) => ["admin", "audit-logs", params] as const,
};

// Dashboard
export const useAdminDashboardSummary = (params?: { clinic_id?: string; date_from?: string; date_to?: string }) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.dashboardSummary(params),
    queryFn: () => adminApi.getDashboardSummary(params),
  });
};

export const useAdminAppointmentsTrend = (params?: { days?: number; clinic_id?: string }) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.appointmentsTrend(params),
    queryFn: () => adminApi.getAppointmentsTrend(params),
  });
};

export const useAdminFinancialSummary = (params?: { days?: number; clinic_id?: string }) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.financialSummary(params),
    queryFn: () => adminApi.getFinancialSummary(params),
  });
};

// Users
export const useAdminUsers = (params?: { role?: string; status?: string; search?: string; page?: number }) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.users(params),
    queryFn: () => adminApi.getUsers(params),
  });
};

export const useAdminUserDetail = (userId: string) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.userDetail(userId),
    queryFn: () => adminApi.getUserDetail(userId),
    enabled: Boolean(userId),
  });
};

export const useAdminActivateUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => adminApi.activateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
    },
  });
};

export const useAdminDeactivateUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => adminApi.deactivateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
    },
  });
};

export const useAdminSuspendUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason?: string }) => adminApi.suspendUser(userId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
    },
  });
};

// Appointments
export const useAdminAppointments = (params?: {
  clinic_id?: string;
  doctor_id?: string;
  status?: string;
  payment_status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
}) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.appointments(params),
    queryFn: () => adminApi.getAppointments(params),
  });
};

export const useAdminAppointmentDetail = (appointmentId: string) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.appointmentDetail(appointmentId),
    queryFn: () => adminApi.getAppointmentDetail(appointmentId),
    enabled: Boolean(appointmentId),
  });
};

export const useAdminAppointmentHistory = (appointmentId: string) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.appointmentHistory(appointmentId),
    queryFn: () => adminApi.getAppointmentHistory(appointmentId),
    enabled: Boolean(appointmentId),
  });
};

export const useAdminCancelAppointment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ appointmentId, reason }: { appointmentId: string; reason: string }) =>
      adminApi.cancelAppointment(appointmentId, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "appointments"] });
      queryClient.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.appointmentHistory(variables.appointmentId) });
      queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
    },
  });
};

// Payments & Commissions
export const useAdminPayments = (params?: {
  status?: string;
  clinic_id?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
}) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.payments(params),
    queryFn: () => adminApi.getPayments(params),
  });
};

export const useAdminCommissions = (params?: {
  status?: string;
  clinic_id?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
}) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.commissions(params),
    queryFn: () => adminApi.getCommissions(params),
  });
};

export const useAdminCommissionSettings = () => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.commissionSettings(),
    queryFn: () => adminApi.getCommissionSettings(),
  });
};

export const useUpdateAdminCommissionSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { default_rate?: string | number; clinic_id?: string | null; clinic_rate?: string | number | null; reason?: string }) =>
      adminApi.updateCommissionSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.commissionSettings() });
      queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
    },
  });
};

// Audit Logs
export const useAdminAuditLogs = (params?: {
  action?: string;
  resource_type?: string;
  clinic_id?: string;
  actor_id?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
}) => {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.auditLogs(params),
    queryFn: () => adminApi.getAuditLogs(params),
  });
};
