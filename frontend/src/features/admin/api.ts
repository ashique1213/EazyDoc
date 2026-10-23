import apiClient from "@/services/api";
import type {
  AdminAppointment,
  AdminAppointmentHistory,
  AdminAuditLog,
  AdminCommissionRecord,
  AdminCommissionSettingsData,
  AdminPayment,
  AdminUser,
  AppointmentTrendPoint,
  DashboardSummaryData,
  FinancialSummaryData,
  PaginatedResponse,
} from "./types";

export const adminApi = {
  // Dashboard & Analytics
  getDashboardSummary: async (params?: { clinic_id?: string; date_from?: string; date_to?: string }): Promise<DashboardSummaryData> => {
    const response = await apiClient.get<{ success: boolean; data: DashboardSummaryData }>("/admin/dashboard/summary/", { params });
    return response.data.data;
  },

  getAppointmentsTrend: async (params?: { days?: number; clinic_id?: string }): Promise<AppointmentTrendPoint[]> => {
    const response = await apiClient.get<{ success: boolean; data: AppointmentTrendPoint[] }>("/admin/dashboard/appointments-trend/", { params });
    return response.data.data;
  },

  getFinancialSummary: async (params?: { days?: number; clinic_id?: string }): Promise<FinancialSummaryData> => {
    const response = await apiClient.get<{ success: boolean; data: FinancialSummaryData }>("/admin/dashboard/financial-summary/", { params });
    return response.data.data;
  },

  // User Management
  getUsers: async (params?: { role?: string; status?: string; search?: string; page?: number }): Promise<PaginatedResponse<AdminUser>> => {
    const response = await apiClient.get<PaginatedResponse<AdminUser>>("/admin/users/", { params });
    return response.data;
  },

  getUserDetail: async (userId: string): Promise<AdminUser> => {
    const response = await apiClient.get<{ success: boolean; data: AdminUser }>(`/admin/users/${userId}/`);
    return response.data.data;
  },

  activateUser: async (userId: string): Promise<AdminUser> => {
    const response = await apiClient.post<{ success: boolean; data: AdminUser }>(`/admin/users/${userId}/activate/`);
    return response.data.data;
  },

  deactivateUser: async (userId: string): Promise<AdminUser> => {
    const response = await apiClient.post<{ success: boolean; data: AdminUser }>(`/admin/users/${userId}/deactivate/`);
    return response.data.data;
  },

  suspendUser: async (userId: string, reason?: string): Promise<AdminUser> => {
    const response = await apiClient.post<{ success: boolean; data: AdminUser }>(`/admin/users/${userId}/suspend/`, { reason });
    return response.data.data;
  },

  // Appointments
  getAppointments: async (params?: {
    clinic_id?: string;
    doctor_id?: string;
    status?: string;
    payment_status?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResponse<AdminAppointment>> => {
    const response = await apiClient.get<PaginatedResponse<AdminAppointment>>("/admin/appointments/", { params });
    return response.data;
  },

  getAppointmentDetail: async (appointmentId: string): Promise<AdminAppointment> => {
    const response = await apiClient.get<{ success: boolean; data: AdminAppointment }>(`/admin/appointments/${appointmentId}/`);
    return response.data.data;
  },

  getAppointmentHistory: async (appointmentId: string): Promise<AdminAppointmentHistory[]> => {
    const response = await apiClient.get<{ success: boolean; data: AdminAppointmentHistory[] }>(`/admin/appointments/${appointmentId}/history/`);
    return response.data.data;
  },

  cancelAppointment: async (appointmentId: string, reason: string): Promise<AdminAppointment> => {
    const response = await apiClient.post<{ success: boolean; data: AdminAppointment }>(`/admin/appointments/${appointmentId}/cancel/`, { reason });
    return response.data.data;
  },

  // Finance & Payments
  getPayments: async (params?: {
    status?: string;
    clinic_id?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResponse<AdminPayment>> => {
    const response = await apiClient.get<PaginatedResponse<AdminPayment>>("/admin/payments/", { params });
    return response.data;
  },

  getCommissions: async (params?: {
    status?: string;
    clinic_id?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
  }): Promise<PaginatedResponse<AdminCommissionRecord>> => {
    const response = await apiClient.get<PaginatedResponse<AdminCommissionRecord>>("/admin/commissions/", { params });
    return response.data;
  },

  getCommissionSettings: async (): Promise<AdminCommissionSettingsData> => {
    const response = await apiClient.get<{ success: boolean; data: AdminCommissionSettingsData }>("/admin/settings/commission/");
    return response.data.data;
  },

  updateCommissionSettings: async (data: {
    default_rate?: string | number;
    clinic_id?: string | null;
    clinic_rate?: string | number | null;
    reason?: string;
  }): Promise<{ default_rate: string }> => {
    const response = await apiClient.patch<{ success: boolean; message: string; data: { default_rate: string } }>("/admin/settings/commission/", data);
    return response.data.data;
  },

  // Audit Logs
  getAuditLogs: async (params?: {
    action?: string;
    resource_type?: string;
    clinic_id?: string;
    actor_id?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResponse<AdminAuditLog>> => {
    const response = await apiClient.get<PaginatedResponse<AdminAuditLog>>("/admin/audit-logs/", { params });
    return response.data;
  },
};
