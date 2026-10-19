import { apiClient } from "@/services/api";
import type { PaginatedResponse } from "@/features/discovery/types";
import type {
  Appointment,
  AppointmentListItem,
  BookAppointmentPayload,
  MyAppointmentsParams,
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
