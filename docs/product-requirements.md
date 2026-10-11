# EazyDoc — Product Requirements Document (PRD)

## 1. Executive Summary & Vision

**EazyDoc** is a multi-clinic doctor appointment and practice management SaaS platform. The platform serves as a two-sided healthcare ecosystem:
1. **Public Marketplace & Patient Portal:** Patients discover verified doctors and specialized clinics, view clinic-specific consultation fees, verify real-time available time slots, book appointments, make secure online payments, and access post-consultation digital prescriptions.
2. **Clinic & Practice Management SaaS:** Clinic owners and staff manage their clinic profile, onboard doctors (or invite existing registered doctors), configure weekly clinic-specific consultation schedules, manage in-clinic appointment queues, handle patient check-ins, record consultations, issue digital prescriptions, and track clinic revenue and settlements.
3. **Platform Administration:** Platform Super Admins oversee clinic verification, doctor credential verification, dispute resolutions, commission rates, platform financial settlements, and operational analytics.

---

## 2. Target Personas & User Roles

| Role | Scope | Key Goals & Responsibilities |
| :--- | :--- | :--- |
| **Super Admin** | Platform-wide | Verify/suspend clinics, verify doctor registration licenses, configure default platform commission rates, view aggregate bookings and financial audit logs, manage dispute settlements. |
| **Clinic Owner** | Clinic-scoped | Manage clinic profile, operating hours, locations; invite/associate doctors; configure clinic-specific doctor schedules and fees; manage clinic staff; oversee clinic finances and payouts. |
| **Clinic Staff / Receptionist** | Clinic-scoped | Check in patients at physical desk, manage daily appointment queue, book walk-in/offline appointments, view daily doctor rosters, handle basic patient inquiries. |
| **Doctor** | Global Profile / Multi-Clinic | Maintain global verified identity and medical registration number; accept/reject clinic association requests; review appointment schedules across clinics; conduct consultations; issue digital prescriptions. |
| **Patient** | Public / Personal | Search by specialization, doctor, clinic, and locality; book confirmed appointments; pay online via Razorpay; reschedule or cancel within allowed policy windows; view consultation notes and prescriptions. |

---

## 3. Core Functional Requirements

### 3.1. Doctor Identity, Profile & Medical Registration Verification
- **Global Doctor Profile:** A doctor maintains a single global medical identity linked 1:1 with their primary login account (`User`, role: `DOCTOR`).
- **Medical Registration Uniqueness:**
  - A medical registration number uniquely identifies a doctor within their issuing authority.
  - Scope: Enforced via a composite unique constraint: `(normalized_registration_council, normalized_registration_number)`.
  - Normalization: Automatically strips whitespace and converts to uppercase (e.g. ` MMC / 12345 ` -> `MMC/12345`; ` Maharashtra Medical Council ` -> `MAHARASHTRA MEDICAL COUNCIL`). Case variations and spacing tricks cannot bypass uniqueness.
  - Defense-in-depth: Enforced through application-level validation in `clean()` and serializers, plus physical database constraint `unique_doctor_council_normalized_reg_no`.
- **Doctor Registration & Verification Lifecycle:**
  - `DRAFT`: Doctor account created and profile details saved. Doctor can edit all fields and upload supporting evidence documents.
  - `PENDING`: Doctor submits completed profile for verification. Super Admin review queue displays submitted details.
  - `VERIFIED`: Super Admin verifies authenticity of medical council records. Records verifier admin user and timestamp. Doctor becomes eligible for clinic invitations and appointment scheduling.
  - `REJECTED`: Super Admin rejects submission with a mandatory reason. Doctor is notified, can correct credentials, and resubmit.
  - `SUSPENDED`: Super Admin suspends practitioner with an audited reason. Suspended doctors are ineligible for new clinic associations or appointments.
- **Self-Approval Invariant:** An administrator cannot verify their own doctor profile.
- **Private Verification Documents:**
  - Doctors upload registration certificates and degree proofs privately (max 5MB, PDF/JPG/PNG).
  - Documents are stored in secure private storage and never exposed via public endpoints or directory searches.
  - Only the owning doctor and authorized Super Admins have permission to access private verification files.
- **Privacy-Preserving Registration Lookup:**
  - Authorized Clinic Owners can query `GET /api/v1/doctors/registration-lookup/?registration_number=...` to verify if a doctor exists and is verified before sending clinic invitations.
  - Omits private contact details, email, phone, documents, verification notes, and patient data.
  - Disambiguation: If a registration number matches across multiple state councils, the API explicitly prompts for `registration_council`.

- **Doctor ↔ Clinic Many-to-Many Association (`DoctorClinic`):**
  - A doctor can practice at Clinic A (e.g., morning) and Clinic B (e.g., evening).
  - Each association requires mutual consent: Clinic Owner sends an invitation/request, and Doctor accepts via their dashboard (or vice-versa).
  - Association status can be `INVITED`, `ACTIVE`, `PAUSED`, or `TERMINATED`.
