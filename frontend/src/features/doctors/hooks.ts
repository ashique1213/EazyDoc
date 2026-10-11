import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adminReactivateDoctor,
  adminRejectDoctor,
  adminSuspendDoctor,
  adminVerifyDoctor,
  createDoctorProfile,
  deleteDoctorDocument,
  getAdminDoctorById,
  getAdminDoctors,
  getDoctorDocuments,
  getDoctorMe,
  getSpecializations,
  lookupDoctorRegistration,
  submitDoctorVerification,
  updateDoctorProfile,
  uploadDoctorDocument,
} from "./api";
import type {
  AdminDoctorFilters,
  DoctorProfilePayload,
} from "./types";

export const DOCTOR_QUERY_KEYS = {
  all: ["doctors"] as const,
  me: () => ["doctors", "me"] as const,
  documents: () => ["doctors", "documents"] as const,
  specializations: () => ["doctors", "specializations"] as const,
  lookup: (regNum: string, council?: string) =>
    ["doctors", "lookup", regNum, council || ""] as const,
  adminAll: (filters?: AdminDoctorFilters) => ["admin", "doctors", filters] as const,
  adminDetail: (id: string) => ["admin", "doctors", "detail", id] as const,
};

export const useDoctorMe = () => {
  return useQuery({
    queryKey: DOCTOR_QUERY_KEYS.me(),
    queryFn: getDoctorMe,
    retry: (failureCount, error: Error) => {
      // Don't retry on 404 (doctor hasn't created profile yet)
      if (axios.isAxiosError(error) && error.response?.status === 404) return false;
      return failureCount < 2;
    },
  });
};

export const useCreateDoctorProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DoctorProfilePayload) => createDoctorProfile(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(DOCTOR_QUERY_KEYS.me(), data);
      queryClient.invalidateQueries({ queryKey: DOCTOR_QUERY_KEYS.all });
    },
  });
};

export const useUpdateDoctorProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<DoctorProfilePayload>) => updateDoctorProfile(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(DOCTOR_QUERY_KEYS.me(), data);
      queryClient.invalidateQueries({ queryKey: DOCTOR_QUERY_KEYS.all });
    },
  });
};

export const useSubmitDoctorVerification = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: submitDoctorVerification,
    onSuccess: (data) => {
      queryClient.setQueryData(DOCTOR_QUERY_KEYS.me(), data);
      queryClient.invalidateQueries({ queryKey: DOCTOR_QUERY_KEYS.all });
    },
  });
};

export const useDoctorDocuments = () => {
  return useQuery({
    queryKey: DOCTOR_QUERY_KEYS.documents(),
    queryFn: getDoctorDocuments,
  });
};

export const useUploadDoctorDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentType, file }: { documentType: string; file: File }) =>
      uploadDoctorDocument(documentType, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCTOR_QUERY_KEYS.documents() });
      queryClient.invalidateQueries({ queryKey: DOCTOR_QUERY_KEYS.me() });
    },
  });
};

export const useDeleteDoctorDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDoctorDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCTOR_QUERY_KEYS.documents() });
      queryClient.invalidateQueries({ queryKey: DOCTOR_QUERY_KEYS.me() });
    },
  });
};

export const useSpecializations = () => {
  return useQuery({
    queryKey: DOCTOR_QUERY_KEYS.specializations(),
    queryFn: getSpecializations,
    staleTime: 1000 * 60 * 30, // 30 minutes cache
  });
};

export const useLookupDoctorRegistration = (
  registrationNumber: string,
  registrationCouncil?: string,
  enabled: boolean = false
) => {
  return useQuery({
    queryKey: DOCTOR_QUERY_KEYS.lookup(registrationNumber, registrationCouncil),
    queryFn: () => lookupDoctorRegistration(registrationNumber, registrationCouncil),
    enabled: enabled && Boolean(registrationNumber.trim()),
  });
};

// Admin Hooks
export const useAdminDoctors = (filters: AdminDoctorFilters = {}) => {
  return useQuery({
    queryKey: DOCTOR_QUERY_KEYS.adminAll(filters),
    queryFn: () => getAdminDoctors(filters),
  });
};

export const useAdminDoctor = (id?: string) => {
  return useQuery({
    queryKey: DOCTOR_QUERY_KEYS.adminDetail(id || ""),
    queryFn: () => getAdminDoctorById(id!),
    enabled: Boolean(id),
  });
};

export const useAdminVerifyDoctor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminVerifyDoctor(id),
    onSuccess: (data, id) => {
      queryClient.setQueryData(DOCTOR_QUERY_KEYS.adminDetail(id), data);
      queryClient.invalidateQueries({ queryKey: ["admin", "doctors"] });
    },
  });
};

export const useAdminRejectDoctor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      adminRejectDoctor(id, reason),
    onSuccess: (data, { id }) => {
      queryClient.setQueryData(DOCTOR_QUERY_KEYS.adminDetail(id), data);
      queryClient.invalidateQueries({ queryKey: ["admin", "doctors"] });
    },
  });
};

export const useAdminSuspendDoctor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      adminSuspendDoctor(id, reason),
    onSuccess: (data, { id }) => {
      queryClient.setQueryData(DOCTOR_QUERY_KEYS.adminDetail(id), data);
      queryClient.invalidateQueries({ queryKey: ["admin", "doctors"] });
    },
  });
};

export const useAdminReactivateDoctor = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminReactivateDoctor(id),
    onSuccess: (data, id) => {
      queryClient.setQueryData(DOCTOR_QUERY_KEYS.adminDetail(id), data);
      queryClient.invalidateQueries({ queryKey: ["admin", "doctors"] });
    },
  });
};
