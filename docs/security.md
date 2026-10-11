# EazyDoc — Security Architecture & Threat Model

## 1. Security Overview & Philosophy

Healthcare SaaS platforms operate under rigorous compliance requirements (including India's **Digital Personal Data Protection Act 2023 - DPDPA** and international HIPAA security guidelines). EazyDoc enforces **defense-in-depth**: every architectural layer—network, container, application, ORM, database, and background queue—applies distinct security boundaries.

---

## 2. Authentication & Session Management

### 2.1. Dual-Token JWT Strategy
- **Access Tokens:** Short-lived (15 minutes), containing user UUID, role, and authorized clinic scopes. Transmitted via standard `Authorization: Bearer <token>` header.
- **Refresh Tokens:** Long-lived (7 days), stored exclusively in **`HttpOnly`**, **`Secure`**, **`SameSite=Strict`** cookies to prevent client-side JavaScript theft via Cross-Site Scripting (XSS).
- **Token Rotation & Revocation:** Every token refresh issues a new refresh token and blacklists the previous token in Redis (`djangorestframework-simplejwt` token blacklist).
- **Session Revocation:** Changing password or triggering "Logout from all devices" immediately invalidates all active refresh tokens for the user in Redis.

### 2.2. Password Storage
- Passwords are encrypted using **Argon2id** (winner of the Password Hashing Competition) with salts generated via cryptographically secure random number generators (`os.urandom`).
- Minimum password policy: 8+ characters, requiring uppercase, lowercase, numbers, and special characters.

---

## 3. Authorization, RBAC & Multi-Tenant Isolation

### 3.1. Role-Based Access Control (RBAC) Hierarchy

| Role | Scope | Permitted Actions | Prohibited Actions |
| :--- | :--- | :--- | :--- |
| **Super Admin** | Global | Verify/suspend clinics, view platform revenue, configure commission %, audit disputes. | View private doctor-patient clinical consultation notes without judicial/audit authorization. |
| **Clinic Owner** | Clinic | Manage clinic profile, invite doctors, configure schedules & fees, manage staff, view clinic revenue. | Access other clinics' appointments, patients, revenue, or schedules. |
| **Clinic Staff** | Clinic | Check in patients, manage live queue, book offline walk-ins, view daily doctor roster. | Alter consultation fees, modify doctor medical credentials, access financial settlement accounts. |
| **Doctor** | Multi-Clinic / Self | Accept clinic invites, view appointments across their clinics, conduct consultations, issue prescriptions. | Alter another doctor's clinical records, access clinic financials beyond own consultation logs. |
| **Patient** | Self | Search doctors/clinics, book slots, pay online, reschedule/cancel own appointments, view own prescriptions. | Access another patient's medical records, view clinic backend revenue or internal platform commission. |

### 3.2. Prevention of Broken Object-Level Authorization (BOLA / IDOR)
- **Tenant Context Scoping:** All database queries for clinic-scoped entities are mediated by `TenantQuerySetMixin`:
  ```python
  class TenantQuerySetMixin:
      def get_queryset(self):
          user = self.request.user
          if user.role == UserRole.CLINIC_OWNER:
              return super().get_queryset().filter(clinic__owner=user)
          elif user.role == UserRole.STAFF:
              return super().get_queryset().filter(clinic=self.request.user.staff_profile.clinic)
          elif user.role == UserRole.DOCTOR:
              return super().get_queryset().filter(doctor_clinic__doctor__user=user)
          elif user.role == UserRole.PATIENT:
              return super().get_queryset().filter(patient__user=user)
          elif user.role == UserRole.SUPER_ADMIN:
              return super().get_queryset()
          return super().get_queryset().none()
  ```
- **UUID Keys:** All IDs are random UUIDv4, eliminating sequential enumeration attacks (e.g. `/api/v1/appointments/101` vs `/102`).

### 3.3. Clinic Multi-Tenant Security & Verification Governance (Day 4)
- **Role Gating:** Only authenticated users with `CLINIC_OWNER` or `SUPER_ADMIN` role can create clinics. Patients, Doctors, and Staff receive `403 Forbidden`.
- **Tenant Isolation:** Clinic owners can list and retrieve only clinics they own (`owner = request.user`). Direct object lookups for another tenant's clinic ID yield `403 Forbidden` / `404 Not Found`.
- **Protected Profile Fields:** Clinic owners cannot escalate privileges or alter governance metadata. Updates to `status`, `owner`, `approved_at`, `approved_by`, and `verification_notes` are discarded and protected at the serializer and view layers.
- **Self-Approval Prevention:** In accordance with healthcare compliance guidelines, a clinic owner cannot approve their own clinic, even if they hold Super Admin status.
- **Secure Logo Upload:**
  - Files capped at 2MB.
  - Whitelisted MIME types (`image/jpeg`, `image/png`, `image/webp`) and extensions.
  - Pillow deep inspection verifies genuine image binary headers, rejecting disguised binaries or PHP/executable files.

### 3.4. Doctor Identity Governance & Credential Privacy (Day 5)
- **Role Gating:** Only authenticated users with `DOCTOR` role can create practitioner profiles and access `/api/v1/doctors/me/`. Non-doctor accounts receive `403 Forbidden`.
- **Medical Registration Uniqueness & Normalization:**
  - Physical database composite `UniqueConstraint(fields=["normalized_registration_council", "normalized_registration_number"])` prevents concurrent collisions.
  - Whitespace is stripped and text uppercased at both the serializer and model layer, preventing bypass attempts using varied letter casing or whitespace padding.
  - Scoped to issuing authority council: doctors with identical numbers issued by different legitimate state councils can coexist without collision.
- **Verification Status Protection:**
  - Doctors cannot alter their `verification_status`, `verified_by`, `verified_at`, `submitted_at`, or `verification_notes`.
  - Permitted profile fields are strictly filtered via `DoctorProfileUpdateSerializer`.
  - Only Super Admins can verify, reject, suspend, or reactivate doctors.
  - Self-Approval Invariant: An administrator holding a doctor profile is prohibited from self-approving their own credentials.
- **Privacy-Preserving Registration Lookup:**
  - Clinic Owners can verify existence and eligibility via `GET /api/v1/doctors/registration-lookup/?registration_number=...`.
  - Privacy Guarantees: Strictly returns only `found`, `full_name`, `specialization`, `registration_council`, `is_verified`, and `is_eligible_for_invitation`. Never leaks email, phone, documents, audit notes, or patient data.
  - Access is restricted to `CLINIC_OWNER` and `SUPER_ADMIN`. Patients and anonymous users are blocked (`403` / `401`).
- **Private Document Evidence Storage:**
  - Verification documents (certificates, degrees, ID proofs) are stored in secure private storage (`doctor_documents/private/`).
  - Public URLs are never generated or exposed. Files are streamed only through authenticated, authorized endpoints with object-level permission enforcement (`IsDoctorDocumentOwnerOrAdmin`).
  - File upload integrity: 5MB size limit, extension whitelisting, MIME type validation, and Pillow binary verification on image uploads.
- **Security Audit Trails:**
  - Immutable audit logs record all critical practitioner actions (`DOCTOR_PROFILE_CREATED`, `DOCTOR_PROFILE_UPDATED`, `DOCTOR_SUBMITTED_VERIFICATION`, `DOCTOR_VERIFIED`, `DOCTOR_REJECTED`, `DOCTOR_SUSPENDED`, `DOCTOR_REACTIVATED`, `DOCTOR_DOCUMENT_UPLOADED`).
  - Passwords, JWT tokens, and private clinical documents are sanitized and never written to application logs.

---

## 4. Payment Security & Fraud Prevention (Razorpay)

### 4.1. Server-Side Cryptographic Signature Verification
The frontend payment response is treated as completely untrusted. The backend verifies the HMAC-SHA256 signature before transitioning an appointment to `CONFIRMED`:
```python
import hmac
import hashlib

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    message = f"{order_id}|{payment_id}".encode("utf-8")
    generated_signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, signature)
```

### 4.2. Webhook Authentication & Idempotency
- Incoming Razorpay webhooks (`/api/v1/payments/webhook/`) verify the `X-Razorpay-Signature` against `RAZORPAY_WEBHOOK_SECRET`.
- Every webhook event is checked for idempotency using `event_id` stored in Redis with a 24-hour TTL to prevent double-processing refunds or duplicate credit ledger entries.

### 4.3. PCI-DSS Compliance
- Zero payment card numbers, CVVs, or bank credentials ever touch EazyDoc servers. Payment details are entered directly inside the PCI-DSS Level 1 certified Razorpay iframe.

---

## 5. File & Clinical Document Security

### 5.1. Secure Storage Architecture
- Patient prescriptions, lab reports, and doctor KYC documents are stored in **private AWS S3 buckets** with public access blocked (`BlockPublicAcls`, `BlockPublicPolicy`).
- No public direct URLs exist for medical documents.

### 5.2. Pre-Signed Temporary URLs
- Files are accessed exclusively via temporary pre-signed S3 URLs generated on-demand with a **15-minute expiration window**.
- Before generating a pre-signed URL, the API verifies that `request.user` is either:
  1. The patient owning the record.
  2. The attending doctor linked to that patient's appointment.
  3. Authorized clinic staff for an active consultation.

### 5.3. Upload Validation
- File uploads are validated server-side for:
  - Allowed MIME types: `application/pdf`, `image/jpeg`, `image/png`.
  - Magic byte verification using `python-magic` (rejecting files with spoofed extensions).
  - Maximum file size: 10MB per document.

---

## 6. API Security, Rate Limiting & Input Validation

### 6.1. Rate Limiting via Redis
- **Auth endpoints (`/api/v1/auth/login/`, `/api/v1/auth/verify-otp/`):** 5 requests per minute per IP to prevent brute-force attacks.
- **Booking checkout endpoints:** 20 requests per minute per user to prevent bot slot hoarding.
- **Public search endpoints:** 60 requests per minute per IP.

### 6.2. Cross-Site Scripting (XSS) & Content Security Policy (CSP)
- React automatically escapes variables in JSX.
- HTTP security headers configured via `django-csp` and Nginx:
  - `Content-Security-Policy: default-src 'self'; ...`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`

### 6.3. CORS & CSRF
- **CORS:** Strict whitelist of frontend origins (e.g., `https://app.eazydoc.com`). Wildcards (`*`) are prohibited in production.
- **CSRF:** Django CSRF token enforcement for state-modifying requests using cookie authentication.

---

## 7. Audit Logging & Compliance

### 7.1. Immutable Audit Trail
- Critical security and financial events are written to an append-only `AuditLog` table:
  - User authentication failures and logins.
  - Appointment cancellations and rescheduling.
  - Razorpay payment verifications and refunds.
  - Changes to doctor schedules, fees, or clinic commission overrides.
  - Access to patient medical records and prescriptions.
- Records store the actor, clinic tenant, IP address, user-agent, action timestamp, and JSON snapshot of state changes.
