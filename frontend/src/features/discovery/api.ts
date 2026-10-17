import apiClient from "@/services/api";
import type {
  ClinicSearchParams,
  DoctorSearchParams,
  PaginatedResponse,
  PublicAvailabilityResponse,
  PublicClinic,
  PublicDoctor,
  Specialization,
} from "./types";

export const discoveryApi = {
  searchDoctors: async (params: DoctorSearchParams = {}): Promise<PaginatedResponse<PublicDoctor>> => {
    // Filter out empty params
    const cleanParams: Record<string, string | number> = {};
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        cleanParams[key] = val;
      }
    });
    const response = await apiClient.get<PaginatedResponse<PublicDoctor>>("/public/doctors/", {
      params: cleanParams,
    });
    return response.data;
  },

  getDoctorDetail: async (doctorId: string): Promise<PublicDoctor> => {
    const response = await apiClient.get<PublicDoctor>(`/public/doctors/${doctorId}/`);
    return response.data;
  },

  searchClinics: async (params: ClinicSearchParams = {}): Promise<PaginatedResponse<PublicClinic>> => {
    const cleanParams: Record<string, string | number> = {};
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        cleanParams[key] = val;
      }
    });
    const response = await apiClient.get<PaginatedResponse<PublicClinic>>("/public/clinics/", {
      params: cleanParams,
    });
    return response.data;
  },

  getClinicDetail: async (clinicId: string): Promise<PublicClinic> => {
    const response = await apiClient.get<PublicClinic>(`/public/clinics/${clinicId}/`);
    return response.data;
  },

  getDoctorAvailability: async (
    clinicId: string,
    doctorId: string,
    date: string
  ): Promise<PublicAvailabilityResponse> => {
    const response = await apiClient.get<PublicAvailabilityResponse>(
      `/public/clinics/${clinicId}/doctors/${doctorId}/availability/`,
      {
        params: { date },
      }
    );
    return response.data;
  },

  getSpecializations: async (): Promise<Specialization[]> => {
    const response = await apiClient.get<{ success: boolean; data: Specialization[] }>(
      "/public/specializations/"
    );
    return response.data.data;
  },

  getCities: async (): Promise<string[]> => {
    const response = await apiClient.get<{ success: boolean; data: string[] }>("/public/cities/");
    return response.data.data;
  },
};
