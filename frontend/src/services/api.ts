import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import type { HealthResponse } from "@/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

// In-memory access token storage (NEVER in localStorage/sessionStorage)
let inMemoryAccessToken: string | null = null;

export const setInMemoryAccessToken = (token: string | null) => {
  inMemoryAccessToken = token;
};

export const getInMemoryAccessToken = (): string | null => {
  return inMemoryAccessToken;
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // Enables browser to send and receive HttpOnly cookies
  timeout: 15000,
});

// Request interceptor: Attach in-memory access token if available
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (inMemoryAccessToken && config.headers) {
      config.headers.Authorization = `Bearer ${inMemoryAccessToken}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor: 401 token refresh queue with loop prevention
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: AxiosError | null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Only attempt refresh on 401 for non-auth endpoints
    const requestUrl = originalRequest?.url || "";
    const isAuthRoute =
      requestUrl.includes("/auth/login/") ||
      requestUrl.includes("/auth/refresh/") ||
      requestUrl.includes("/auth/logout/") ||
      requestUrl.includes("/auth/register/");

    if (error.response?.status === 401 && !originalRequest?._retry && !isAuthRoute) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => apiClient(originalRequest))
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshResponse = await apiClient.post("/auth/refresh/");
        const newAccessToken = refreshResponse.data?.data?.tokens?.access;
        if (newAccessToken) {
          setInMemoryAccessToken(newAccessToken);
        }
        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as AxiosError);
        setInMemoryAccessToken(null);
        // Signal unauthenticated state
        window.dispatchEvent(new CustomEvent("eazydoc:session-expired"));
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export const systemApi = {
  checkHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>("/health/");
    return response.data;
  },
};

export default apiClient;
