# EazyDoc — REST API Specification & Endpoint Blueprint

## 1. Global API Standards

- **Base URL:** `/api/v1/`
- **Content-Type:** `application/json` (except file uploads using `multipart/form-data`)
- **Authentication:** `Authorization: Bearer <jwt_access_token>`
- **Tenant Context Header (Optional/Multi-Clinic):** `X-Clinic-ID: <clinic_uuid>`
- **Response Format:**
  ```json
  {
    "success": true,
    "data": {},
    "meta": {
      "page": 1,
      "page_size": 20,
      "total_count": 105
    }
  }
  ```
- **Error Format:**
  ```json
  {
    "success": false,
    "error": {
      "code": "SLOT_ALREADY_BOOKED",
      "message": "The selected appointment slot has already been reserved.",
      "details": {}
    }
  }
  ```

---

## 2. API Modules & Endpoints

### 2.1. Authentication & User Profile (`/api/v1/auth/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register/` | Public | Register new user (Patient, Doctor, Clinic Owner) |
| `POST` | `/auth/verify-otp/` | Public | Verify OTP for phone/email activation |
| `POST` | `/auth/login/` | Public | Authenticate user, return JWT access + refresh cookie |
| `POST` | `/auth/token/refresh/` | Public (Cookie) | Rotate JWT access and refresh tokens |
| `POST` | `/auth/logout/` | Authenticated | Blacklist refresh token and clear auth cookies |
| `POST` | `/auth/forgot-password/` | Public | Send password reset OTP/link |
| `POST` | `/auth/reset-password/` | Public | Submit new password with reset token |
| `GET` | `/auth/me/` | Authenticated | Fetch current user profile, role, and permissions |
| `PATCH`| `/auth/me/` | Authenticated | Update user first name, last name, avatar |

---

### 2.2. Clinics & Practice Management (`/api/v1/clinics/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/clinics/` | Public | Search clinics by city, name, specialization |
| `GET` | `/clinics/{id}/` | Public | Public clinic profile, doctors, address, contact |
| `POST` | `/clinics/` | Clinic Owner | Register a new clinic (Status: `PENDING_VERIFICATION`) |
| `PATCH`| `/clinics/{id}/` | Clinic Owner | Update clinic details, address, phone, logo |
| `GET` | `/clinics/{id}/doctors/` | Public | List active doctors practicing at the clinic |
| `POST` | `/clinics/{id}/invite-doctor/` | Clinic Owner | Search doctor by Reg No and send clinic invite |
| `GET` | `/clinics/{id}/staff/` | Clinic Owner | List all clinic staff members |
| `POST` | `/clinics/{id}/staff/` | Clinic Owner | Invite/create receptionist or clinic staff |
| `DELETE`| `/clinics/{id}/staff/{staff_id}/` | Clinic Owner | Deactivate/remove clinic staff |
| `GET` | `/clinics/{id}/analytics/` | Clinic Owner | Clinic revenue, appointment volume, cancellation metrics |

---

### 2.3. Doctors & Specializations (`/api/v1/doctors/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/specializations/` | Public | List all medical specializations |
| `GET` | `/doctors/` | Public | Search verified doctors (by name, specialty, city) |
| `GET` | `/doctors/{id}/` | Public | Public doctor profile, qualifications, affiliated clinics |
| `POST` | `/doctors/profile/` | Doctor | Submit doctor credentials and Reg No for verification |
| `GET` | `/doctors/me/clinics/` | Doctor | List all affiliated clinics and pending invites |
| `PATCH`| `/doctors/invitations/{id}/accept/` | Doctor | Accept a clinic's association invite |
| `PATCH`| `/doctors/invitations/{id}/reject/` | Doctor | Decline a clinic's association invite |
| `GET` | `/doctors/me/master-schedule/` | Doctor | Unified multi-clinic weekly schedule view |

---

### 2.4. Doctor-Clinic Associations (`/api/v1/doctor-clinics/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/doctor-clinics/{id}/` | Owner / Doctor | View association details, fee, slot duration |
| `PATCH`| `/doctor-clinics/{id}/` | Owner / Doctor | Update `consultation_fee`, `appointment_duration` |
| `POST` | `/doctor-clinics/{id}/pause/` | Owner / Doctor | Temporarily pause bookings for this clinic |
| `POST` | `/doctor-clinics/{id}/terminate/` | Owner / Doctor | Terminate doctor-clinic association |

---

