import { apiClient } from "@/services/api";
import type {
  DoctorClinic,
  DoctorClinicInvitationPayload,
  DoctorClinicSettingsPayload,
  DoctorClinicStatus,
} from "./types";

// ==========================================
// Clinic Owner API Endpoints
// ==========================================

export const getClinicDoctors = async (
  clinicId: string,
  statusFilter?: DoctorClinicStatus | "ALL"
): Promise<DoctorClinic[]> => {
  const params: Record<string, string> = {};
  if (statusFilter && statusFilter !== "ALL") {
    params.status = statusFilter;
  }
  const response = await apiClient.get(`/clinics/${clinicId}/doctors/`, { params });
  return response.data.data;
};

export const getClinicDoctorInvitations = async (
  clinicId: string,
  statusFilter?: DoctorClinicStatus
): Promise<DoctorClinic[]> => {
  const params: Record<string, string> = {};
  if (statusFilter) {
    params.status = statusFilter;
  }
  const response = await apiClient.get(`/clinics/${clinicId}/doctor-invitations/`, { params });
  return response.data.data;
};

export const inviteDoctorToClinic = async (
  clinicId: string,
  payload: DoctorClinicInvitationPayload
): Promise<DoctorClinic> => {
  const response = await apiClient.post(`/clinics/${clinicId}/doctor-invitations/`, payload);
  return response.data.data;
};

export const updateClinicDoctorSettings = async (
  clinicId: string,
  associationId: string,
  payload: DoctorClinicSettingsPayload
): Promise<DoctorClinic> => {
  const response = await apiClient.patch(
    `/clinics/${clinicId}/doctors/${associationId}/settings/`,
    payload
  );
  return response.data.data;
};

export const removeClinicDoctor = async (
  clinicId: string,
  associationId: string
): Promise<DoctorClinic> => {
  const response = await apiClient.post(
    `/clinics/${clinicId}/doctors/${associationId}/remove/`
  );
  return response.data.data;
};

// ==========================================
// Doctor API Endpoints
// ==========================================

export const getDoctorClinics = async (
  statusFilter?: DoctorClinicStatus | "ALL"
): Promise<DoctorClinic[]> => {
  const params: Record<string, string> = {};
  if (statusFilter && statusFilter !== "ALL") {
    params.status = statusFilter;
  }
  const response = await apiClient.get("/doctors/me/clinics/", { params });
  return response.data.data;
};

export const getDoctorClinicInvitations = async (): Promise<DoctorClinic[]> => {
  const response = await apiClient.get("/doctors/me/clinic-invitations/");
  return response.data.data;
};

export const acceptClinicInvitation = async (
  associationId: string
): Promise<DoctorClinic> => {
  const response = await apiClient.post(
    `/doctors/me/clinic-invitations/${associationId}/accept/`
  );
  return response.data.data;
};

export const rejectClinicInvitation = async (
  associationId: string
): Promise<DoctorClinic> => {
  const response = await apiClient.post(
    `/doctors/me/clinic-invitations/${associationId}/reject/`
  );
  return response.data.data;
};
