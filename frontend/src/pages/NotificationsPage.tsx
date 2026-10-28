import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  Calendar,
  CreditCard,
  Building2,
  Stethoscope,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Loader2,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useNotifications,
  useUnreadCount,
  useMarkAsRead,
  useMarkAllAsRead,
} from "@/features/notifications/hooks";
import NotificationPreferencesSection from "@/features/notifications/components/NotificationPreferencesSection";
import type { NotificationItem, NotificationType } from "@/features/notifications/types";

function formatDateTime(dateString: string): string {
  try {
    const d = new Date(dateString);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateString;
  }
}

function getNotificationTypeBadge(type: NotificationType) {
  if (type.startsWith("PAYMENT")) {
    return (
      <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border-emerald-200">
        Payment
      </Badge>
    );
  }
  if (type.startsWith("CLINIC")) {
    return (
      <Badge variant="outline" className="text-[10px] bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300 border-indigo-200">
        Clinic
      </Badge>
    );
  }
  if (type === "DOCTOR_UNAVAILABLE" || type === "APPOINTMENT_REQUIRES_ATTENTION") {
    return (
      <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border-amber-200">
        Action Required
      </Badge>
    );
  }
  if (type.startsWith("APPOINTMENT")) {
    return (
      <Badge variant="outline" className="text-[10px] bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300 border-sky-200">
        Appointment
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="text-[10px]">
      General
    </Badge>
  );
}

function getNotificationIcon(type: NotificationType) {
  if (type.startsWith("PAYMENT")) {
    return <CreditCard className="h-5 w-5 text-emerald-500 shrink-0" />;
  }
  if (type.startsWith("CLINIC")) {
    return <Building2 className="h-5 w-5 text-indigo-500 shrink-0" />;
  }
  if (type === "DOCTOR_UNAVAILABLE" || type === "APPOINTMENT_REQUIRES_ATTENTION") {
    return <AlertCircle className="h-5 w-5 text-amber-500 shrink-0" />;
  }
  if (type.startsWith("APPOINTMENT")) {
    return <Calendar className="h-5 w-5 text-sky-500 shrink-0" />;
  }
  return <Stethoscope className="h-5 w-5 text-primary shrink-0" />;
}

export function NotificationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const tabParam = searchParams.get("tab") || "all";
  const [activeTab, setActiveTab] = useState<"all" | "unread" | "preferences">(
    tabParam === "preferences" ? "preferences" : tabParam === "unread" ? "unread" : "all"
  );
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (tabParam === "preferences") setActiveTab("preferences");
    else if (tabParam === "unread") setActiveTab("unread");
    else setActiveTab("all");
  }, [tabParam]);

  const handleTabChange = (tab: "all" | "unread" | "preferences") => {
    setActiveTab(tab);
    setPage(1);
    setSearchParams(tab === "all" ? {} : { tab });
  };

  const isUnreadOnly = activeTab === "unread";
  const { data: notificationsData, isLoading, isError } = useNotifications(page, isUnreadOnly);
  const { data: unreadData } = useUnreadCount();
  const markAsReadMutation = useMarkAsRead();
  const markAllReadMutation = useMarkAllAsRead();

  const unreadCount = unreadData?.unread_count ?? notificationsData?.unread_count ?? 0;
  const notifications = notificationsData?.results ?? [];
  const totalCount = notificationsData?.count ?? 0;
  const totalPages = Math.ceil(totalCount / 20) || 1;

  const handleNotificationAction = (item: NotificationItem) => {
    if (!item.is_read) {
      markAsReadMutation.mutate(item.id);
    }
    if (item.action_url) {
      navigate(item.action_url);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center space-x-2">
            <span>Notification Center</span>
            {unreadCount > 0 && (
              <Badge variant="secondary" className="text-xs px-2 py-0.5 ml-2">
                {unreadCount} unread
              </Badge>
            )}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Stay updated with appointment schedules, payments, and clinic operations.
          </p>
        </div>

        {unreadCount > 0 && activeTab !== "preferences" && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => markAllReadMutation.mutate()}
            disabled={markAllReadMutation.isPending}
            className="gap-2"
          >
            {markAllReadMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCheck className="h-4 w-4 text-primary" />
            )}
            <span>Mark all as read</span>
          </Button>
        )}
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center space-x-2 border-b">
        <button
          type="button"
          onClick={() => handleTabChange("all")}
          className={`pb-3 px-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === "all"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          All Notifications
        </button>
        <button
          type="button"
          onClick={() => handleTabChange("unread")}
          className={`pb-3 px-3 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center space-x-1.5 ${
            activeTab === "unread"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <span>Unread</span>
          {unreadCount > 0 && (
            <span className="rounded-full bg-primary/15 text-primary text-[10px] px-1.5 py-0.2 font-bold">
              {unreadCount}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => handleTabChange("preferences")}
          className={`pb-3 px-3 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center space-x-1.5 ${
            activeTab === "preferences"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          <span>Preferences</span>
        </button>
      </div>

      {/* Tab Content: Preferences */}
      {activeTab === "preferences" ? (
        <div className="bg-card rounded-2xl border p-6 shadow-sm">
          <NotificationPreferencesSection />
        </div>
      ) : (
        /* Tab Content: Notifications List */
        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground space-y-3">
              <Loader2 className="h-7 w-7 animate-spin text-primary" />
              <span className="text-sm font-medium">Loading notifications...</span>
            </div>
          ) : isError ? (
            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-6 text-center text-sm text-destructive">
              Failed to load notifications. Please check your connection and refresh.
            </div>
          ) : notifications.length === 0 ? (
            <div className="rounded-2xl border bg-card p-12 text-center text-muted-foreground shadow-sm">
              <Bell className="mx-auto h-10 w-10 text-muted-foreground/30 mb-3" />
              <h3 className="text-base font-semibold text-foreground">
                {activeTab === "unread" ? "No unread notifications" : "No notifications yet"}
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
                {activeTab === "unread"
                  ? "You are all caught up! Check the 'All Notifications' tab to view earlier updates."
                  : "Updates about your appointment schedules, payment receipts, and clinics will appear here."}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {notifications.map((item) => (
                <div
                  key={item.id}
                  className={`rounded-xl border p-4 sm:p-5 transition-all shadow-sm ${
                    !item.is_read
                      ? "bg-card border-primary/30 shadow-primary/[0.02]"
                      : "bg-card/70 border-border/80"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start space-x-3.5 flex-1 min-w-0">
                      <div className="p-2.5 rounded-xl bg-muted/60 shrink-0 mt-0.5">
                        {getNotificationIcon(item.notification_type)}
                      </div>
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-sm font-bold text-foreground truncate">
                            {item.title}
                          </h4>
                          {getNotificationTypeBadge(item.notification_type)}
                          {!item.is_read && (
                            <Badge variant="default" className="text-[9px] py-0 px-1.5 h-4 bg-primary text-primary-foreground">
                              New
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-foreground/80 leading-relaxed">
                          {item.message}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          {formatDateTime(item.created_at)}
                        </p>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2 shrink-0">
                      {!item.is_read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => markAsReadMutation.mutate(item.id)}
                          disabled={markAsReadMutation.isPending}
                          className="h-8 text-xs text-muted-foreground hover:text-foreground"
                        >
                          Mark read
                        </Button>
                      )}
                      {item.action_url && (
                        <Button
                          size="sm"
                          onClick={() => handleNotificationAction(item)}
                          className="h-8 text-xs gap-1.5"
                        >
                          <span>View Details</span>
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t pt-4 px-2">
                  <span className="text-xs text-muted-foreground">
                    Page {page} of {totalPages} ({totalCount} total)
                  </span>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(p - 1, 1))}
                      disabled={page <= 1}
                      className="h-8 w-8 p-0"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                      disabled={page >= totalPages}
                      className="h-8 w-8 p-0"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default NotificationsPage;
