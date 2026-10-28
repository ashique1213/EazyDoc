export type NotificationType =
  | "APPOINTMENT_CONFIRMED"
  | "APPOINTMENT_PENDING"
  | "APPOINTMENT_REMINDER"
  | "APPOINTMENT_CANCELLED"
  | "APPOINTMENT_RESCHEDULED"
  | "DOCTOR_UNAVAILABLE"
  | "CLINIC_CLOSURE"
  | "APPOINTMENT_REQUIRES_ATTENTION"
  | "APPOINTMENT_COMPLETED"
  | "PAYMENT_VERIFIED"
  | "PAYMENT_FAILED"
  | "PAYMENT_PENDING"
  | "PAYMENT_ISSUE"
  | "CLINIC_INVITATION_SENT"
  | "CLINIC_INVITATION_ACCEPTED"
  | "CLINIC_INVITATION_REJECTED";

export interface NotificationItem {
  id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  related_object_type: string;
  related_object_id: string;
  action_url: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface PaginatedNotifications {
  count: number;
  next: string | null;
  previous: string | null;
  unread_count?: number;
  results: NotificationItem[];
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface NotificationPreference {
  email_enabled: boolean;
  in_app_enabled: boolean;
  appointment_reminders_enabled: boolean;
  appointment_updates_enabled: boolean;
  payment_updates_enabled: boolean;
  clinic_announcements_enabled: boolean;
  updated_at: string;
}

export interface MarkReadResponse {
  success: boolean;
  message: string;
  notification?: NotificationItem;
}

export interface MarkAllReadResponse {
  success: boolean;
  message: string;
  marked_read_count: number;
}