- **Clinic-Specific Fees:** Each `DoctorClinic` link independently defines:
  - `consultation_fee` (in INR, e.g., ₹500 at Clinic A, ₹700 at Clinic B).
  - `online_consultation_fee` (if telemedicine is enabled).
  - `follow_up_fee` and `follow_up_validity_days`.
  - `appointment_duration_minutes` (e.g., 15 mins, 20 mins, 30 mins).

### 3.2. Clinic-Specific Schedules & Overlap Prevention
- **Schedule Ownership:** Weekly recurring schedules belong to the `DoctorClinic` association, never directly to the Doctor alone.
- **Slot Time Representation:** Day of week (0=Monday ... 6=Sunday), shift start time (e.g., `10:00:00`), shift end time (e.g., `13:00:00`), slot duration in minutes, and maximum patients per slot.
- **Physical Feasibility & Conflict Prevention:**
  - A doctor cannot be scheduled in two different clinics simultaneously.
  - When a Clinic Owner creates or updates a schedule shift for Doctor D on Day X from `T_start` to `T_end`, the system queries all active schedules for Doctor D across *all* clinics.
  - If `[T_start, T_end)` overlaps with an existing shift at any clinic, the API rejects the creation with a descriptive conflict error (`409 Conflict`), indicating the conflicting clinic name and hours.
  - Travel buffer time (e.g., minimum 30 minutes between clinics) can be enforced as an optional policy.

### 3.3. Appointment Booking & Anti-Double-Booking Engine
- **Slot Generation:** Dynamic slot generation combining recurring schedule, active blocked dates, doctor unavailability leaves, and already booked/held appointments.
- **Atomic Concurrency Control:**
  - When two patients simultaneously attempt to reserve the same slot, pessimistic locking (`select_for_update`) or temporary atomic slot reservation tokens with Redis TTL are employed.
  - A database unique constraint `(doctor_clinic_id, appointment_date, appointment_time)` on active appointments guarantees that double-booking is physically impossible at the storage level.
- **Slot Reservation Lifetime:** During checkout, a slot is held for 10 minutes (`HOLD` status in Redis/Database). If payment is not verified within 10 minutes, the hold expires and the slot becomes open to other patients.

### 3.4. Appointment Lifecycle & State Machine
Appointments progress through strict, audited states:
1. `PENDING`: Slot reserved, awaiting payment verification.
2. `CONFIRMED`: Payment verified server-side via Razorpay signature or webhook.
3. `CHECKED_IN`: Patient arrived at clinic; Receptionist marked physical presence.
4. `IN_CONSULTATION`: Patient called into consultation room with doctor.
5. `COMPLETED`: Doctor concluded consultation; optional digital prescription generated.
6. `CANCELLED_BY_PATIENT`: Patient cancelled within the valid cancellation window.
7. `CANCELLED_BY_DOCTOR`: Doctor cancelled due to emergency/illness.
8. `CANCELLED_BY_CLINIC`: Clinic closed/administrative cancellation.
9. `RESCHEDULED`: Appointment rescheduled to a new date/time slot (creates new appointment reference and updates old to `RESCHEDULED`).
10. `NO_SHOW`: Appointment window passed without check-in or cancellation.

### 3.5. Cancellation & Rescheduling Rules
- **Patient Cancellation Window:**
  - A patient may cancel an appointment **only until 11:59:59 PM on the day preceding the appointment date**, evaluated in the clinic's local timezone (default: `Asia/Kolkata`).
  - *Example:* For an appointment on Friday at 5:00 PM, the deadline is Thursday at 11:59:59 PM. Starting Friday at 12:00:00 AM, the patient cancellation button is disabled, and backend requests return `400 Bad Request`.
- **Patient Rescheduling Window:**
  - Follows the identical deadline (previous day 11:59:59 PM). A patient may reschedule up to 2 times per booking.
- **Doctor/Clinic Cancellation Override:**
  - If a doctor or clinic cancels at any time (even on the appointment day), the patient deadline is bypassed.
  - The system marks affected appointments as `CANCELLED_BY_DOCTOR` / `CANCELLED_BY_CLINIC`, triggers a 100% refund or provides a free priority reschedule credit, and dispatches instant SMS/Email/WhatsApp alerts.

### 3.6. Doctor Unavailability & Out-of-Office Management
- **Unavailability Range:** Clinic owners, authorized staff, or doctors can mark unavailability across a date range or specific hour interval (e.g., Sick Leave, Conference, Emergency, Clinic Holiday).
- **Automated Blast-Radius Resolution:**
  - The system identifies all active appointments (`CONFIRMED`, `PENDING`) falling into the unavailable window.
  - Transition appointments to `CANCELLED_BY_DOCTOR` or `PENDING_RESCHEDULE`.
  - Automated asynchronous Celery task executes refund processing via Razorpay Refund API and sends push/email/SMS notifications with rescheduling links.

