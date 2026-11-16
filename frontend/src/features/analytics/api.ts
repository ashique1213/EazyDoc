import apiClient from "@/services/api";
import type {
  AdminOverviewData,
  AnalyticsFilterParams,
  AppointmentAnalyticsData,
  ClinicAppointmentData,
  ClinicDoctorPerformanceItem,
  ClinicOverviewData,
  ClinicPerformanceItem,
  ClinicRevenueData,
  DoctorPerformanceItem,
  FinancialReconciliationData,
  RevenueAnalyticsData,
} from "./types";

export const analyticsApi = {
  // Super Admin Endpoints
  getAdminOverview: async (params?: AnalyticsFilterParams): Promise<AdminOverviewData> => {
    const res = await apiClient.get<{ success: boolean; data: AdminOverviewData }>(
      "/admin/analytics/overview/",
      { params }
    );
    return res.data.data;
  },

  getAdminRevenue: async (params?: AnalyticsFilterParams): Promise<RevenueAnalyticsData> => {
    const res = await apiClient.get<{ success: boolean; data: RevenueAnalyticsData }>(
      "/admin/analytics/revenue/",
      { params }
    );
    return res.data.data;
  },

  getAdminAppointments: async (params?: AnalyticsFilterParams): Promise<AppointmentAnalyticsData> => {
    const res = await apiClient.get<{ success: boolean; data: AppointmentAnalyticsData }>(
      "/admin/analytics/appointments/",
      { params }
    );
    return res.data.data;
  },

  getAdminClinics: async (
    params?: AnalyticsFilterParams & { search?: string }
  ): Promise<ClinicPerformanceItem[]> => {
    const res = await apiClient.get<{ success: boolean; data: ClinicPerformanceItem[] }>(
      "/admin/analytics/clinics/",
      { params }
    );
    return res.data.data;
  },

  getAdminDoctors: async (
    params?: AnalyticsFilterParams & { verification_status?: string; search?: string }
  ): Promise<DoctorPerformanceItem[]> => {
    const res = await apiClient.get<{ success: boolean; data: DoctorPerformanceItem[] }>(
      "/admin/analytics/doctors/",
      { params }
    );
    return res.data.data;
  },

  getAdminReconciliation: async (
    params?: AnalyticsFilterParams
  ): Promise<FinancialReconciliationData> => {
    const res = await apiClient.get<{ success: boolean; data: FinancialReconciliationData }>(
      "/admin/analytics/reconciliation/",
      { params }
    );
    return res.data.data;
  },

  downloadAdminReport: async (
    reportType: string,
    params?: AnalyticsFilterParams
  ): Promise<void> => {
    const query = new URLSearchParams();
    query.set("report_type", reportType);
    if (params?.period) query.set("period", params.period);
    if (params?.date_from) query.set("date_from", params.date_from);
    if (params?.date_to) query.set("date_to", params.date_to);
    if (params?.clinic_id) query.set("clinic_id", params.clinic_id);
    if (params?.doctor_id) query.set("doctor_id", params.doctor_id);

    const response = await apiClient.get(`/admin/analytics/reports/export/?${query.toString()}`, {
      responseType: "blob",
    });

    const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `eazydoc-admin-${reportType}-${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Clinic Scoped Endpoints
  getClinicOverview: async (
    clinicId: string,
    params?: AnalyticsFilterParams
  ): Promise<ClinicOverviewData> => {
    const res = await apiClient.get<{ success: boolean; data: ClinicOverviewData }>(
      `/clinics/${clinicId}/analytics/overview/`,
      { params }
    );
    return res.data.data;
  },

  getClinicRevenue: async (
    clinicId: string,
    params?: AnalyticsFilterParams
  ): Promise<ClinicRevenueData> => {
    const res = await apiClient.get<{ success: boolean; data: ClinicRevenueData }>(
      `/clinics/${clinicId}/analytics/revenue/`,
      { params }
    );
    return res.data.data;
  },

  getClinicAppointments: async (
    clinicId: string,
    params?: AnalyticsFilterParams
  ): Promise<ClinicAppointmentData> => {
    const res = await apiClient.get<{ success: boolean; data: ClinicAppointmentData }>(
      `/clinics/${clinicId}/analytics/appointments/`,
      { params }
    );
    return res.data.data;
  },

  getClinicDoctors: async (
    clinicId: string,
    params?: AnalyticsFilterParams
  ): Promise<ClinicDoctorPerformanceItem[]> => {
    const res = await apiClient.get<{ success: boolean; data: ClinicDoctorPerformanceItem[] }>(
      `/clinics/${clinicId}/analytics/doctors/`,
      { params }
    );
    return res.data.data;
  },

  downloadClinicReport: async (
    clinicId: string,
    reportType: string,
    params?: AnalyticsFilterParams
  ): Promise<void> => {
    const query = new URLSearchParams();
    query.set("report_type", reportType);
    if (params?.period) query.set("period", params.period);
    if (params?.date_from) query.set("date_from", params.date_from);
    if (params?.date_to) query.set("date_to", params.date_to);
    if (params?.doctor_id) query.set("doctor_id", params.doctor_id);

    const response = await apiClient.get(
      `/clinics/${clinicId}/analytics/reports/export/?${query.toString()}`,
      { responseType: "blob" }
    );

    const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `clinic-${clinicId}-${reportType}-${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

