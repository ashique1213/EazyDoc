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

### 2.2. Clinics & Practice Management (`/api/v1/clinics/` & `/api/v1/admin/clinics/`)

#### 2.2.1. Clinic Owner Endpoints
| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/clinics/` | Clinic Owner | Register clinic owned by auth user (Status: `PENDING` or `DRAFT`) |
| `GET` | `/clinics/my-clinics/` | Clinic Owner | List only clinics owned by authenticated user |
| `GET` | `/clinics/{id}/` | Owner / Super Admin | Retrieve clinic details with tenant isolation |
| `PATCH`| `/clinics/{id}/` | Clinic Owner | Update permitted profile fields (name, phone, address, logo, etc.) |
| `POST` | `/clinics/{id}/submit/` | Clinic Owner | Submit `DRAFT` or `REJECTED` clinic for Super Admin verification |

#### 2.2.2. Super Admin Verification Endpoints
| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/clinics/` | Super Admin | List all clinics with status filtering and search pagination |
| `GET` | `/admin/clinics/{id}/` | Super Admin | Inspect full clinic details, owner info, and verification notes |
| `POST` | `/admin/clinics/{id}/approve/` | Super Admin | Approve pending clinic (Owner cannot self-approve) |
| `POST` | `/admin/clinics/{id}/reject/` | Super Admin | Reject pending clinic with mandatory feedback reason |
| `POST` | `/admin/clinics/{id}/suspend/` | Super Admin | Suspend approved clinic with mandatory reason |
| `POST` | `/admin/clinics/{id}/reactivate/` | Super Admin | Reactivate suspended clinic back to `APPROVED` |

---

### 2.3. Doctors & Verification Management (`/api/v1/doctors/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/doctors/profile/` | Doctor | Create initial practitioner profile in `DRAFT` status |
| `GET` | `/doctors/me/` | Doctor | Retrieve authenticated practitioner's full profile and verification status |
| `PATCH`| `/doctors/me/` | Doctor | Update permitted profile fields (qualifications, experience, bio, languages, photo) |
| `POST` | `/doctors/me/submit-verification/` | Doctor | Submit/resubmit completed profile for Super Admin verification review |
| `GET` | `/doctors/me/documents/` | Doctor | List private uploaded verification evidence documents |
| `POST` | `/doctors/me/documents/` | Doctor | Upload private registration certificate or qualification proof (max 5MB) |
| `DELETE`| `/doctors/me/documents/{id}/` | Doctor | Remove uploaded verification document |
| `GET` | `/doctors/me/documents/{id}/download/` | Doctor | Securely stream private verification document |
| `GET` | `/doctors/registration-lookup/` | Clinic Owner / Admin | Privacy-preserving lookup by registration number & council |
| `GET` | `/doctors/specializations/` | Authenticated | List medical specialization catalog |
| `GET` | `/doctors/` | Public | Search verified doctors (by name, specialty, city) [Future] |
| `GET` | `/doctors/{id}/` | Public | Public doctor profile, qualifications, affiliated clinics [Future] |
| `GET` | `/doctors/me/clinics/` | Doctor | List all affiliated clinics and pending invites [Future] |
| `PATCH`| `/doctors/invitations/{id}/accept/` | Doctor | Accept a clinic's association invite [Future] |
| `PATCH`| `/doctors/invitations/{id}/reject/` | Doctor | Decline a clinic's association invite [Future] |
| `GET` | `/doctors/me/master-schedule/` | Doctor | Unified multi-clinic weekly schedule view [Future] |

#### Super Admin Doctor Oversight (`/api/v1/admin/doctors/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/admin/doctors/` | Super Admin | List all doctor profiles with status filtering and keyword search (paginated) |
| `GET` | `/admin/doctors/{id}/` | Super Admin | View full doctor profile, credentials, verification audit trail, and documents |
| `POST` | `/admin/doctors/{id}/verify/` | Super Admin | Approve pending doctor (records `verified_by` and `verified_at`) |
| `POST` | `/admin/doctors/{id}/reject/` | Super Admin | Reject pending doctor with mandatory reason for resubmission |
| `POST` | `/admin/doctors/{id}/suspend/` | Super Admin | Suspend active doctor with mandatory justification reason |
| `POST` | `/admin/doctors/{id}/reactivate/` | Super Admin | Reactivate suspended doctor back to `VERIFIED` |
| `GET` | `/admin/doctors/{id}/documents/{doc_id}/download/` | Super Admin | Securely stream and inspect private verification document |

