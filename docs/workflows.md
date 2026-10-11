# EazyDoc — End-to-End System Workflows

## 1. Patient Registration & Authentication Workflow

```
[Patient]                                  [Backend API]                         [Database]
   │                                             │                                    │
   │─── 1. POST /api/v1/auth/register/ ─────────►│                                    │
   │    (email, phone, password, name)           │                                    │
   │                                             │─── 2. Validate email & phone ─────►│
   │                                             │       (Unique constraint check)    │
   │                                             │◄─── Phone & Email Available ───────┤
   │                                             │                                    │
   │                                             │─── 3. Hash password (Argon2)       │
   │                                             │─── 4. Create User (Role=PATIENT) ─►│
   │                                             │─── 5. Create Patient Profile ─────►│
   │                                             │                                    │
   │                                             │─── 6. Generate OTP (Redis 5m TTL)  │
   │                                             │─── 7. Async SMS / Email Dispatch   │
   │◄── 8. Return 201 Created (Requires OTP) ────┤                                    │
   │                                             │                                    │
   │─── 9. POST /api/v1/auth/verify-otp/ ───────►│                                    │
   │◄── 10. Return JWT (Access + Refresh Cookie)─┤                                    │
```

---

## 2. Clinic Registration & Verification Lifecycle (Day 4)

### 2.1. End-to-End Workflow Diagram

```
[Clinic Owner]                           [Backend API]                         [Super Admin]
   │                                           │                                     │
   │─── 1. POST /api/v1/clinics/ ─────────────►│                                     │
   │    (Name, Email, Phone, Address,          │                                     │
   │     City, State, Pincode, Country, Logo)  │─── 2. Validate fields & slug        │
   │                                           │─── 3. Persist (Status: PENDING)     │
   │◄── 4. 201 Created (Pending Verification) ─┤                                     │
   │                                           │                                     │
   │                                           │◄── 5. GET /api/v1/admin/clinics/ ───│
   │                                           │       (Filter & inspect submission) │
   │                                           │                                     │
   │                                           │◄── 6. POST .../clinics/{id}/approve/│
   │                                           │       (Owner cannot self-approve)   │
   │                                           │─── 7. Status -> APPROVED            │
   │                                           │       approved_at, approved_by set  │
   │                                           │─── 8. Immutable audit logged        │
   │◄── 9. Status = APPROVED (Bookable) ───────┤                                     │
   │                                           │                                     │
   │   [Alternative: Rejection Flow]           │                                     │
   │                                           │◄── 10. POST .../reject/ (reason) ───│
   │                                           │─── 11. Status -> REJECTED           │
   │◄── 12. View Rejection Reason ─────────────┤        verification_notes updated   │
   │─── 13. PATCH /clinics/{id}/ (corrections)►│                                     │
   │─── 14. POST /clinics/{id}/submit/ ───────►│─── 15. Status -> PENDING            │
   │◄── 16. Resubmitted for Admin Review ──────┤                                     │
```

### 2.2. State Transition Matrix

| Current Status | Action | Actor | New Status | Pre-Conditions / Requirements |
| :--- | :--- | :--- | :--- | :--- |
| `None` | Create (Default) | `CLINIC_OWNER` | `PENDING` | Valid form, unique slug generated |
| `None` | Create (Draft) | `CLINIC_OWNER` | `DRAFT` | Valid form, status requested as DRAFT |
| `DRAFT` | Submit | `CLINIC_OWNER` | `PENDING` | Owner authorization |
| `PENDING` | Approve | `SUPER_ADMIN` | `APPROVED` | Approver != Clinic Owner, sets `approved_at` & `approved_by` |
| `PENDING` | Reject | `SUPER_ADMIN` | `REJECTED` | Non-empty reason required in `verification_notes` |
| `REJECTED` | Resubmit | `CLINIC_OWNER` | `PENDING` | Owner corrects profile, calls `submit/` |
| `APPROVED` | Suspend | `SUPER_ADMIN` | `SUSPENDED` | Non-empty reason required, blocks bookings |
| `SUSPENDED`| Reactivate | `SUPER_ADMIN` | `APPROVED` | Super Admin review confirms compliance |

---

## 3. Doctor Registration & Medical Registration Verification

