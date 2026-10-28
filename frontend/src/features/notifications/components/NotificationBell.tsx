import { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  Calendar,
  CreditCard,
  Building2,
  Stethoscope,
  AlertCircle,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  useNotifications,
  useUnreadCount,
  useMarkAsRead,
  useMarkAllAsRead,
} from "../hooks";
import type { NotificationItem, NotificationType } from "../types";

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) return "Just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

function getNotificationIcon(type: NotificationType) {
  if (type.startsWith("PAYMENT")) {
    return <CreditCard className="h-4 w-4 text-emerald-500 shrink-0" />;
  }
  if (type.startsWith("CLINIC")) {
    return <Building2 className="h-4 w-4 text-indigo-500 shrink-0" />;
  }
  if (type === "DOCTOR_UNAVAILABLE" || type === "APPOINTMENT_REQUIRES_ATTENTION") {
    return <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />;
  }
  if (type.startsWith("APPOINTMENT")) {
    return <Calendar className="h-4 w-4 text-sky-500 shrink-0" />;
  }
  return <Stethoscope className="h-4 w-4 text-primary shrink-0" />;
}

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const { data: unreadData } = useUnreadCount();
  const { data: notificationsData, isLoading, isError } = useNotifications(1, false);
  const markAsReadMutation = useMarkAsRead();
  const markAllReadMutation = useMarkAllAsRead();

  const unreadCount = unreadData?.unread_count ?? notificationsData?.unread_count ?? 0;
  const recentNotifications = (notificationsData?.results ?? []).slice(0, 5);

  // Close popover when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleNotificationClick = (item: NotificationItem) => {
    if (!item.is_read) {
      markAsReadMutation.mutate(item.id);
    }
    setIsOpen(false);
    if (item.action_url) {
      navigate(item.action_url);
    }
  };

  const handleMarkAllRead = () => {
    markAllReadMutation.mutate();
  };

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      {/* Bell Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label="Open notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded-lg border bg-card text-muted-foreground hover:bg-accent hover:text-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground shadow-sm">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl border bg-card p-0 shadow-xl z-50 animate-in fade-in-0 zoom-in-95 duration-100">
          {/* Header */}
          <div className="flex items-center justify-between border-b px-4 py-3 bg-muted/30 rounded-t-xl">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold text-foreground">Notifications</span>
              {unreadCount > 0 && (
                <Badge variant="secondary" className="text-[10px] py-0 px-1.5 h-4">
                  {unreadCount} new
                </Badge>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                disabled={markAllReadMutation.isPending}
                className="flex items-center space-x-1 text-xs text-primary hover:underline font-medium disabled:opacity-50"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                <span>Mark all read</span>
              </button>
            )}
          </div>

          {/* Notification List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-border">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground space-y-2">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="text-xs">Loading notifications...</span>
              </div>
            ) : isError ? (
              <div className="py-6 px-4 text-center text-xs text-destructive">
                Failed to load notifications. Please try again.
              </div>
            ) : recentNotifications.length === 0 ? (
              <div className="py-8 px-4 text-center text-muted-foreground">
                <Bell className="mx-auto h-7 w-7 text-muted-foreground/40 mb-2" />
                <p className="text-xs font-medium text-foreground">No notifications yet</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  We will notify you about your appointments, payments, and clinic updates.
                </p>
              </div>
            ) : (
              recentNotifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleNotificationClick(item)}
                  className={`flex items-start space-x-3 p-3.5 cursor-pointer transition-colors hover:bg-accent/60 ${
                    !item.is_read ? "bg-primary/[0.04]" : ""
                  }`}
                >
                  <div className="mt-0.5 rounded-full p-1.5 bg-muted/60">
                    {getNotificationIcon(item.notification_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1 mb-0.5">
                      <p className={`text-xs truncate ${!item.is_read ? "font-semibold text-foreground" : "font-medium text-foreground/80"}`}>
                        {item.title}
                      </p>
                      <span className="text-[10px] text-muted-foreground shrink-0">
                        {formatRelativeTime(item.created_at)}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                      {item.message}
                    </p>
                  </div>
                  {!item.is_read && (
                    <div className="h-2 w-2 rounded-full bg-primary shrink-0 self-center" />
                  )}
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t p-2.5 bg-muted/20 rounded-b-xl flex items-center justify-between text-xs">
            <Link
              to="/notifications"
              onClick={() => setIsOpen(false)}
              className="flex items-center space-x-1 font-medium text-primary hover:underline px-2 py-1 rounded"
            >
              <span>View all notifications</span>
              <ExternalLink className="h-3 w-3" />
            </Link>
            <Link
              to="/notifications?tab=preferences"
              onClick={() => setIsOpen(false)}
              className="text-muted-foreground hover:text-foreground px-2 py-1 transition-colors"
            >
              Settings
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationBell;
