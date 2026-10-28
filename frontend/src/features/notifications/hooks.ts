import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getNotificationPreferences,
  getNotifications,
  getUnreadCount,
  markAllAsRead,
  markAsRead,
  updateNotificationPreferences,
} from "./api";
import type { NotificationPreference } from "./types";

export const NOTIFICATIONS_QUERY_KEY = ["notifications"];
export const UNREAD_COUNT_QUERY_KEY = ["notifications", "unread-count"];
export const PREFERENCES_QUERY_KEY = ["notifications", "preferences"];

export const useNotifications = (page = 1, unreadOnly = false) => {
  return useQuery({
    queryKey: [...NOTIFICATIONS_QUERY_KEY, page, unreadOnly],
    queryFn: () => getNotifications({ page, unread: unreadOnly }),
    staleTime: 10000,
  });
};

export const useUnreadCount = (enabled = true) => {
  return useQuery({
    queryKey: UNREAD_COUNT_QUERY_KEY,
    queryFn: getUnreadCount,
    enabled,
    refetchInterval: 30000, // Background check every 30s
    refetchOnWindowFocus: true,
  });
};

export const useMarkAsRead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => markAsRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_QUERY_KEY });
    },
  });
};

export const useMarkAllAsRead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: markAllAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_QUERY_KEY });
    },
  });
};

export const useNotificationPreferences = () => {
  return useQuery({
    queryKey: PREFERENCES_QUERY_KEY,
    queryFn: getNotificationPreferences,
  });
};

export const useUpdateNotificationPreferences = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Partial<NotificationPreference>) => updateNotificationPreferences(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(PREFERENCES_QUERY_KEY, updated);
    },
  });
};