```
[Doctor]                                      [Backend API]                         [Super Admin]
   │                                                │                                     │
   │─── 1. Register User Account (Role=DOCTOR) ────►│                                     │
   │                                                │                                     │
   │─── 2. POST /api/v1/doctors/profile/ ──────────►│                                     │
   │    (Reg No, Council, Specs, Qualifications)   │─── Validate & Normalize Reg No      │
   │                                                │    (Enforce Council Uniqueness)     │
   │◄── 3. 201 Created (Status: DRAFT) ─────────────┤                                     │
   │                                                │                                     │
   │─── 4. POST /api/v1/doctors/me/documents/ ─────►│                                     │
   │    (Upload Certificate / ID Evidence)          │─── Store Private Evidence           │
   │                                                │                                     │
   │─── 5. POST /api/v1/doctors/me/submit-          │                                     │
   │       verification/ ──────────────────────────►│                                     │
   │                                                │─── Set Status: PENDING              │
   │◄── 6. 200 OK (Awaiting Admin Review) ──────────┤                                     │
   │                                                │                                     │
   │                                                │◄── 7. GET /api/v1/admin/doctors/ ───│
   │                                                │    (Admin reviews submitted queue)  │
   │                                                │                                     │
   │                                                │◄── 8. Verify / Reject / Suspend ────│
   │                                                │    - Verify: Set VERIFIED           │
   │                                                │    - Reject: Set REJECTED + reason  │
   │                                                │    - Suspend: Set SUSPENDED + reason│
   │◄── 9. Doctor views verified status / notes ────┤                                     │
   │    (If REJECTED: correct & resubmit)           │                                     │
```

### Verification Status Transitions
- `DRAFT -> PENDING`: Doctor submits completed profile and evidence.
- `PENDING -> VERIFIED`: Super Admin approves valid registration (records `verified_by` and `verified_at`).
- `PENDING -> REJECTED`: Super Admin rejects with mandatory reason notes.
- `REJECTED -> PENDING`: Doctor corrects credentials and resubmits.
- `VERIFIED -> SUSPENDED`: Super Admin suspends practitioner with audited justification.
- `SUSPENDED -> VERIFIED`: Super Admin reinstates doctor standing.
- **Invariants:**
  - Doctors cannot verify themselves.
  - Verifying administrator cannot approve their own doctor account.
  - Suspended doctors cannot become verified via normal profile editing or resubmission.
  - Public users and patients cannot view private doctor verification records or documents.

---

## 4. Doctor Joining Clinic (Multi-Clinic Association Workflow)

```
[Clinic Owner]             [Backend API]                    [Doctor]              [Database]
      │                          │                             │                       │
      │── 1. Search Doctor ─────►│                             │                       │
      │   by Reg No "MED123456"  │── 2. Query Doctor ─────────────────────────────────►│
      │◄─ 3. Return Dr Profile ──┤                             │                       │
      │                          │                             │                       │
      │── 4. Invite Doctor ─────►│                             │                       │
      │   (fee=₹500, dur=15m)    │── 5. Create DoctorClinic ──────────────────────────►│
      │                          │      (status='INVITED')     │                       │
      │                          │── 6. Send Invitation Alert ►│                       │
      │                          │                             │                       │
      │                          │◄─ 7. Accept Invite ─────────│                       │
      │                          │   (PATCH .../accept/)       │                       │
      │                          │── 8. Update DoctorClinic ──────────────────────────►│
      │                          │      (status='ACTIVE')      │                       │
      │◄─ 9. Doctor Linked ──────┤                             │                       │
```

---

## 5. End-to-End Appointment Booking & Payment Workflow

```
[Patient]               [Backend API]             [Redis / DB]           [Razorpay Gateway]
   │                          │                         │                         │
   │── 1. Select Slot ───────►│                         │                         │
   │   (Clinic, Doc, 10:00AM) │── 2. Acquire Slot Hold ─►│                         │
   │                          │      (SET NX EX 600s)   │                         │
   │                          │◄─ 3. Hold Granted ──────┤                         │
   │                          │                         │                         │
   │                          │── 4. Create Appointment ─►│                         │
   │                          │      (status='PENDING') │                         │
   │                          │                         │                         │
   │                          │── 5. Create Order ───────────────────────────────►│
   │                          │      (amount=₹500.00)   │                         │
   │                          │◄─ 6. Return order_id ─────────────────────────────┤
   │                          │                         │                         │
   │◄─ 7. Open Razorpay Modal ┤                         │                         │
   │   (order_id, ₹500.00)    │                         │                         │
   │                          │                         │                         │
   │── 8. Payment Completed ─────────────────────────────────────────────────────►│
   │◄─ 9. payment_id + sig ───────────────────────────────────────────────────────┤
   │                          │                         │                         │
   │── 10. POST .../verify/ ─►│                         │                         │
   │   (order_id, payment_id, │── 11. Verify HMAC-SHA256│                         │
   │    signature)            │       Signature Match?  │                         │
   │                          │                         │                         │
   │                          │── 12. BEGIN TX ────────►│                         │
   │                          │   - Lock Appointment    │                         │
   │                          │   - status='CONFIRMED'  │                         │
   │                          │   - Calculate Comm:     │                         │
   │                          │     Comm (5%) = ₹25     │                         │
   │                          │     Clinic Net = ₹475   │                         │
   │                          │   - Save Payment Record │                         │
   │                          │── 13. COMMIT TX ───────►│                         │
   │                          │                         │                         │
   │                          │── 14. Del Redis Hold ──►│                         │
   │                          │── 15. Async SMS / Email │                         │
   │◄─ 16. Booking Confirmed ─┤                         │                         │
```

