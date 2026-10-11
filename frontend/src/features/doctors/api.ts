import { apiClient } from "@/services/api";
import type {
  AdminDoctorFilters,
  Doctor,
  DoctorDocument,
  DoctorProfilePayload,
  DoctorRegistrationLookupResult,
  PaginatedResponse,
  Specialization,
} from "./types";

export const getDoctorMe = async (): Promise<Doctor> => {
  const response = await apiClient.get("/doctors/me/");
  return response.data.data;
};

export const createDoctorProfile = async (payload: DoctorProfilePayload): Promise<Doctor> => {
  let requestData: FormData | DoctorProfilePayload;

  if (payload.profile_photo instanceof File) {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (key === "profile_photo" && value instanceof File) {
          formData.append("profile_photo", value);
        } else {
          formData.append(key, String(value));
        }
      }
    });
    requestData = formData;
  } else {
    requestData = payload;
  }

  const response = await apiClient.post("/doctors/profile/", requestData, {
    headers: requestData instanceof FormData ? { "Content-Type": "multipart/form-data" } : {},
  });
  return response.data.data;
};

export const updateDoctorProfile = async (
  payload: Partial<DoctorProfilePayload>
): Promise<Doctor> => {
  let requestData: FormData | Partial<DoctorProfilePayload>;

  if (payload.profile_photo instanceof File) {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (key === "profile_photo" && value instanceof File) {
          formData.append("profile_photo", value);
        } else {
          formData.append(key, String(value));
        }
      }
    });
    requestData = formData;
  } else {
    requestData = payload;
  }

  const response = await apiClient.patch("/doctors/me/", requestData, {
    headers: requestData instanceof FormData ? { "Content-Type": "multipart/form-data" } : {},
  });
  return response.data.data;
};

export const submitDoctorVerification = async (): Promise<Doctor> => {
  const response = await apiClient.post("/doctors/me/submit-verification/");
  return response.data.data;
};

export const getDoctorDocuments = async (): Promise<DoctorDocument[]> => {
  const response = await apiClient.get("/doctors/me/documents/");
  return response.data.data;
};

export const uploadDoctorDocument = async (
  documentType: string,
  file: File
): Promise<DoctorDocument> => {
  const formData = new FormData();
  formData.append("document_type", documentType);
  formData.append("file", file);

  const response = await apiClient.post("/doctors/me/documents/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data.data;
};

export const deleteDoctorDocument = async (id: string): Promise<void> => {
  await apiClient.delete(`/doctors/me/documents/${id}/`);
};

export const getSpecializations = async (): Promise<Specialization[]> => {
  const response = await apiClient.get("/doctors/specializations/");
  return response.data.data;
};

export const lookupDoctorRegistration = async (
  registrationNumber: string,
  registrationCouncil?: string
): Promise<DoctorRegistrationLookupResult> => {
  const params: Record<string, string> = {
    registration_number: registrationNumber,
  };
  if (registrationCouncil) {
    params.registration_council = registrationCouncil;
  }

  const response = await apiClient.get("/doctors/registration-lookup/", { params });
  return response.data.data;
};

// Super Admin API endpoints
export const getAdminDoctors = async (
  filters: AdminDoctorFilters = {}
): Promise<PaginatedResponse<Doctor>> => {
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

  const response = await apiClient.get("/admin/doctors/", { params });
  return response.data;
};

export const getAdminDoctorById = async (id: string): Promise<Doctor> => {
  const response = await apiClient.get(`/admin/doctors/${id}/`);
  return response.data.data;
};

export const adminVerifyDoctor = async (id: string): Promise<Doctor> => {
  const response = await apiClient.post(`/admin/doctors/${id}/verify/`);
  return response.data.data;
};

export const adminRejectDoctor = async (id: string, reason: string): Promise<Doctor> => {
  const response = await apiClient.post(`/admin/doctors/${id}/reject/`, { reason });
  return response.data.data;
};

export const adminSuspendDoctor = async (id: string, reason: string): Promise<Doctor> => {
  const response = await apiClient.post(`/admin/doctors/${id}/suspend/`, { reason });
  return response.data.data;
};

export const adminReactivateDoctor = async (id: string): Promise<Doctor> => {
  const response = await apiClient.post(`/admin/doctors/${id}/reactivate/`);
  return response.data.data;
};
