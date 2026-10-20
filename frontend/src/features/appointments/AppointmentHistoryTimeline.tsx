import {
  CheckCircle2,
  AlertCircle,
  User,
  History,
  RotateCcw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAppointmentHistory } from "./hooks";

interface AppointmentHistoryTimelineProps {
  appointmentId: string;
}

function getEventBadge(eventType: string) {
  switch (eventType) {
    case "CREATED":
      return (
        <Badge variant="outline" className="text-emerald-700 bg-emerald-500/10 border-emerald-500/30 gap-1 text-[11px]">
          <CheckCircle2 className="h-3 w-3" />
          <span>Created</span>
        </Badge>
      );
    case "PATIENT_CANCELLED":
    case "CLINIC_CANCELLED":
      return (
        <Badge variant="outline" className="text-destructive bg-destructive/10 border-destructive/30 gap-1 text-[11px]">
          <AlertCircle className="h-3 w-3" />
          <span>Cancelled</span>
        </Badge>
      );
    case "RESCHEDULED":
      return (
        <Badge variant="outline" className="text-blue-700 bg-blue-500/10 border-blue-500/30 gap-1 text-[11px]">
          <RotateCcw className="h-3 w-3" />
          <span>Rescheduled</span>
        </Badge>
      );
    case "DOCTOR_UNAVAILABLE":
      return (
        <Badge variant="outline" className="text-amber-700 bg-amber-500/10 border-amber-500/30 gap-1 text-[11px]">
          <AlertCircle className="h-3 w-3" />
          <span>Doctor Unavailable</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-[11px]">
          <span>{eventType}</span>
        </Badge>
      );
  }
}

export function AppointmentHistoryTimeline({ appointmentId }: AppointmentHistoryTimelineProps) {
  const { data: history, isLoading, isError } = useAppointmentHistory(appointmentId);

  if (isLoading) {
    return (
      <div className="p-4 text-center text-xs text-muted-foreground animate-pulse">
        Loading appointment audit trail...
      </div>
    );
  }

  if (isError || !history || history.length === 0) {
    return (
      <div className="rounded-xl border border-border/60 bg-muted/20 p-4 text-center text-xs text-muted-foreground">
        No historical audit events recorded yet for this appointment.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
        <History className="h-4 w-4 text-primary" />
        <span>Appointment Lifecycle History ({history.length})</span>
      </div>

      <div className="relative border-l-2 border-border ml-3 pl-4 space-y-4">
        {history.map((entry) => {
          const timestamp = new Date(entry.created_at).toLocaleString("en-IN", {
            dateStyle: "medium",
            timeStyle: "short",
          });

          return (
            <div key={entry.id} className="relative group">
              {/* Dot */}
              <div className="absolute -left-[23px] top-1 h-3.5 w-3.5 rounded-full border-2 border-background bg-primary" />

              <div className="rounded-xl border border-border/70 bg-card p-3 space-y-2 shadow-sm text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {getEventBadge(entry.event_type)}
                    {entry.is_exception && (
                      <Badge className="bg-purple-500/10 text-purple-700 border-purple-500/30 text-[10px] py-0 px-1.5">
                        Authorized Exception
                      </Badge>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground">{timestamp}</span>
                </div>

                {/* Actor & Role */}
                <div className="flex items-center gap-2 text-muted-foreground text-[11px]">
                  <span className="flex items-center gap-1 text-foreground font-semibold">
                    <User className="h-3 w-3 text-primary" /> {entry.actor_name}
                  </span>
                  <span>({entry.actor_role})</span>
                </div>

                {/* Reschedule timestamps change */}
                {entry.new_start_at && entry.previous_start_at && entry.new_start_at !== entry.previous_start_at && (
                  <div className="bg-muted/40 p-2 rounded-lg text-[11px] space-y-0.5 font-mono text-muted-foreground">
                    <div>
                      From: {new Date(entry.previous_start_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                    </div>
                    <div className="text-foreground font-bold">
                      To: {new Date(entry.new_start_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                    </div>
                  </div>
                )}

                {/* Reason note */}
                {entry.reason && (
                  <p className="text-muted-foreground italic text-[11px] bg-muted/20 p-2 rounded-lg border border-border/40">
                    "{entry.reason}"
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
