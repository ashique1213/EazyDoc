# Super Admin Dashboard & Multi-Tenant SaaS Management Architecture

## 1. Overview
The Super Admin Dashboard provides centralized platform governance, multi-tenant monitoring, commercial commission configuration, user account controls, and an immutable security audit trail for the EazyDoc SaaS platform.

It is strictly isolated from clinic-facing and patient-facing modules. Clinic Owners and Doctors can never access Super Admin endpoints or cross-tenant data.

---

## 2. Role & Permission Matrix

| Role | Admin Dashboard & Metrics | Clinic Verification / Suspend | Doctor Verification / Suspend | User Status Management | Global Commission Settings | Audit Logs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **SUPER_ADMIN** | **Full Access** | **Full Access** | **Full Access** | **Full Access** | **Full Access** | **Full Access** |
| **CLINIC_OWNER**| ❌ Forbidden (403) | ❌ (Own clinic DRAFT->PENDING only) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Read/Update Forbidden | ❌ Forbidden (403) |
| **STAFF** | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) |
| **DOCTOR** | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) |
| **PATIENT** | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) | ❌ Forbidden (403) |

---

## 3. Administrative REST API Endpoints (`/api/v1/admin/`)

### Dashboard & Analytics
- `GET /api/v1/admin/dashboard/summary/`: Aggregated platform counts (clinics, doctors, patients, appointments, financials).
- `GET /api/v1/admin/dashboard/appointments-trend/`: Daily volume breakdown (confirmed, completed, cancelled) over the last N days.
- `GET /api/v1/admin/dashboard/financial-summary/`: Revenue aggregations and daily gross/commission flow.

### Clinics Management
- `GET /api/v1/admin/clinics/`: Paginated clinic list with `status`, `search`, `date_from`, `date_to` filters.
- `GET /api/v1/admin/clinics/{clinic_id}/`: Full clinic establishment profile.
- `POST /api/v1/admin/clinics/{clinic_id}/approve/`: Transitions `PENDING` -> `APPROVED`.
- `POST /api/v1/admin/clinics/{clinic_id}/reject/`: Transitions `PENDING` -> `REJECTED` (with mandatory reason).
- `POST /api/v1/admin/clinics/{clinic_id}/suspend/`: Transitions `APPROVED` -> `SUSPENDED` (prevents new bookings).
- `POST /api/v1/admin/clinics/{clinic_id}/reactivate/`: Transitions `SUSPENDED` -> `APPROVED`.

### Doctors Management
- `GET /api/v1/admin/doctors/`: Paginated doctor credentials list with `status`, `search`, `date_from`, `date_to` filters.
- `GET /api/v1/admin/doctors/{doctor_id}/`: Full practitioner qualifications and council registration details.
- `POST /api/v1/admin/doctors/{doctor_id}/verify/`: Verifies medical council credentials.
- `POST /api/v1/admin/doctors/{doctor_id}/reject/`: Rejects verification with feedback reason.
- `POST /api/v1/admin/doctors/{doctor_id}/suspend/`: Suspends practitioner; halts public booking without data loss.
- `POST /api/v1/admin/doctors/{doctor_id}/reactivate/`: Reactivates verified status.

### User Account Management
- `GET /api/v1/admin/users/`: Paginated users with `role`, `status`, `is_active`, and keyword search. Passwords and tokens are strictly excluded.
- `GET /api/v1/admin/users/{user_id}/`: Sanitized user account details.
- `POST /api/v1/admin/users/{user_id}/activate/`: Restores active status.
- `POST /api/v1/admin/users/{user_id}/deactivate/`: Deactivates account (self-lockout protected).
- `POST /api/v1/admin/users/{user_id}/suspend/`: Suspends account with reason (self-lockout protected).

### Appointments Management
- `GET /api/v1/admin/appointments/`: Platform-wide appointments with clinic, doctor, status, and date filters.
- `GET /api/v1/admin/appointments/{appointment_id}/`: Full appointment and fee breakdown.
- `GET /api/v1/admin/appointments/{appointment_id}/history/`: Complete chronological state change history.
- `POST /api/v1/admin/appointments/{appointment_id}/cancel/`: Administrative cancellation with mandatory reason.

### Finance & Commission Configuration
- `GET /api/v1/admin/payments/`: Gateway transactions with payment IDs, patient, clinic, failure code/reason.
- `GET /api/v1/admin/commissions/`: Commission ledger records with historical snapshot rates.
- `GET /api/v1/admin/settings/commission/`: View platform default rate (e.g. 5.00%), clinic overrides, and audit history.
- `PATCH /api/v1/admin/settings/commission/`: Update platform default rate or set/clear clinic-specific overrides.

### Audit Logs
- `GET /api/v1/admin/audit-logs/`: Immutable security audit trail with action, actor, resource, and JSON details.

---

## 4. Commission Configuration & Financial Rules

### Precedence Hierarchy
1. Explicit custom rate snapshot (if specified during administrative settlement override).
2. Clinic-specific override (`clinic.commission_rate`), if configured.
3. Platform default commission rate (`PlatformSetting.get_default_commission_rate()`, default 5.00%).

### Invariants & Accounting Rules
1. **Historical Immutability**: Modifying the global default commission rate or a clinic override applies solely to **future eligible transactions**. Existing `CommissionRecord` snapshots remain intact.
2. **Gross Invariant**:
   $$\text{Gross Amount} = \text{Commission Amount} + \text{Clinic Share}$$
3. **Financial Terminology Definitions**:
   - **Gross Successful Payments**: Total INR collected from patients via Razorpay checkout for successful appointments.
   - **Recorded Platform Commission**: Retained SaaS platform fee snapshot recorded at payment capture time.
   - **Calculated Clinic Share**: Internal accounting ledger allocation earmarked for the clinic.
   - **Actual Refunds**: Money returned through the gateway (0.00 unless explicitly refunded).
   - **Actual Payouts / Settlements**: External bank transfers disbursed to clinic bank accounts. EazyDoc explicitly displays `0.00` because automated bank payout settlement is not active. Calculated clinic share is never mislabeled as disbursed funds.

---

## 5. Security & Self-Lockout Guards
- **Backend Authorization**: All administrative endpoints enforce `IsSuperAdmin` backend permission. Frontend navigation hiding is never relied upon as a security boundary.
- **Self-Lockout Protection**: A Super Admin cannot deactivate or suspend their own account via administrative user management endpoints.
- **Credential Hygiene**: Password hashes, JWT tokens, reset tokens, and gateway secret keys are never included in API responses or audit log details.
