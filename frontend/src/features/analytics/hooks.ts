import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "./api";
import type { AnalyticsFilterParams } from "./types";

export const ANALYTICS_QUERY_KEYS = {
  adminOverview: (params?: AnalyticsFilterParams) => ["analytics", "admin", "overview", params] as const,
  adminRevenue: (params?: AnalyticsFilterParams) => ["analytics", "admin", "revenue", params] as const,
  adminAppointments: (params?: AnalyticsFilterParams) => ["analytics", "admin", "appointments", params] as const,
  adminClinics: (params?: AnalyticsFilterParams & { search?: string }) => ["analytics", "admin", "clinics", params] as const,
  adminDoctors: (params?: AnalyticsFilterParams & { verification_status?: string; search?: string }) => ["analytics", "admin", "doctors", params] as const,
  adminReconciliation: (params?: AnalyticsFilterParams) => ["analytics", "admin", "reconciliation", params] as const,

  clinicOverview: (clinicId: string, params?: AnalyticsFilterParams) =>
    ["analytics", "clinic", clinicId, "overview", params] as const,
  clinicRevenue: (clinicId: string, params?: AnalyticsFilterParams) =>
    ["analytics", "clinic", clinicId, "revenue", params] as const,
  clinicAppointments: (clinicId: string, params?: AnalyticsFilterParams) =>
    ["analytics", "clinic", clinicId, "appointments", params] as const,
  clinicDoctors: (clinicId: string, params?: AnalyticsFilterParams) =>
    ["analytics", "clinic", clinicId, "doctors", params] as const,
};

// Super Admin Hooks
export const useAdminAnalyticsOverview = (params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.adminOverview(params),
    queryFn: () => analyticsApi.getAdminOverview(params),
  });
};

export const useAdminAnalyticsRevenue = (params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.adminRevenue(params),
    queryFn: () => analyticsApi.getAdminRevenue(params),
  });
};

export const useAdminAnalyticsAppointments = (params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.adminAppointments(params),
    queryFn: () => analyticsApi.getAdminAppointments(params),
  });
};

export const useAdminAnalyticsClinics = (params?: AnalyticsFilterParams & { search?: string }) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.adminClinics(params),
    queryFn: () => analyticsApi.getAdminClinics(params),
  });
};

export const useAdminAnalyticsDoctors = (
  params?: AnalyticsFilterParams & { verification_status?: string; search?: string }
) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.adminDoctors(params),
    queryFn: () => analyticsApi.getAdminDoctors(params),
  });
};

export const useAdminAnalyticsReconciliation = (params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.adminReconciliation(params),
    queryFn: () => analyticsApi.getAdminReconciliation(params),
  });
};

// Clinic Owner Hooks
export const useClinicAnalyticsOverview = (clinicId: string, params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.clinicOverview(clinicId, params),
    queryFn: () => analyticsApi.getClinicOverview(clinicId, params),
    enabled: Boolean(clinicId),
  });
};

export const useClinicAnalyticsRevenue = (clinicId: string, params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.clinicRevenue(clinicId, params),
    queryFn: () => analyticsApi.getClinicRevenue(clinicId, params),
    enabled: Boolean(clinicId),
  });
};

export const useClinicAnalyticsAppointments = (clinicId: string, params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.clinicAppointments(clinicId, params),
    queryFn: () => analyticsApi.getClinicAppointments(clinicId, params),
    enabled: Boolean(clinicId),
  });
};

export const useClinicAnalyticsDoctors = (clinicId: string, params?: AnalyticsFilterParams) => {
  return useQuery({
    queryKey: ANALYTICS_QUERY_KEYS.clinicDoctors(clinicId, params),
    queryFn: () => analyticsApi.getClinicDoctors(clinicId, params),
    enabled: Boolean(clinicId),
  });
};
