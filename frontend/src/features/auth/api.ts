import apiClient, { setInMemoryAccessToken } from "@/services/api";
import type {
  AuthResponse,
  AuthUser,
  ForgotPasswordPayload,
  LoginPayload,
  LoginResponseData,
  RegisterPayload,
  ResendVerificationPayload,
  ResetPasswordPayload,
  VerifyEmailPayload,
} from "./types";

export const authApi = {
  login: async (payload: LoginPayload): Promise<AuthResponse<LoginResponseData>> => {
    const response = await apiClient.post<AuthResponse<LoginResponseData>>(
      "/auth/login/",
      payload
    );
    const accessToken = response.data?.data?.tokens?.access;
    if (accessToken) {
      setInMemoryAccessToken(accessToken);
    }
    return response.data;
  },

  register: async (payload: RegisterPayload): Promise<AuthResponse<{ user: AuthUser }>> => {
    const response = await apiClient.post<AuthResponse<{ user: AuthUser }>>(
      "/auth/register/",
      payload
    );
    return response.data;
  },

  logout: async (): Promise<AuthResponse> => {
    try {
      const response = await apiClient.post<AuthResponse>("/auth/logout/");
      return response.data;
    } finally {
      setInMemoryAccessToken(null);
    }
  },

  getCurrentUser: async (): Promise<AuthUser> => {
    const response = await apiClient.get<AuthUser>("/auth/me/");
    return response.data;
  },

  refreshToken: async (): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>("/auth/refresh/");
    const newAccessToken = (response.data as { data?: { tokens?: { access?: string } } })
      ?.data?.tokens?.access;
    if (newAccessToken) {
      setInMemoryAccessToken(newAccessToken);
    }
    return response.data;
  },

  verifyEmail: async (payload: VerifyEmailPayload): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>("/auth/verify-email/", payload);
    return response.data;
  },

  resendVerification: async (payload: ResendVerificationPayload): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>(
      "/auth/resend-verification/",
      payload
    );
    return response.data;
  },

  forgotPassword: async (payload: ForgotPasswordPayload): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>(
      "/auth/forgot-password/",
      payload
    );
    return response.data;
  },

  resetPassword: async (payload: ResetPasswordPayload): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>(
      "/auth/reset-password/",
      payload
    );
    return response.data;
  },
};

export default authApi;
