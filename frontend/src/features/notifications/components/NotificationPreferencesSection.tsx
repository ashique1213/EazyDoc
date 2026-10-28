import { useState, useEffect } from "react";
import {
  Bell,
  Mail,
  Clock,
  Calendar,
  CreditCard,
  Building2,
  ShieldCheck,
  Check,
  Loader2,
} from "lucide-react";
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
} from "../hooks";

interface PreferenceItemProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (val: boolean) => void;
}

function PreferenceToggle({
  icon,
  title,
  description,
  checked,
  disabled = false,
  onChange,
}: PreferenceItemProps) {
  return (
    <div className="flex items-start justify-between p-4 rounded-xl border bg-card hover:bg-muted/10 transition-colors">
      <div className="flex items-start space-x-3.5 pr-4">
        <div className="p-2 rounded-lg bg-muted shrink-0 text-foreground">
          {icon}
        </div>
        <div>
          <h4 className="text-sm font-semibold text-foreground">{title}</h4>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            {description}
          </p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
          checked ? "bg-primary" : "bg-muted-foreground/30"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}

export function NotificationPreferencesSection() {
  const { data: preferences, isLoading, isError } = useNotificationPreferences();
  const updateMutation = useUpdateNotificationPreferences();

  const [formState, setFormState] = useState({
    email_enabled: true,
    in_app_enabled: true,
    appointment_reminders_enabled: true,
    appointment_updates_enabled: true,
    payment_updates_enabled: true,
    clinic_announcements_enabled: true,
  });

  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    if (preferences) {
      setFormState({
        email_enabled: preferences.email_enabled,
        in_app_enabled: preferences.in_app_enabled,
        appointment_reminders_enabled: preferences.appointment_reminders_enabled,
        appointment_updates_enabled: preferences.appointment_updates_enabled,
        payment_updates_enabled: preferences.payment_updates_enabled,
        clinic_announcements_enabled: preferences.clinic_announcements_enabled,
      });
    }
  }, [preferences]);

  const handleToggle = (key: keyof typeof formState, val: boolean) => {
    const nextState = { ...formState, [key]: val };
    setFormState(nextState);

    updateMutation.mutate(
      { [key]: val },
      {
        onSuccess: () => {
          setSavedNotice(true);
          setTimeout(() => setSavedNotice(false), 3000);
        },
      }
    );
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground space-y-3">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="text-sm">Loading notification preferences...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 rounded-xl border border-destructive/20 bg-destructive/10 text-xs text-destructive">
        Failed to load preferences. Please try refreshing the page.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b pb-4">
        <div>
          <h3 className="text-lg font-bold text-foreground">Notification Preferences</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Choose how and when EazyDoc delivers updates to your account.
          </p>
        </div>
        {savedNotice && (
          <div className="flex items-center space-x-1.5 text-xs text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-3 py-1.5 rounded-lg border border-emerald-200">
            <Check className="h-3.5 w-3.5" />
            <span>Preferences saved</span>
          </div>
        )}
      </div>

      {/* Mandatory Operational Alerts Notice */}
      <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 flex items-start space-x-3 text-xs text-foreground">
        <ShieldCheck className="h-5 w-5 text-primary shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-primary">Essential Security & Account Notices</p>
          <p className="text-muted-foreground leading-relaxed">
            Critical transaction verifications, password resets, and account security notifications
            are mandatory to keep your medical practice and patient bookings secure and cannot be disabled.
          </p>
        </div>
      </div>

      {/* Channels Section */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Delivery Channels
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <PreferenceToggle
            icon={<Bell className="h-4 w-4" />}
            title="In-App Notifications"
            description="Receive alerts inside the EazyDoc navigation bar and notification bell."
            checked={formState.in_app_enabled}
            onChange={(val) => handleToggle("in_app_enabled", val)}
          />
          <PreferenceToggle
            icon={<Mail className="h-4 w-4" />}
            title="Email Notifications"
            description="Receive operational confirmations and summaries sent to your verified email."
            checked={formState.email_enabled}
            onChange={(val) => handleToggle("email_enabled", val)}
          />
        </div>
      </div>

      {/* Categories Section */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Event Categories
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <PreferenceToggle
            icon={<Clock className="h-4 w-4 text-sky-500" />}
            title="Upcoming Reminders"
            description="Reminders sent 24 hours and 2 hours prior to scheduled consultations."
            checked={formState.appointment_reminders_enabled}
            onChange={(val) => handleToggle("appointment_reminders_enabled", val)}
          />
          <PreferenceToggle
            icon={<Calendar className="h-4 w-4 text-emerald-500" />}
            title="Appointment Lifecycle"
            description="Booking confirmations, rescheduling notices, and cancellation updates."
            checked={formState.appointment_updates_enabled}
            onChange={(val) => handleToggle("appointment_updates_enabled", val)}
          />
          <PreferenceToggle
            icon={<CreditCard className="h-4 w-4 text-purple-500" />}
            title="Payment & Billing"
            description="Payment verification receipts and settlement dispute alerts."
            checked={formState.payment_updates_enabled}
            onChange={(val) => handleToggle("payment_updates_enabled", val)}
          />
          <PreferenceToggle
            icon={<Building2 className="h-4 w-4 text-indigo-500" />}
            title="Clinic & Practice Alerts"
            description="Doctor invitations, schedule changes, and clinic administrative updates."
            checked={formState.clinic_announcements_enabled}
            onChange={(val) => handleToggle("clinic_announcements_enabled", val)}
          />
        </div>
      </div>
    </div>
  );
}

export default NotificationPreferencesSection;