---

## 6. Cancellation Workflow (Strict 11:59 PM Rule)

```
[Patient]                                  [Backend API]                         [Razorpay]
   │                                             │                                    │
   │─── 1. POST /api/v1/appointments/{id}/cancel►│                                    │
   │                                             │─── 2. Fetch Clinic Timezone        │
   │                                             │       (e.g., 'Asia/Kolkata')       │
   │                                             │─── 3. Compute Deadline:            │
   │                                             │       Appointment Date - 1 day     │
   │                                             │       at 23:59:59 local time       │
   │                                             │                                    │
   │                                             │─── 4. Is current_time > deadline?  │
   │                                             │       ├── YES: Return 400 ERROR    │
   │                                             │       │   "Cancellation window     │
   │                                             │       │    closed at 11:59 PM"     │
   │                                             │       │                            │
   │                                             │       └── NO: Allowed              │
   │                                             │           ├── Transition status    │
   │                                             │           │   to 'CANCELLED_PATIENT│
   │                                             │           ├── Call Razorpay Refund►│
   │                                             │           │   (Full gross_amount)  │
   │                                             │           ├── Update Payment Record│
   │                                             │           │   (status='REFUNDED')  │
   │                                             │           └── Trigger SMS / Email  │
   │◄── 5. 200 OK (Appointment Cancelled & Refunded)───┤                              │
```

---

## 7. Rescheduling Workflow

```
[Patient]                                  [Backend API]                         [Database]
   │                                             │                                    │
   │─── 1. POST .../{id}/reschedule/ ───────────►│                                    │
   │    (new_date, new_slot_time)                │─── 2. Validate Deadline            │
   │                                             │       (Must be <= Prev Day 11:59PM)│
   │                                             │─── 3. Check Target Slot Availability│
   │                                             │                                    │
   │                                             │─── 4. BEGIN TX ───────────────────►│
   │                                             │   - Lock Target Slot               │
   │                                             │   - Old Appt status='RESCHEDULED'  │
   │                                             │   - Create New Appointment         │
   │                                             │     (status='CONFIRMED',           │
   │                                             │      original_appointment=old_id)  │
   │                                             │   - Re-link Payment to New Appt    │
   │                                             │─── 5. COMMIT TX ──────────────────►│
   │                                             │                                    │
   │◄── 6. 200 OK (New Booking Reference Issued)─┤                                    │
```

---

## 8. Doctor Unavailability & Blast Radius Resolution

```
[Clinic Owner / Doctor]                    [Backend API]                    [Celery Worker]
          │                                      │                                 │
          │── 1. POST .../unavailability/ ──────►│                                 │
          │   (doctor_id, start_dt, end_dt,      │── 2. Create Unavailability      │
          │    reason='SICK_LEAVE')              │      Record in DB               │
          │                                      │── 3. Dispatch Celery Task ─────►│
          │◄─ 4. 202 Accepted (Processing) ──────┤                                 │
          │                                                                        │── 4. Query active appts
          │                                                                        │      in [start_dt, end_dt]
          │                                                                        │── 5. For each appointment:
          │                                                                        │      - status='CANCELLED_DOCTOR'
          │                                                                        │      - Trigger 100% Refund
          │                                                                        │      - Send Urgent SMS / Email
          │                                                                        │        with free priority
          │                                                                        │        reschedule link
```

---

## 9. In-Clinic Queue, Consultation & Prescription Workflow

```
[Receptionist]                [Doctor]                      [Backend]                 [Patient]
      │                          │                              │                         │
      │── 1. Patient Arrives ───►│                              │                         │
      │   Mark 'CHECKED_IN'      │                              │── Update Live Queue ───►│
      │   (Assign Token #4)      │                              │   (WebSocket broadcast) │
      │                          │                              │                         │
      │                          │── 2. Doctor calls Token #4 ─►│                         │
      │                          │   Mark 'IN_CONSULTATION'     │── WebSocket Notification│
      │                          │                              │   "Please enter Room 2" │
      │                          │                              │                         │
      │                          │── 3. Conduct Examination ───►│                         │
      │                          │   - Enter Vitals (BP, Temp)  │                         │
      │                          │   - Diagnosis & Notes        │                         │
      │                          │   - Add Prescription Items   │                         │
      │                          │     (Med, Dosage, 1-0-1)     │                         │
      │                          │                              │                         │
      │                          │── 4. POST .../prescriptions/►│                         │
      │                          │   Mark Appt 'COMPLETED'      │── Async Celery PDF Task │
      │                          │                              │   - Render Prescription │
      │                          │                              │   - Upload to S3        │
      │                          │                              │   - Send Download Link ─►
```
