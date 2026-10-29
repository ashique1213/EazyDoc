import { useContext } from "react";
import { ClinicContext } from "./context";

export const useActiveClinic = () => useContext(ClinicContext);
