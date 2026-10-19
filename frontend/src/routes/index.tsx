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
import ClinicRegisterPage from "@/pages/clinic/ClinicRegisterPage";
import MyClinicsPage from "@/pages/clinic/MyClinicsPage";
import ClinicDetailPage from "@/pages/clinic/ClinicDetailPage";
import DoctorPage from "@/pages/DoctorPage";
import DoctorProfilePage from "@/pages/doctor/DoctorProfilePage";
import DoctorVerificationPage from "@/pages/doctor/DoctorVerificationPage";
import DoctorClinicsPage from "@/pages/doctor/DoctorClinicsPage";
import DoctorSchedulesPage from "@/pages/doctor/DoctorSchedulesPage";
import PatientPage from "@/pages/PatientPage";
import AdminPage from "@/pages/AdminPage";
import AdminClinicsPage from "@/pages/admin/AdminClinicsPage";
import AdminClinicDetailPage from "@/pages/admin/AdminClinicDetailPage";
import AdminDoctorsPage from "@/pages/admin/AdminDoctorsPage";
import AdminDoctorDetailPage from "@/pages/admin/AdminDoctorDetailPage";

import { ProtectedRoute } from "@/features/auth";

import DoctorSearchPage from "@/pages/discovery/DoctorSearchPage";
import DoctorDetailPage from "@/pages/discovery/DoctorDetailPage";
import ClinicSearchPage from "@/pages/discovery/ClinicSearchPage";
import PublicClinicDetailPage from "@/pages/discovery/PublicClinicDetailPage";

import AppointmentDetailPage from "@/pages/appointments/AppointmentDetailPage";
import PatientAppointmentsPage from "@/pages/appointments/PatientAppointmentsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <PublicLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "doctors",
        element: <DoctorSearchPage />,
      },
      {
        path: "doctors/:doctorId",
        element: <DoctorDetailPage />,
      },
      {
        path: "clinics",
        element: <ClinicSearchPage />,
      },
      {
        path: "clinics/:clinicId",
        element: <PublicClinicDetailPage />,
      },
      {
        path: "appointments/:appointmentId",
        element: <AppointmentDetailPage />,
      },
      {
        path: "my-appointments",
        element: (
          <ProtectedRoute allowedRoles={["PATIENT"]}>
            <PatientAppointmentsPage />
          </ProtectedRoute>
        ),
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
        element: <MyClinicsPage />,
      },
      {
        path: "dashboard",
        element: <ClinicPage />,
      },
      {
        path: "register",
        element: <ClinicRegisterPage />,
      },
      {
        path: "my-clinics",
        element: <MyClinicsPage />,
      },
      {
        path: "my-clinics/:id",
        element: <ClinicDetailPage />,
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
      {
        path: "profile",
        element: <DoctorProfilePage />,
      },
      {
        path: "verification",
        element: <DoctorVerificationPage />,
      },
      {
        path: "clinics",
        element: <DoctorClinicsPage />,
      },
      {
        path: "schedules",
        element: <DoctorSchedulesPage />,
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
      {
        path: "appointments",
        element: <PatientAppointmentsPage />,
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
      {
        path: "clinics",
        element: <AdminClinicsPage />,
      },
      {
        path: "clinics/:id",
        element: <AdminClinicDetailPage />,
      },
      {
        path: "doctors",
        element: <AdminDoctorsPage />,
      },
      {
        path: "doctors/:id",
        element: <AdminDoctorDetailPage />,
      },
    ],
  },
]);

export default router;
