import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "./api";
import { useAuthStore } from "./auth-store";
import type {
  ForgotPasswordPayload,
  LoginPayload,
  RegisterPayload,
  ResendVerificationPayload,
  ResetPasswordPayload,
  UserRole,
  VerifyEmailPayload,
} from "./types";

export const getRoleRedirectPath = (role?: UserRole): string => {
  switch (role) {
    case "SUPER_ADMIN":
      return "/admin";
    case "CLINIC_OWNER":
    case "STAFF":
      return "/clinic";
    case "DOCTOR":
      return "/doctor";
    case "PATIENT":
    default:
      return "/patient";
  }
};

export const useCurrentUser = () => {
  const { setUser, clearAuth } = useAuthStore();

  return useQuery({
    queryKey: ["auth", "currentUser"],
    queryFn: async () => {
      try {
        const user = await authApi.getCurrentUser();
        setUser(user);
        return user;
      } catch (error) {
        clearAuth();
        throw error;
      }
    },
    retry: false,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useLogin = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setUser } = useAuthStore();

  return useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: (response) => {
      const user = response.data?.user;
      if (user) {
        setUser(user);
        queryClient.setQueryData(["auth", "currentUser"], user);
        navigate(getRoleRedirectPath(user.role), { replace: true });
      }
    },
  });
};

export const useRegister = () => {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => authApi.register(payload),
  });
};

export const useLogout = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { clearAuth } = useAuthStore();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      clearAuth();
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  });
};

export const useVerifyEmail = () => {
  return useMutation({
    mutationFn: (payload: VerifyEmailPayload) => authApi.verifyEmail(payload),
  });
};

export const useResendVerification = () => {
  return useMutation({
    mutationFn: (payload: ResendVerificationPayload) => authApi.resendVerification(payload),
  });
};

export const useForgotPassword = () => {
  return useMutation({
    mutationFn: (payload: ForgotPasswordPayload) => authApi.forgotPassword(payload),
  });
};

export const useResetPassword = () => {
  return useMutation({
    mutationFn: (payload: ResetPasswordPayload) => authApi.resetPassword(payload),
  });
};
