import { createContext } from "react";
import type { Clinic } from "@/features/clinics/types";

export interface ClinicContextType {
  clinics: Clinic[];
  activeClinic: Clinic | null;
  activeClinicId: string;
  setActiveClinicId: (id: string) => void;
  isLoading: boolean;
}

export const ClinicContext = createContext<ClinicContextType>({
  clinics: [],
  activeClinic: null,
  activeClinicId: "",
  setActiveClinicId: () => {},
  isLoading: true,
});

