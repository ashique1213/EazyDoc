import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adminApproveClinic,
  adminReactivateClinic,
  adminRejectClinic,
  adminSuspendClinic,
  createClinic,
  getAdminClinicById,
  getAdminClinics,
  getClinicById,
  getMyClinics,
  submitClinic,
  updateClinic,
} from "./api";
import type {
  AdminClinicFilters,
  ClinicCreatePayload,
  ClinicUpdatePayload,
} from "./types";

export const CLINIC_QUERY_KEYS = {
  all: ["clinics"] as const,
  myClinics: () => ["clinics", "my-clinics"] as const,
  detail: (id: string) => ["clinics", "detail", id] as const,
  adminAll: (filters?: AdminClinicFilters) => ["admin", "clinics", filters] as const,
  adminDetail: (id: string) => ["admin", "clinics", "detail", id] as const,
};

export const useMyClinics = () => {
  return useQuery({
    queryKey: CLINIC_QUERY_KEYS.myClinics(),
    queryFn: getMyClinics,
  });
};

export const useClinic = (id?: string) => {
  return useQuery({
    queryKey: CLINIC_QUERY_KEYS.detail(id || ""),
    queryFn: () => getClinicById(id!),
    enabled: Boolean(id),
  });
};

export const useCreateClinic = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClinicCreatePayload) => createClinic(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CLINIC_QUERY_KEYS.all });
    },
  });
};

export const useUpdateClinic = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClinicUpdatePayload) => updateClinic(id, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(CLINIC_QUERY_KEYS.detail(id), updated);
      queryClient.invalidateQueries({ queryKey: CLINIC_QUERY_KEYS.myClinics() });
    },
  });
};

export const useSubmitClinic = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => submitClinic(id),
    onSuccess: (updated) => {
      queryClient.setQueryData(CLINIC_QUERY_KEYS.detail(id), updated);
      queryClient.invalidateQueries({ queryKey: CLINIC_QUERY_KEYS.myClinics() });
    },
  });
};

// Super Admin Hooks
export const useAdminClinics = (filters: AdminClinicFilters = {}) => {
  return useQuery({
    queryKey: CLINIC_QUERY_KEYS.adminAll(filters),
    queryFn: () => getAdminClinics(filters),
  });
};

export const useAdminClinic = (id?: string) => {
  return useQuery({
    queryKey: CLINIC_QUERY_KEYS.adminDetail(id || ""),
    queryFn: () => getAdminClinicById(id!),
    enabled: Boolean(id),
  });
};

export const useAdminApproveClinic = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => adminApproveClinic(id),
    onSuccess: (updated) => {
      queryClient.setQueryData(CLINIC_QUERY_KEYS.adminDetail(id), updated);
      queryClient.invalidateQueries({ queryKey: ["admin", "clinics"] });
    },
  });
};

export const useAdminRejectClinic = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => adminRejectClinic(id, reason),
    onSuccess: (updated) => {
      queryClient.setQueryData(CLINIC_QUERY_KEYS.adminDetail(id), updated);
      queryClient.invalidateQueries({ queryKey: ["admin", "clinics"] });
    },
  });
};

export const useAdminSuspendClinic = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => adminSuspendClinic(id, reason),
    onSuccess: (updated) => {
      queryClient.setQueryData(CLINIC_QUERY_KEYS.adminDetail(id), updated);
      queryClient.invalidateQueries({ queryKey: ["admin", "clinics"] });
    },
  });
};

export const useAdminReactivateClinic = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => adminReactivateClinic(id),
    onSuccess: (updated) => {
      queryClient.setQueryData(CLINIC_QUERY_KEYS.adminDetail(id), updated);
      queryClient.invalidateQueries({ queryKey: ["admin", "clinics"] });
    },
  });
};
