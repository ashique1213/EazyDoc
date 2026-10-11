import { Link } from "react-router-dom";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ClinicStatusBadge } from "./ClinicStatusBadge";
import type { Clinic } from "../types";
import { Building2, MapPin, Phone, Mail, ArrowRight, Send, AlertTriangle } from "lucide-react";

interface ClinicCardProps {
  clinic: Clinic;
  onSubmitForVerification?: (id: string) => void;
  isSubmitting?: boolean;
}

export function ClinicCard({
  clinic,
  onSubmitForVerification,
  isSubmitting = false,
}: ClinicCardProps) {
  return (
    <Card className="flex flex-col overflow-hidden border transition-all duration-200 hover:shadow-md">
      <CardHeader className="p-5 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center space-x-3">
            {clinic.logo ? (
              <img
                src={clinic.logo}
                alt={clinic.name}
                className="h-11 w-11 rounded-lg border object-cover"
              />
            ) : (
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Building2 className="h-6 w-6" />
              </div>
            )}
            <div>
              <h3 className="font-semibold text-base leading-tight text-foreground line-clamp-1">
                {clinic.name}
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">/{clinic.slug}</p>
            </div>
          </div>
          <ClinicStatusBadge status={clinic.status} />
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-5 pt-2 space-y-3 text-xs text-muted-foreground">
        <div className="flex items-center space-x-2">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">
            {clinic.city}, {clinic.state} — {clinic.pincode}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-1 border-t">
          <div className="flex items-center space-x-1.5 truncate">
            <Mail className="h-3 w-3 shrink-0" />
            <span className="truncate">{clinic.email}</span>
          </div>
          <div className="flex items-center space-x-1.5 truncate">
            <Phone className="h-3 w-3 shrink-0" />
            <span className="truncate">{clinic.phone}</span>
          </div>
        </div>

        {clinic.status === "REJECTED" && clinic.verification_notes && (
          <div className="rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 p-2.5 text-xs text-rose-700 dark:text-rose-300">
            <div className="flex items-center space-x-1 font-semibold mb-0.5">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <span>Feedback from Admin:</span>
            </div>
            <p className="line-clamp-2 text-[11px]">{clinic.verification_notes}</p>
          </div>
        )}
      </CardContent>

      <CardFooter className="p-4 pt-2 border-t bg-muted/20 flex items-center justify-between gap-2">
        {(clinic.status === "DRAFT" || clinic.status === "REJECTED") && onSubmitForVerification ? (
          <Button
            size="sm"
            variant="outline"
            className="text-xs gap-1 text-primary border-primary/30 hover:bg-primary/10"
            onClick={() => onSubmitForVerification(clinic.id)}
            disabled={isSubmitting}
          >
            <Send className="h-3 w-3" />
            {clinic.status === "REJECTED" ? "Resubmit" : "Submit"}
          </Button>
        ) : (
          <span className="text-[11px] text-muted-foreground">
            Added {new Date(clinic.created_at).toLocaleDateString()}
          </span>
        )}

        <Link to={`/clinic/my-clinics/${clinic.id}`}>
          <Button size="sm" variant="default" className="text-xs gap-1">
            Manage
            <ArrowRight className="h-3 w-3" />
          </Button>
        </Link>
      </CardFooter>
    </Card>
  );
}
