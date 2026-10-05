import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import type { HealthResponse } from "@/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
  timeout: 10000,
});

// Request interceptor: Prepared for Day 3 JWT attachment
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // In Day 3, access token from auth store will be attached here
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor: Standardized error formatting
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Interceptor hook for 401 token refresh (scheduled for Day 3)
    return Promise.reject(error);
  }
);

// Service API methods
export const systemApi = {
  checkHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>("/health/");
    return response.data;
  },
};

export default apiClient;
