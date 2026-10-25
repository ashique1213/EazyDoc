import React, { createContext, useContext, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMyClinics } from "@/features/clinics/api";
import type { Clinic } from "@/features/clinics/types";
import { Building2, ChevronDown, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ClinicContextType {
  clinics: Clinic[];
  activeClinic: Clinic | null;
  activeClinicId: string;
  setActiveClinicId: (id: string) => void;
  isLoading: boolean;
}

const ClinicContext = createContext<ClinicContextType>({
  clinics: [],
  activeClinic: null,
  activeClinicId: "",
  setActiveClinicId: () => {},
  isLoading: true,
});

export const ClinicProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { data: clinics = [], isLoading } = useQuery({
    queryKey: ["my-clinics"],
    queryFn: getMyClinics,
  });

  const [activeClinicId, setActiveClinicIdState] = useState<string>(() => {
    return sessionStorage.getItem("eazydoc_active_clinic_id") || "";
  });

  useEffect(() => {
    if (clinics.length > 0) {
      const exists = clinics.some((c) => c.id === activeClinicId);
      if (!activeClinicId || !exists) {
        const approved = clinics.find((c) => c.status === "APPROVED") || clinics[0];
        setActiveClinicIdState(approved.id);
        sessionStorage.setItem("eazydoc_active_clinic_id", approved.id);
      }
    }
  }, [clinics, activeClinicId]);

  const setActiveClinicId = (id: string) => {
    setActiveClinicIdState(id);
    sessionStorage.setItem("eazydoc_active_clinic_id", id);
  };

  const activeClinic = clinics.find((c) => c.id === activeClinicId) || null;

  return (
    <ClinicContext.Provider
      value={{
        clinics,
        activeClinic,
        activeClinicId,
        setActiveClinicId,
        isLoading,
      }}
    >
      {children}
    </ClinicContext.Provider>
  );
};

export const useActiveClinic = () => useContext(ClinicContext);

export const ClinicSwitcher: React.FC = () => {
  const { clinics, activeClinic, setActiveClinicId, isLoading } = useActiveClinic();
  const [open, setOpen] = useState(false);

  if (isLoading || clinics.length === 0) {
    return null;
  }

  return (
    <div className="relative inline-block text-left">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(!open)}
        className="flex items-center space-x-2 border-primary/20 bg-card hover:bg-accent/50 text-xs font-medium"
      >
        <Building2 className="h-3.5 w-3.5 text-primary" />
        <span className="max-w-[140px] truncate">{activeClinic?.name || "Select Clinic"}</span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 w-56 origin-top-right rounded-lg border bg-popover p-1 shadow-lg z-50">
            <div className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Your Facilities ({clinics.length})
            </div>
            {clinics.map((clinic) => {
              const isSelected = clinic.id === activeClinic?.id;
              return (
                <button
                  key={clinic.id}
                  onClick={() => {
                    setActiveClinicId(clinic.id);
                    setOpen(false);
                  }}
                  className={`w-full flex items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors ${
                    isSelected
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "text-foreground hover:bg-accent"
                  }`}
                >
                  <div className="flex flex-col text-left truncate mr-2">
                    <span className="truncate">{clinic.name}</span>
                    <span className={`text-[10px] ${isSelected ? "text-primary-foreground/80" : "text-muted-foreground"}`}>
                      {clinic.city} ({clinic.status})
                    </span>
                  </div>
                  {isSelected && <Check className="h-3.5 w-3.5 shrink-0" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
