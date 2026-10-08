import { createBrowserRouter } from "react-router-dom";
import PublicLayout from "@/layouts/PublicLayout";
import AuthLayout from "@/layouts/AuthLayout";
import DashboardLayout from "@/layouts/DashboardLayout";

import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import VerifyEmailPage from "@/pages/VerifyEmailPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";

import ClinicPage from "@/pages/ClinicPage";
import DoctorPage from "@/pages/DoctorPage";
import PatientPage from "@/pages/PatientPage";
import AdminPage from "@/pages/AdminPage";

import { ProtectedRoute } from "@/features/auth";

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
      {
        path: "verify-email",
        element: <VerifyEmailPage />,
      },
      {
        path: "forgot-password",
        element: <ForgotPasswordPage />,
      },
      {
        path: "reset-password",
        element: <ResetPasswordPage />,
      },
    ],
  },
  {
    path: "clinic",
    element: (
      <ProtectedRoute allowedRoles={["CLINIC_OWNER", "STAFF"]}>
        <DashboardLayout roleTitle="Clinic SaaS Portal" />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <ClinicPage />,
      },
    ],
  },
  {
    path: "doctor",
    element: (
      <ProtectedRoute allowedRoles={["DOCTOR"]}>
        <DashboardLayout roleTitle="Doctor Practice Suite" />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DoctorPage />,
      },
    ],
  },
  {
    path: "patient",
    element: (
      <ProtectedRoute allowedRoles={["PATIENT"]}>
        <DashboardLayout roleTitle="Patient Portal" />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <PatientPage />,
      },
    ],
  },
  {
    path: "admin",
    element: (
      <ProtectedRoute allowedRoles={["SUPER_ADMIN"]}>
        <DashboardLayout roleTitle="Super Admin Controls" />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <AdminPage />,
      },
    ],
  },
]);

export default router;
