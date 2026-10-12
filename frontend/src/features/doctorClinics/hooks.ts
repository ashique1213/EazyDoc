import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acceptClinicInvitation,
  getClinicDoctorInvitations,
  getClinicDoctors,
  getDoctorClinicInvitations,
  getDoctorClinics,
  inviteDoctorToClinic,
  rejectClinicInvitation,
  removeClinicDoctor,
  updateClinicDoctorSettings,
} from "./api";
import type {
  DoctorClinicInvitationPayload,
  DoctorClinicSettingsPayload,
  DoctorClinicStatus,
} from "./types";

// ==========================================
// Clinic Owner Hooks
// ==========================================

export const useClinicDoctors = (
  clinicId?: string,
  statusFilter?: DoctorClinicStatus | "ALL"
) => {
  return useQuery({
    queryKey: ["clinicDoctors", clinicId, statusFilter],
    queryFn: () => getClinicDoctors(clinicId!, statusFilter),
    enabled: Boolean(clinicId),
  });
};

export const useClinicDoctorInvitations = (
  clinicId?: string,
  statusFilter?: DoctorClinicStatus
) => {
  return useQuery({
    queryKey: ["clinicDoctorInvitations", clinicId, statusFilter],
    queryFn: () => getClinicDoctorInvitations(clinicId!, statusFilter),
    enabled: Boolean(clinicId),
  });
};

export const useInviteDoctorToClinic = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DoctorClinicInvitationPayload) =>
      inviteDoctorToClinic(clinicId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinicDoctors", clinicId] });
      queryClient.invalidateQueries({ queryKey: ["clinicDoctorInvitations", clinicId] });
    },
  });
};

export const useUpdateClinicDoctorSettings = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      associationId,
      payload,
    }: {
      associationId: string;
      payload: DoctorClinicSettingsPayload;
    }) => updateClinicDoctorSettings(clinicId, associationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinicDoctors", clinicId] });
    },
  });
};

export const useRemoveClinicDoctor = (clinicId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (associationId: string) =>
      removeClinicDoctor(clinicId, associationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinicDoctors", clinicId] });
    },
  });
};

// ==========================================
// Doctor Hooks
// ==========================================

export const useDoctorClinics = (statusFilter?: DoctorClinicStatus | "ALL") => {
  return useQuery({
    queryKey: ["doctorClinics", statusFilter],
    queryFn: () => getDoctorClinics(statusFilter),
  });
};

export const useDoctorClinicInvitations = () => {
  return useQuery({
    queryKey: ["doctorClinicInvitations"],
    queryFn: () => getDoctorClinicInvitations(),
  });
};

export const useAcceptClinicInvitation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (associationId: string) => acceptClinicInvitation(associationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctorClinics"] });
      queryClient.invalidateQueries({ queryKey: ["doctorClinicInvitations"] });
    },
  });
};

export const useRejectClinicInvitation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (associationId: string) => rejectClinicInvitation(associationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctorClinics"] });
      queryClient.invalidateQueries({ queryKey: ["doctorClinicInvitations"] });
    },
  });
};
