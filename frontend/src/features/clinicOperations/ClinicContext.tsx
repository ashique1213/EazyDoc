import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMyClinics } from "@/features/clinics/api";
import { ClinicContext } from "./context";

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