---

### 2.4. Doctor-Clinic Associations (`/api/v1/clinics/...` & `/api/v1/doctors/...`)

#### Clinic Owner Endpoints
| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/clinics/{clinic_id}/doctors/` | Clinic Owner / Super Admin | List doctors affiliated with clinic and their statuses (filter `?status=`) |
| `POST` | `/clinics/{clinic_id}/doctor-invitations/` | Clinic Owner / Super Admin | Invite verified doctor to approved clinic (handles safe re-invitation) |
| `GET` | `/clinics/{clinic_id}/doctor-invitations/` | Clinic Owner / Super Admin | List pending/filtered doctor invitations for clinic |
| `PATCH`| `/clinics/{clinic_id}/doctors/{association_id}/settings/` | Clinic Owner / Super Admin | Update clinic-specific consultation fee, follow-up fee, slot duration |
| `POST` | `/clinics/{clinic_id}/doctors/{association_id}/remove/` | Clinic Owner / Super Admin | End active association (`ACTIVE` -> `REMOVED`) without deleting doctor profile |

#### Doctor Endpoints
| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/doctors/me/clinics/` | Doctor | List doctor's clinic associations across platform (filter `?status=`) |
| `GET` | `/doctors/me/clinic-invitations/` | Doctor | List pending clinic invitations awaiting doctor decision |
| `POST` | `/doctors/me/clinic-invitations/{association_id}/accept/` | Doctor | Accept clinic invitation (`INVITED` -> `ACTIVE`) |
| `POST` | `/doctors/me/clinic-invitations/{association_id}/reject/` | Doctor | Decline clinic invitation (`INVITED` -> `REJECTED`) |

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

---

### 2.11. Public Doctor and Clinic Discovery (`/api/v1/public/`)

| Method | Endpoint | Access Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/public/doctors/` | Public (AllowAny) | Search verified doctors with active clinic associations. Supports name, specialization, city, area, clinic, date, ordering, pagination. |
| `GET` | `/public/doctors/{doctor_id}/` | Public (AllowAny) | Retrieve doctor's public professional profile and eligible practice locations with clinic-specific fees. |
| `GET` | `/public/clinics/` | Public (AllowAny) | Search approved and active clinics by name, city, area, or service. Includes doctor count and pagination. |
| `GET` | `/public/clinics/{clinic_id}/` | Public (AllowAny) | Retrieve approved clinic details and currently practicing verified doctors with clinic-specific fees (supports UUID or slug). |
| `GET` | `/public/clinics/{clinic_id}/doctors/{doctor_id}/availability/?date=YYYY-MM-DD` | Public (AllowAny) | Real-time candidate appointment slots computed using clinic timezone, active shifts, doctor leaves, and administrative blocked slots. |
| `GET` | `/public/specializations/` | Public (AllowAny) | Catalog of medical specializations for search filter dropdowns. |
| `GET` | `/public/cities/` | Public (AllowAny) | Distinct list of cities where approved clinics are currently operating. |

#### Public Data Visibility Rules & Security Boundaries:
1. **Doctors in Public Search:**
   - Must have `verification_status == VERIFIED` and `is_verified == True`.
   - Linked user account must have `is_active == True` and `status == ACTIVE`.
   - Must have at least one active association (`DoctorClinic.status == ACTIVE`) with an approved, active clinic (`Clinic.status == APPROVED`).
   - Doctors with pending, rejected, suspended, or draft status are strictly excluded.
2. **Clinics in Public Search:**
   - Must have `status == APPROVED` and `is_verified == True`.
   - Suspended, pending, or draft clinics are strictly excluded.
3. **Multi-Clinic Doctor Semantics:**
   - General doctor search returns exactly one doctor record per practitioner (deduplicated across clinics).
   - If a clinic filter is applied, only the matching clinic practice location is attached, preserving the doctor's unique identity.
   - Clinic-specific consultation fees and appointment durations are maintained independently per association without arbitrary fee blending.
4. **Strictly Prohibited Fields (Never Leaked in Public Responses):**
   - Doctor medical council documents / uploaded verification certificates (`DoctorDocument`).
   - Private user account credentials, emails, personal phone numbers, and password hashes.
   - Internal super administrator review notes (`verification_notes`).
   - Private invitation tokens, invitation messages, and commission rates.
   - Other tenants' private schedule configurations or patient data.

