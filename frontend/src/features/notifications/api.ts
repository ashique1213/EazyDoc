import { apiClient } from "@/services/api";
import type {
  MarkAllReadResponse,
  MarkReadResponse,
  NotificationPreference,
  PaginatedNotifications,
  UnreadCountResponse,
} from "./types";

export const getNotifications = async (params?: {
  page?: number;
  unread?: boolean;
}): Promise<PaginatedNotifications> => {
  const query = new URLSearchParams();
  if (params?.page) {
    query.append("page", params.page.toString());
  }
  if (params?.unread) {
    query.append("unread", "true");
  }

  const queryString = query.toString();
  const url = queryString ? `/notifications/?${queryString}` : "/notifications/";
  const response = await apiClient.get<PaginatedNotifications>(url);
  return response.data;
};

export const getUnreadCount = async (): Promise<UnreadCountResponse> => {
  const response = await apiClient.get<UnreadCountResponse>("/notifications/unread-count/");
  return response.data;
};

export const markAsRead = async (notificationId: string): Promise<MarkReadResponse> => {
  const response = await apiClient.post<MarkReadResponse>(`/notifications/${notificationId}/read/`);
  return response.data;
};

export const markAllAsRead = async (): Promise<MarkAllReadResponse> => {
  const response = await apiClient.post<MarkAllReadResponse>("/notifications/read-all/");
  return response.data;
};

export const getNotificationPreferences = async (): Promise<NotificationPreference> => {
  const response = await apiClient.get<NotificationPreference>("/notifications/preferences/");
  return response.data;
};

export const updateNotificationPreferences = async (
  payload: Partial<NotificationPreference>
): Promise<NotificationPreference> => {
  const response = await apiClient.patch<NotificationPreference>("/notifications/preferences/", payload);
  return response.data;
};
