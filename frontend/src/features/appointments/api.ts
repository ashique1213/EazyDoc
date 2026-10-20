import { apiClient } from "@/services/api";
import type { PaginatedResponse } from "@/features/discovery/types";
import type {
  Appointment,
  AppointmentHistoryItem,
  AppointmentListItem,
  BookAppointmentPayload,
  CancelAppointmentPayload,
  MyAppointmentsParams,
  ReportUnavailabilityPayload,
  RescheduleAppointmentPayload,
} from "./types";

export const appointmentsApi = {
  createAppointment: async (
    payload: BookAppointmentPayload,
    idempotencyKey?: string
  ): Promise<Appointment> => {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }
    const response = await apiClient.post<Appointment>(
      "/appointments/",
      {
        ...payload,
        idempotency_key: idempotencyKey || payload.idempotency_key,
      },
      { headers }
    );
    return response.data;
  },

  getMyAppointments: async (
    params?: MyAppointmentsParams
  ): Promise<PaginatedResponse<AppointmentListItem>> => {
    const response = await apiClient.get<PaginatedResponse<AppointmentListItem>>(
      "/appointments/my/",
      { params }
    );
    return response.data;
  },

  getAppointmentDetail: async (appointmentId: string): Promise<Appointment> => {
    const response = await apiClient.get<Appointment>(
      `/appointments/${appointmentId}/`
    );
    return response.data;
  },

  cancelAppointment: async (
    appointmentId: string,
    payload?: CancelAppointmentPayload
  ): Promise<Appointment> => {
    const response = await apiClient.post<Appointment>(
      `/appointments/${appointmentId}/cancel/`,
      payload || {}
    );
    return response.data;
  },

  rescheduleAppointment: async (
    appointmentId: string,
    payload: RescheduleAppointmentPayload
  ): Promise<Appointment> => {
    const response = await apiClient.post<Appointment>(
      `/appointments/${appointmentId}/reschedule/`,
      payload
    );
    return response.data;
  },

  getAppointmentHistory: async (
    appointmentId: string
  ): Promise<AppointmentHistoryItem[]> => {
    const response = await apiClient.get<AppointmentHistoryItem[]>(
      `/appointments/${appointmentId}/history/`
    );
    return response.data;
  },

  clinicCancelAppointment: async (
    clinicId: string,
    appointmentId: string,
    payload?: CancelAppointmentPayload
  ): Promise<Appointment> => {
    const response = await apiClient.post<Appointment>(
      `/clinics/${clinicId}/appointments/${appointmentId}/cancel/`,
      payload || {}
    );
    return response.data;
  },

  clinicRescheduleAppointment: async (
    clinicId: string,
    appointmentId: string,
    payload: RescheduleAppointmentPayload
  ): Promise<Appointment> => {
    const response = await apiClient.post<Appointment>(
      `/clinics/${clinicId}/appointments/${appointmentId}/reschedule/`,
      payload
    );
    return response.data;
  },

  clinicReportUnavailability: async (
    clinicId: string,
    appointmentId: string,
    payload: ReportUnavailabilityPayload
  ): Promise<Appointment> => {
    const response = await apiClient.post<Appointment>(
      `/clinics/${clinicId}/appointments/${appointmentId}/report-unavailability/`,
      payload
    );
    return response.data;
  },

  doctorReportUnavailability: async (
    appointmentId: string,
    payload: ReportUnavailabilityPayload
  ): Promise<Appointment> => {
    const response = await apiClient.post<Appointment>(
      `/doctors/me/appointments/${appointmentId}/report-unavailability/`,
      payload
    );
    return response.data;
  },

  getClinicAppointments: async (
    clinicId: string,
    params?: { doctor_id?: string; status?: string; filter?: string; page?: number }
  ): Promise<PaginatedResponse<Appointment>> => {
    const response = await apiClient.get<PaginatedResponse<Appointment>>(
      `/clinics/${clinicId}/appointments/`,
      { params }
    );
    return response.data;
  },

  getDoctorAppointments: async (
    params?: { clinic_id?: string; status?: string; filter?: string; page?: number }
  ): Promise<PaginatedResponse<Appointment>> => {
    const response = await apiClient.get<PaginatedResponse<Appointment>>(
      "/doctors/me/appointments/",
      { params }
    );
    return response.data;
  },
};

