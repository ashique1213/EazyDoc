import { apiClient } from "@/services/api";
import type {
  AdminClinicFilters,
  Clinic,
  ClinicCreatePayload,
  ClinicUpdatePayload,
  PaginatedResponse,
} from "./types";

export const createClinic = async (payload: ClinicCreatePayload): Promise<Clinic> => {
  let requestData: FormData | ClinicCreatePayload;

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

  const response = await apiClient.post("/clinics/", requestData, {
    headers: requestData instanceof FormData ? { "Content-Type": "multipart/form-data" } : {},
  });
  return response.data.data;
};

export const getMyClinics = async (): Promise<Clinic[]> => {
  const response = await apiClient.get("/clinics/my-clinics/");
  return response.data.data;
};

export const getClinicById = async (id: string): Promise<Clinic> => {
  const response = await apiClient.get(`/clinics/${id}/`);
  return response.data.data;
};

export const updateClinic = async (
  id: string,
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

  const response = await apiClient.patch(`/clinics/${id}/`, requestData, {
    headers: requestData instanceof FormData ? { "Content-Type": "multipart/form-data" } : {},
  });
  return response.data.data;
};

export const submitClinic = async (id: string): Promise<Clinic> => {
  const response = await apiClient.post(`/clinics/${id}/submit/`);
  return response.data.data;
};

// Super Admin API endpoints
export const getAdminClinics = async (
  filters: AdminClinicFilters = {}
): Promise<PaginatedResponse<Clinic>> => {
  const params: Record<string, string | number> = {};
  if (filters.status && filters.status !== "ALL") {
    params.status = filters.status;
  }
  if (filters.search) {
    params.search = filters.search;
  }
  if (filters.page) {
    params.page = filters.page;
  }

  const response = await apiClient.get("/admin/clinics/", { params });
  return response.data;
};

export const getAdminClinicById = async (id: string): Promise<Clinic> => {
  const response = await apiClient.get(`/admin/clinics/${id}/`);
  return response.data.data;
};

export const adminApproveClinic = async (id: string): Promise<Clinic> => {
  const response = await apiClient.post(`/admin/clinics/${id}/approve/`);
  return response.data.data;
};

export const adminRejectClinic = async (
  id: string,
  reason: string
): Promise<Clinic> => {
  const response = await apiClient.post(`/admin/clinics/${id}/reject/`, { reason });
  return response.data.data;
};

export const adminSuspendClinic = async (
  id: string,
  reason: string
): Promise<Clinic> => {
  const response = await apiClient.post(`/admin/clinics/${id}/suspend/`, { reason });
  return response.data.data;
};

export const adminReactivateClinic = async (id: string): Promise<Clinic> => {
  const response = await apiClient.post(`/admin/clinics/${id}/reactivate/`);
  return response.data.data;
};
