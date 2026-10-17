import { useQuery } from "@tanstack/react-query";
import { discoveryApi } from "./api";
import type { ClinicSearchParams, DoctorSearchParams } from "./types";

export function useDoctorSearch(params: DoctorSearchParams) {
  return useQuery({
    queryKey: ["publicDoctors", params],
    queryFn: () => discoveryApi.searchDoctors(params),
    placeholderData: (previousData) => previousData,
    staleTime: 60 * 1000,
  });
}

export function useDoctorDetail(doctorId: string | undefined) {
  return useQuery({
    queryKey: ["publicDoctor", doctorId],
    queryFn: () => discoveryApi.getDoctorDetail(doctorId!),
    enabled: Boolean(doctorId),
    staleTime: 60 * 1000,
  });
}

export function useClinicSearch(params: ClinicSearchParams) {
  return useQuery({
    queryKey: ["publicClinics", params],
    queryFn: () => discoveryApi.searchClinics(params),
    placeholderData: (previousData) => previousData,
    staleTime: 60 * 1000,
  });
}

export function useClinicDetail(clinicId: string | undefined) {
  return useQuery({
    queryKey: ["publicClinic", clinicId],
    queryFn: () => discoveryApi.getClinicDetail(clinicId!),
    enabled: Boolean(clinicId),
    staleTime: 60 * 1000,
  });
}

export function useDoctorAvailability(
  clinicId: string | undefined,
  doctorId: string | undefined,
  date: string | undefined
) {
  return useQuery({
    queryKey: ["doctorAvailability", clinicId, doctorId, date],
    queryFn: () => discoveryApi.getDoctorAvailability(clinicId!, doctorId!, date!),
    enabled: Boolean(clinicId && doctorId && date),
    staleTime: 30 * 1000, // Shorter stale time for availability
  });
}

export function useSpecializations() {
  return useQuery({
    queryKey: ["publicSpecializations"],
    queryFn: discoveryApi.getSpecializations,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCities() {
  return useQuery({
    queryKey: ["publicCities"],
    queryFn: discoveryApi.getCities,
    staleTime: 5 * 60 * 1000,
  });
}
