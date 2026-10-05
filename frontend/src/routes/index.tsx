import { createBrowserRouter } from "react-router-dom";
import PublicLayout from "@/layouts/PublicLayout";
import AuthLayout from "@/layouts/AuthLayout";
import DashboardLayout from "@/layouts/DashboardLayout";

import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import ClinicPage from "@/pages/ClinicPage";
import DoctorPage from "@/pages/DoctorPage";
import PatientPage from "@/pages/PatientPage";
import AdminPage from "@/pages/AdminPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <PublicLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
    ],
  },
  {
    element: <AuthLayout />,
    children: [
      {
        path: "login",
        element: <LoginPage />,
      },
      {
        path: "register",
        element: <RegisterPage />,
      },
    ],
  },
  {
    path: "clinic",
    element: <DashboardLayout roleTitle="Clinic SaaS Portal" />,
    children: [
      {
        index: true,
        element: <ClinicPage />,
      },
    ],
  },
  {
    path: "doctor",
    element: <DashboardLayout roleTitle="Doctor Practice Suite" />,
    children: [
      {
        index: true,
        element: <DoctorPage />,
      },
    ],
  },
  {
    path: "patient",
    element: <DashboardLayout roleTitle="Patient Portal" />,
    children: [
      {
        index: true,
        element: <PatientPage />,
      },
    ],
  },
  {
    path: "admin",
    element: <DashboardLayout roleTitle="Super Admin Controls" />,
    children: [
      {
        index: true,
        element: <AdminPage />,
      },
    ],
  },
]);

export default router;