### 3.7. Platform Commission & Financial Split
- **Gross Transparent Pricing:** Patients are presented only with the total consultation fee (e.g., `₹500`).
- **Internal Commission Engine:**
  - The platform commission is an internal operational calculation and **must NEVER appear as a surcharge or line-item to the patient**.
  - Default rate: Configured globally in `PlatformSetting` (e.g., `5.00%`), with optional per-clinic custom negotiated rates in `Clinic.custom_commission_rate`.
  - Financial Ledger breakdown per booking:
    - `gross_amount`: ₹500.00
    - `platform_commission_rate`: 5.00%
    - `platform_commission_amount`: ₹25.00
    - `clinic_settlement_amount`: ₹475.00
    - `payment_gateway_fee`: e.g., 2% + GST (tracked for reconciliation)
    - `settlement_status`: `PENDING`, `READY_FOR_PAYOUT`, `SETTLED`, `REFUNDED`

### 3.8. Multi-Tenant Data Isolation
- Strict separation of clinic operational data. Staff of Clinic A cannot list, view, modify, or export patients, appointments, revenue, or medical notes of Clinic B.
- Backend enforcement via Django REST Framework base querysets filtering on `clinic_id` derived from verified JWT user claims and clinic memberships.

### 3.9. Consultations & Digital Prescriptions
- **Clinical Records:** Doctors record Chief Complaints, Clinical Observations, Diagnoses (ICD-10 optional), and Vital Signs (BP, Pulse, Temperature, SpO2, Weight).
- **Prescriptions:** Medicines with dosage, frequency (e.g., 1-0-1), duration (e.g., 5 days), route (Oral, Topical), and special instructions (After food), alongside recommended lab investigations and follow-up date.
### 3.10. Clinic Registration, Verification & Lifecycle (Day 4)
- **Establishment Onboarding:**
  - Authenticated `CLINIC_OWNER` users can register medical centers and clinics.
  - Required profile: Legal/commercial name, unique public slug, official email, phone, physical address (line 1, line 2, city, state, postal/PIN code, country), optional clinic logo.
  - Creation status: Starts as `PENDING` (or `DRAFT` if saved as draft).
  - An owner can own and manage multiple clinics independently.
- **Verification State Machine:**
  - `DRAFT`: Saved clinic profile. Not visible for booking or admin review until submitted.
  - `PENDING`: Awaiting Super Admin compliance and credential check.
  - `APPROVED`: Verified by Super Admin. Publicly bookable in patient discovery.
  - `REJECTED`: Rejected by Super Admin with mandatory feedback notes. Clinic owner can correct information and resubmit.
  - `SUSPENDED`: Administratively suspended with mandatory reason. Blocked from taking new patient bookings. Super Admin can reactivate.
- **Critical Policy Rules & Invariants:**
  - A clinic owner can never approve, reject, suspend, or reactivate their own clinic (or any clinic).
  - Only platform `SUPER_ADMIN` users can execute verification decisions.
  - Rejected clinics require explicit correction before transitioning back to `PENDING` via the submission endpoint.
  - Non-clinic owners (Patients, Doctors, Staff) are strictly forbidden from creating or administering clinics.
  - Strict tenant isolation: Clinic owners can only view and mutate clinics they own.

---

## 4. Non-Functional Requirements

### 4.1. Security & Compliance
- **Data Protection:** Compliance with healthcare data guidelines (Digital Personal Data Protection Act - DPDPA 2023 India, HIPAA security rule principles).
- **Authentication:** Dual-token JWT (short-lived access tokens 15m, rotating refresh tokens 7d stored in Secure, HttpOnly, SameSite cookies).
- **Sensitive Fields:** Passwords hashed with Argon2/PBKDF2; medical notes and PII encrypted or access-restricted; zero plaintext payment credentials.
- **Audit Trails:** Immutable append-only audit logging for patient medical access, appointment status changes, and financial refunds.

### 4.2. Performance & Scalability
- **Response Latency:** 95th percentile API response time < 150ms for search and slot availability queries.
- **High Concurrency:** Redis caching for static metadata (specializations, doctor bios) and dynamic availability masks with cache invalidation on booking/cancellation.
- **Background Tasks:** Non-blocking email, SMS, PDF generation, and webhook handling delegated to Celery workers backed by Redis.

### 4.3. Reliability & Availability
- 99.9% uptime target.
- Database replication, daily automated backups, point-in-time recovery (PITR) in PostgreSQL.
- Idempotency keys on all payment creation and refund endpoints to prevent duplicate charges.