### 2.5. Schedules & Unavailability (`/api/v1/schedules/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/schedules/` | Authenticated | List shifts for a `doctor_clinic_id` |
| `POST` | `/schedules/` | Clinic Owner | Create a recurring weekly shift (conflict-checked) |
| `PUT` | `/schedules/{id}/` | Clinic Owner | Update shift start/end time (conflict-checked) |
| `DELETE`| `/schedules/{id}/` | Clinic Owner | Deactivate a shift |
| `POST` | `/schedules/check-conflict/` | Clinic Owner | Pre-validate shift timings against other clinics |
| `GET` | `/unavailability/` | Owner / Doctor | List doctor leave/unavailability periods |
| `POST` | `/unavailability/` | Owner / Doctor | Mark doctor unavailable (triggers fallout workflow) |
| `DELETE`| `/unavailability/{id}/` | Owner / Doctor | Cancel leave period |
| `POST` | `/blocked-slots/` | Staff / Owner | Block an individual time slot for a specific date |

---

### 2.6. Appointments & Booking Engine (`/api/v1/appointments/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/appointments/available-slots/` | Public | Query available time slots for Doctor + Clinic + Date |
| `POST` | `/appointments/hold-slot/` | Patient | Acquire temporary 10-minute hold token in Redis |
| `POST` | `/appointments/book/` | Patient | Create `PENDING` appointment and generate Razorpay Order |
| `GET` | `/appointments/` | Authenticated | List appointments (scoped: patient/doctor/clinic) |
| `GET` | `/appointments/{id}/` | Authenticated | Detailed appointment view |
| `POST` | `/appointments/{id}/cancel/` | Patient / Staff | Cancel appointment (enforces 11:59 PM deadline for patient) |
| `POST` | `/appointments/{id}/reschedule/` | Patient / Staff | Reschedule appointment to a new date/time slot |
| `POST` | `/appointments/{id}/check-in/` | Staff / Owner | Mark patient arrived; issue daily token number |
| `POST` | `/appointments/{id}/call/` | Doctor | Mark patient `IN_CONSULTATION` (broadcasts WS event) |
| `POST` | `/appointments/{id}/complete/` | Doctor | Mark consultation finished |

---

### 2.7. Payments & Financial Settlements (`/api/v1/payments/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/payments/verify/` | Patient | Verify Razorpay HMAC signature and confirm booking |
| `POST` | `/payments/webhook/` | Razorpay Server | Handle asynchronous Razorpay payment/refund events |
| `GET` | `/payments/{id}/receipt/` | Patient | Fetch downloadable payment receipt (gross fee only) |
| `GET` | `/payments/clinic-settlements/` | Clinic Owner | View clinic net earnings, commission ledger, settlements |
| `GET` | `/payments/admin-ledger/` | Super Admin | View platform commission aggregate and clinic payouts |

---

### 2.8. Consultations & Digital Prescriptions (`/api/v1/consultations/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/consultations/` | Doctor | Create consultation record (vitals, complaints, diagnosis) |
| `GET` | `/consultations/{id}/` | Doctor / Patient | View consultation details and notes |
| `POST` | `/prescriptions/` | Doctor | Create digital prescription with medicine items |
| `GET` | `/prescriptions/{id}/` | Doctor / Patient | View prescription details |
| `GET` | `/prescriptions/{id}/pdf/` | Doctor / Patient | Generate/download signed PDF prescription |

---

### 2.9. Medical Documents & Patient Records (`/api/v1/documents/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/documents/` | Patient / Doctor | List patient's uploaded medical records |
| `POST` | `/documents/upload-url/` | Patient | Request pre-signed S3 URL for secure direct upload |
| `POST` | `/documents/` | Patient | Confirm upload and save document metadata |
| `GET` | `/documents/{id}/download-url/` | Patient / Doctor | Generate 15-minute temporary pre-signed download URL |

---

### 2.10. Super Admin Management (`/api/v1/admin/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/clinics/pending/` | Super Admin | List clinics awaiting verification |
| `POST` | `/admin/clinics/{id}/verify/` | Super Admin | Verify and activate clinic |
| `POST` | `/admin/clinics/{id}/suspend/` | Super Admin | Suspend clinic from platform |
| `GET` | `/admin/doctors/pending/` | Super Admin | List doctors awaiting medical license check |
| `POST` | `/admin/doctors/{id}/verify/` | Super Admin | Verify doctor registration number |
| `GET` | `/admin/settings/` | Super Admin | List platform settings (commission %, etc.) |
| `PATCH`| `/admin/settings/{key}/` | Super Admin | Update platform setting value |
| `GET` | `/admin/audit-logs/` | Super Admin | Query immutable system audit logs |
