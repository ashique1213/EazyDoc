import { create } from "zustand";
import type { AuthUser, UserRole } from "./types";
import { authApi } from "./api";

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  setUser: (user: AuthUser | null) => void;
  clearAuth: () => void;
  checkAuth: () => Promise<AuthUser | null>;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isInitialized: false,

  setUser: (user) => {
    set({
      user,
      isAuthenticated: Boolean(user),
      isLoading: false,
      isInitialized: true,
    });
  },

  clearAuth: () => {
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isInitialized: true,
    });
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const user = await authApi.getCurrentUser();
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        isInitialized: true,
      });
      return user;
    } catch {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        isInitialized: true,
      });
      return null;
    }
  },

  hasRole: (roles) => {
    const { user } = get();
    if (!user) return false;
    const roleList = Array.isArray(roles) ? roles : [roles];
    return roleList.includes(user.role);
  },
}));

// Listen to session expired event triggered by 401 interceptor
if (typeof window !== "undefined") {
  window.addEventListener("eazydoc:session-expired", () => {
    useAuthStore.getState().clearAuth();
  });
}

export default useAuthStore;
