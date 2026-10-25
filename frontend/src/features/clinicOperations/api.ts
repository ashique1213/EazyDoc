import { apiClient } from "@/services/api";
import type {
  ClinicCalendarData,
  ClinicClosure,
  ClinicClosureCreatePayload,
  ClinicClosurePreviewResponse,
  ClinicDashboardSummary,
  ClinicFinanceSummary,
  ClinicStaffCreatePayload,
  ClinicStaffMember,
  ClinicStaffUpdatePayload,
  ClinicTrendsResponse,
  PaginatedPaymentsResponse,
} from "./types";
import type { Clinic, ClinicUpdatePayload } from "@/features/clinics";
import type { Appointment } from "@/features/appointments";

// Dashboard Overview & Trends
export const getClinicDashboardSummary = async (
  clinicId: string,
  params?: { period?: string; from_date?: string; to_date?: string }
): Promise<ClinicDashboardSummary> => {
  const response = await apiClient.get(`/clinics/${clinicId}/dashboard/summary/`, { params });
  return response.data.data;
};

export const getClinicDashboardTrends = async (
  clinicId: string,
  params?: { period?: string; from_date?: string; to_date?: string }
): Promise<ClinicTrendsResponse> => {
  const response = await apiClient.get(`/clinics/${clinicId}/dashboard/appointment-trends/`, { params });
  return response.data.data;
};

// Profile & Management
export const getClinicManagementProfile = async (clinicId: string): Promise<Clinic> => {
  const response = await apiClient.get(`/clinics/${clinicId}/management/`);
  return response.data.data;
};

export const updateClinicManagementProfile = async (
  clinicId: string,
  payload: ClinicUpdatePayload
): Promise<Clinic> => {
  let requestData: FormData | ClinicUpdatePayload;
  if (payload.logo instanceof File) {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (key === "logo" && value instanceof File) {
          formData.append("logo", value);
        } else {
          formData.append(key, String(value));
        }
      }
    });
    requestData = formData;
  } else {
    requestData = payload;
  }

  const response = await apiClient.patch(`/clinics/${clinicId}/management/`, requestData, {
    headers: requestData instanceof FormData ? { "Content-Type": "multipart/form-data" } : {},
  });
  return response.data.data;
};

// Staff Management
export const getClinicStaff = async (clinicId: string): Promise<ClinicStaffMember[]> => {
  const response = await apiClient.get(`/clinics/${clinicId}/staff/`);
  return response.data.data;
};

export const createClinicStaff = async (
  clinicId: string,
  payload: ClinicStaffCreatePayload
): Promise<ClinicStaffMember> => {
  const response = await apiClient.post(`/clinics/${clinicId}/staff/`, payload);
  return response.data.data;
};

export const updateClinicStaff = async (
  clinicId: string,
  staffId: string,
  payload: ClinicStaffUpdatePayload
): Promise<ClinicStaffMember> => {
  const response = await apiClient.patch(`/clinics/${clinicId}/staff/${staffId}/`, payload);
  return response.data.data;
};

export const deleteClinicStaff = async (clinicId: string, staffId: string): Promise<void> => {
  await apiClient.delete(`/clinics/${clinicId}/staff/${staffId}/`);
};

// Closures & Calendar
export const getClinicClosures = async (clinicId: string): Promise<ClinicClosure[]> => {
  const response = await apiClient.get(`/clinics/${clinicId}/closures/`);
  return response.data.data;
};

export const previewClinicClosure = async (
  clinicId: string,
  payload: { start_date: string; end_date: string; reason?: string }
): Promise<ClinicClosurePreviewResponse> => {
  const response = await apiClient.post(`/clinics/${clinicId}/closures/preview/`, payload);
  return response.data.data;
};

export const createClinicClosure = async (
  clinicId: string,
  payload: ClinicClosureCreatePayload
): Promise<ClinicClosure> => {
  const response = await apiClient.post(`/clinics/${clinicId}/closures/`, payload);
  return response.data.data;
};

export const deleteClinicClosure = async (clinicId: string, closureId: string): Promise<void> => {
  await apiClient.delete(`/clinics/${clinicId}/closures/${closureId}/`);
};

export const getClinicCalendar = async (
  clinicId: string,
  params?: { start_date?: string; end_date?: string; doctor_id?: string }
): Promise<ClinicCalendarData> => {
  const response = await apiClient.get(`/clinics/${clinicId}/calendar/`, { params });
  return response.data.data;
};

// Clinic Appointments & Lifecycle
export const getClinicAppointments = async (
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
): Promise<{ count?: number; results: Appointment[] }> => {
  const response = await apiClient.get(`/clinics/${clinicId}/appointments/`, { params });
  if (Array.isArray(response.data)) {
    return { results: response.data };
  }
  return response.data;
};

export const getClinicAppointmentDetail = async (
  clinicId: string,
  appointmentId: string
): Promise<Appointment & { history?: any[] }> => {
  const response = await apiClient.get(`/clinics/${clinicId}/appointments/${appointmentId}/`);
  return response.data.data;
};

export const confirmClinicAppointment = async (
  clinicId: string,
  appointmentId: string
): Promise<Appointment> => {
  const response = await apiClient.post(`/clinics/${clinicId}/appointments/${appointmentId}/confirm/`);
  return response.data.data;
};

export const completeClinicAppointment = async (
  clinicId: string,
  appointmentId: string
): Promise<Appointment> => {
  const response = await apiClient.post(`/clinics/${clinicId}/appointments/${appointmentId}/complete/`);
  return response.data.data;
};

export const markNoShowClinicAppointment = async (
  clinicId: string,
  appointmentId: string
): Promise<Appointment> => {
  const response = await apiClient.post(`/clinics/${clinicId}/appointments/${appointmentId}/no-show/`);
  return response.data.data;
};

// Finance
export const getClinicFinanceSummary = async (
  clinicId: string,
  params?: { period?: string; from_date?: string; to_date?: string }
): Promise<ClinicFinanceSummary> => {
  const response = await apiClient.get(`/clinics/${clinicId}/finance/summary/`, { params });
  return response.data.data;
};

export const getClinicFinancePayments = async (
  clinicId: string,
  params?: { status?: string; search?: string; page?: number; page_size?: number }
): Promise<PaginatedPaymentsResponse> => {
  const response = await apiClient.get(`/clinics/${clinicId}/finance/payments/`, { params });
  return response.data.data;
};
