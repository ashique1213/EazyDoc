# EazyDoc — Database Design & Schema Specification

## 1. Architectural Design Decisions & Core Questions

### 1.1. Doctor + Multiple Clinics
- **Design:** A doctor has a single, canonical global profile (`Doctor`) linked to their global login account (`User`). The doctor connects to clinics via an associative entity: `DoctorClinic`.
- **Rationale:** A doctor is a licensed professional across the healthcare system, not an employee belonging to only one clinic. Creating separate doctor accounts per clinic would fragment their medical registration identity, destroy cross-clinic scheduling visibility, prevent conflict detection, and confuse patients searching for a specific doctor.
- **Fields in `DoctorClinic`:**
  - `consultation_fee` & `online_consultation_fee` (clinic-specific pricing).
  - `appointment_duration_minutes` (e.g., 15 mins at high-volume Clinic A vs. 30 mins at Clinic B).
  - `status` (`INVITED`, `ACTIVE`, `PAUSED`, `TERMINATED`).
  - `joined_date`, `is_primary_clinic`.

### 1.2. Clinic-Specific Schedules
- **Design:** The `Schedule` entity has a direct foreign key to `DoctorClinic`, **never** directly to `Doctor`.
- **Rationale:** A doctor works different days and hours depending on the clinic agreement. Clinic A might have Dr. Rahul on Monday 09:00–13:00, while Clinic B has Dr. Rahul on Monday 16:00–20:00. Scoping schedules to `DoctorClinic` ensures that Clinic A's administration can only see, create, and modify shifts within their own clinic boundaries.

### 1.3. Schedule Conflict Prevention (Cross-Clinic)
- **Design:** PostgreSQL exclusion constraint using the `btree_gist` extension combined with service-layer validation.
- **Mechanism:**
  ```sql
  -- Conceptual Exclusion Constraint for non-overlapping doctor shifts across clinics
  ALTER TABLE schedules ADD CONSTRAINT no_overlapping_doctor_shifts
  EXCLUDE USING gist (
      doctor_id WITH =,
      day_of_week WITH =,
      int4range(EXTRACT(epoch FROM start_time)::int, EXTRACT(epoch FROM end_time)::int) WITH &&
  ) WHERE (is_active = true);
  ```
- **Service Layer Pre-Validation:** When a clinic admin attempts to add a schedule shift for Dr. D on Monday `[10:00, 13:00]`:
  1. Service queries `Schedule.objects.filter(doctor_clinic__doctor=doctor, day_of_week=day, is_active=True)`.
  2. Compares intervals: `start_time < existing.end_time AND end_time > existing.start_time`.
  3. If overlap is detected, an explicit `ScheduleConflictException` is raised detailing the conflicting clinic and shift hours.

### 1.4. Double Booking Prevention (Pessimistic Locking & Database Constraints)
- **Design:** Defense-in-depth using a 3-layer anti-double-booking protection:
  1. **Application Layer (Redis Hold):** When a patient clicks a slot, a 10-minute ephemeral reservation key is set in Redis: `SET slot_hold:<doc_clinic_id>:<date>:<time> <patient_id> NX EX 600`. If `NX` returns null, another patient is currently checking out this slot.
  2. **Transaction Isolation (`select_for_update`):** During payment verification and appointment creation:
     ```python
     with transaction.atomic():
         conflict = Appointment.objects.select_for_update().filter(
             doctor_clinic=doctor_clinic,
             appointment_date=date,
             appointment_time=time,
             status__in=[AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]
         ).exists()
         if conflict:
             raise SlotAlreadyBookedException()
         appointment.status = AppointmentStatus.CONFIRMED
         appointment.save()
     ```
  3. **Storage Engine Unique Partial Index:**
     ```sql
     CREATE UNIQUE INDEX unique_active_slot_booking ON appointments (
         doctor_clinic_id,
         appointment_date,
         appointment_time
     ) WHERE status IN ('PENDING', 'CONFIRMED', 'CHECKED_IN', 'IN_CONSULTATION');
     ```
     This physical database constraint guarantees that even in extreme edge cases of network race conditions, two active appointments can never be persisted for the same slot.

### 1.5. Cancellation & Rescheduling Deadline (11:59 PM Previous Day)
- **Design:** Calculated strictly against the clinic's local timezone (default: `Asia/Kolkata`).
- **Calculation Formula:**
  ```python
  import zoneinfo
  from datetime import datetime, time, timedelta

  def get_cancellation_deadline(appointment_date, clinic_tz_str="Asia/Kolkata"):
      clinic_tz = zoneinfo.ZoneInfo(clinic_tz_str)
      # Previous day date
      previous_day = appointment_date - timedelta(days=1)
      # 23:59:59 on the previous day in clinic timezone
      deadline_local = datetime.combine(previous_day, time(23, 59, 59), tzinfo=clinic_tz)
      return deadline_local

  def is_patient_cancellation_allowed(appointment):
      clinic_tz = zoneinfo.ZoneInfo(appointment.doctor_clinic.clinic.timezone)
      now_clinic_time = datetime.now(clinic_tz)
      deadline = get_cancellation_deadline(appointment.appointment_date, appointment.doctor_clinic.clinic.timezone)
      return now_clinic_time <= deadline
  ```
- **Rationale:** Storing clinic timezone on the `Clinic` record ensures multi-region compatibility while strictly anchoring the business rule to the clinic's local operating day.

### 1.6. Doctor Unavailability & Blast Radius Resolution
- **Design:** Entity `DoctorUnavailability` captures:
  - `doctor_id` (FK to Doctor).
  - `clinic_id` (FK to Clinic, nullable: `NULL` means unavailable across ALL clinics; specific clinic ID means unavailable only at that clinic).
  - `start_datetime`, `end_datetime` (in UTC).
  - `reason` (`SICK_LEAVE`, `EMERGENCY`, `CONFERENCE`, `PERSONAL`, `CLINIC_CLOSURE`).
- **Resolution Query:**
  ```python
  affected_appointments = Appointment.objects.filter(
      doctor_clinic__doctor=doctor,
      status__in=[AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING],
      appointment_date__gte=start_date,
      appointment_date__lte=end_date
  )
  if unavailability.clinic_id:
      affected_appointments = affected_appointments.filter(doctor_clinic__clinic_id=unavailability.clinic_id)
  ```
- **Execution:** When `DoctorUnavailability` is created, a background Celery task `process_doctor_unavailability_task.delay(unavailability_id)` is dispatched. It iterates through affected appointments, transitions them to `CANCELLED_BY_DOCTOR`, issues full Razorpay refunds, and queues notifications to all affected patients.

### 1.7. Platform Commission & Financial Split Storage
- **Design:** All financial figures are stored as fixed-precision `DecimalField(max_digits=10, decimal_places=2)` on both `Appointment` and `Payment`.
- **Storage Fields:**
  - `gross_amount`: Exact fee paid by patient (e.g., `500.00`).
  - `platform_commission_rate`: Stored as a historical snapshot (e.g., `5.00` representing 5%) so future global rate changes do not alter past historical earnings.
  - `platform_commission_amount`: `gross_amount * (platform_commission_rate / 100)` = `25.00`.
  - `clinic_settlement_amount`: `gross_amount - platform_commission_amount` = `475.00`.
  - `payment_gateway_fee`: e.g., `11.80` (Razorpay 2% + 18% GST).
  - `settlement_status`: `PENDING`, `BATCHED`, `SETTLED`, `REFUNDED`.
- **Patient Privacy Guarantee:** The API serializer exposed to patients (`PatientAppointmentDetailSerializer`) only serializes `gross_amount` as `consultation_fee`. The fields `platform_commission_rate`, `platform_commission_amount`, and `clinic_settlement_amount` are strictly omitted from patient endpoints.

### 1.8. Multi-Tenant Isolation
- **Design:** Logical isolation enforced at the ORM QuerySet level via `TenantQuerySetMixin`.
- **Query Protection:** Every clinic-scoped entity (`Appointment`, `ClinicStaff`, `Consultation`, `Payment`) carries a foreign key to `Clinic`. All ViewSets automatically scope queries:
  ```python
  def get_queryset(self):
      return super().get_queryset().filter(clinic=self.request.tenant_clinic)
  ```
- **Object-Level Permission (`IsClinicMember`):** Ensures that attempts to view or mutate an ID belonging to Clinic B while authenticated under Clinic A raise `403 Forbidden` / `404 Not Found`.

---

## 2. Entity Relational Diagram (ERD Overview)

```
       ┌────────────────────────┐
       │         User           │
       │ (Auth, Email, Phone)   │
       └───────────┬────────────┘
                   │ 1:1
       ┌───────────┴────────────┐            ┌────────────────────────┐
       │        Doctor          │            │         Clinic         │
       │ (RegNo, Specialization)│            │ (Name, RegNo, Timezone)│
       └───────────┬────────────┘            └───────────┬────────────┘
                   │                                     │
                   └──────────────┐       ┌──────────────┘
                                  ▼       ▼
                       ┌────────────────────────────┐
                       │        DoctorClinic        │ (M2M Link)
                       │ (Fee, Duration, Status)    │
                       └──────────────┬─────────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               ▼                      ▼                      ▼
    ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
    │      Schedule      │ │    Appointment     │ │  BlockedSlot       │
    │ (Day, Start, End)  │ │ (Date, Time, Status│ │ (Date, Slot, Reason│
    └────────────────────┘ └──────────┬─────────┘ └────────────────────┘
                                      │
                   ┌──────────────────┼──────────────────┐
                   ▼                  ▼                  ▼
        ┌────────────────────┐┌────────────────────┐┌────────────────────┐
        │      Payment       ││    Consultation    ││      Review        │
        │ (Gross, Comm, Sett)││ (Notes, Diagnosis) ││ (Rating, Comment)  │
        └────────────────────┘└──────────┬─────────┘└────────────────────┘
                                         │
                                         ▼
                              ┌────────────────────┐
                              │    Prescription    │
                              │ (Number, PDF, Meds)│
                              └──────────┬─────────┘
                                         │ 1:N
                                         ▼
                              ┌────────────────────┐
                              │  PrescriptionItem  │
                              │ (Dosage, Frequency)│
                              └────────────────────┘
```

---

## 3. Detailed Data Dictionary & Schema Definitions

### 3.1. Core Identity & User Models

#### `users_user`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Global identifier |
| `email` | VARCHAR(255) | Unique, Index | Primary login email |
| `phone_number` | VARCHAR(20) | Unique, Index | Mobile number for OTP & SMS |
| `password` | VARCHAR(128) | Not Null | Argon2 / PBKDF2 hashed password |
| `first_name` | VARCHAR(100) | Not Null | First name |
| `last_name` | VARCHAR(100) | Not Null | Last name |
| `role` | VARCHAR(20) | Not Null, Index | `SUPER_ADMIN`, `CLINIC_OWNER`, `STAFF`, `DOCTOR`, `PATIENT` |
| `is_active` | BOOLEAN | Default: `true` | Account active flag |
| `is_verified` | BOOLEAN | Default: `false` | Email/Phone verified |
| `created_at` | TIMESTAMPTZ | Default: `now()` | Audit creation timestamp |
| `updated_at` | TIMESTAMPTZ | Auto-now | Audit update timestamp |

#### `patients_patient`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Patient record ID |
| `user` | UUID | FK -> `users_user(id)`, 1:1, Unique, OnDelete: CASCADE | Associated user account |
| `date_of_birth` | DATE | Nullable | Date of birth for age calculation |
| `gender` | VARCHAR(10) | `MALE`, `FEMALE`, `OTHER`, `UNDISCLOSED` | Biological gender |
| `blood_group` | VARCHAR(5) | `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-` | Blood group |
| `emergency_contact_name` | VARCHAR(100) | Nullable | Emergency contact person |
| `emergency_contact_phone`| VARCHAR(20) | Nullable | Emergency contact number |
| `address` | TEXT | Nullable | Residential address |

---

### 3.2. Clinic & Staff Management

#### `clinics_clinic`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Clinic ID |
| `owner` | UUID | FK -> `users_user(id)`, OnDelete: RESTRICT, Index | Clinic owner |
| `name` | VARCHAR(255) | Not Null, Index | Legal / Commercial clinic name |
| `slug` | VARCHAR(255) | Unique, Index | Unique SEO friendly URL slug with auto collision suffix |
| `description` | TEXT | Blank, Default: `""` | Clinical biography / facility description |
| `email` | VARCHAR(255) | Not Null | Official reception contact email |
| `phone` | VARCHAR(20) | Not Null | Official contact phone (`phone_number` alias) |
| `address_line_1` | VARCHAR(255) | Not Null | Street address |
| `address_line_2` | VARCHAR(255) | Nullable, Blank | Landmark, unit, or suite |
| `city` | VARCHAR(100) | Not Null, Index | City |
| `state` | VARCHAR(100) | Not Null | State / Province |
| `pincode` | VARCHAR(20) | Not Null | Postal / PIN code (`postal_code` alias) |
| `country` | VARCHAR(100) | Default: `'India'` | Country of establishment |
| `logo` | VARCHAR(500) | Nullable, ImageField | Uploaded clinic logo (max 2MB, validated) |
| `status` | VARCHAR(20) | Index, Default: `'PENDING'` | `DRAFT`, `PENDING`, `APPROVED`, `REJECTED`, `SUSPENDED` |
| `verification_notes`| TEXT | Nullable | Admin notes or required correction reason |
| `timezone` | VARCHAR(50) | Default: `'Asia/Kolkata'` | Operating timezone |
| `is_verified` | BOOLEAN | Default: `false`, Index | True strictly when status is `APPROVED` |
| `approved_at` | TIMESTAMPTZ | Nullable | Timestamp when approved by Super Admin |
| `approved_by` | UUID | FK -> `users_user(id)`, Nullable, OnDelete: SET_NULL | Super Admin user who approved the clinic |
| `created_at` | TIMESTAMPTZ | Default: `now()`, Index | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | Auto-now | Record last update timestamp |

#### `clinics_clinicstaff`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Staff link ID |
| `user` | UUID | FK -> `users_user(id)`, OnDelete: CASCADE | Staff login user |
| `clinic` | UUID | FK -> `clinics_clinic(id)`, OnDelete: CASCADE | Employing clinic |
| `staff_role` | VARCHAR(30) | Default: `'RECEPTIONIST'` | `RECEPTIONIST`, `NURSE`, `CLINIC_MANAGER` |
| `is_active` | BOOLEAN | Default: `true` | Active employment status |
| *Constraints* | UniqueConstraint | `(user, clinic)` | A user has one role per clinic |

---

### 3.3. Doctor & Clinic Association

#### `doctors_specialization`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Specialization ID |
| `name` | VARCHAR(100) | Unique, Index | e.g., 'Cardiology', 'Dermatology' |
| `slug` | VARCHAR(100) | Unique | URL slug |
| `icon_url` | VARCHAR(500) | Nullable | Display icon |

#### `doctors_doctor`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Global Doctor ID |
| `user` | UUID | FK -> `users_user(id)`, 1:1, Unique, OnDelete: CASCADE | Associated user account |
| `registration_number`| VARCHAR(100) | Not Null, Index | Official medical council registration identifier |
| `normalized_registration_number`| VARCHAR(100) | Not Null, Index | Whitespace-stripped and uppercased registration number |
| `registration_council`| VARCHAR(200)| Not Null, Index | Issuing medical council authority name |
| `normalized_registration_council`| VARCHAR(200)| Not Null, Index | Uppercased council name with collapsed whitespace |
| `registration_state` | VARCHAR(100) | Blank, Default: `""` | Issuing state or jurisdiction |
| `full_name` | VARCHAR(200) | Not Null | Practitioner full name |
| `specialization` | VARCHAR(150) | Not Null, Index | Clinical specialty (e.g. Cardiology) |
| `qualifications` | VARCHAR(255) | Not Null | Academic & medical qualifications (e.g. MBBS, MD) |
| `years_of_experience` | INTEGER | Check: `>= 0`, Default: 0 | Years of active clinical practice |
| `bio` | TEXT | Blank, Default: `""` | Professional biography |
| `languages` | VARCHAR(255) | Blank, Default: `'English'` | Spoken consultation languages |
| `profile_photo` | VARCHAR(500) | Nullable, ImageField | Uploaded portrait photo (max 2MB, validated) |
| `verification_status`| VARCHAR(20) | Index, Default: `'DRAFT'` | `DRAFT`, `PENDING`, `VERIFIED`, `REJECTED`, `SUSPENDED` |
| `is_verified` | BOOLEAN | Default: `false`, Index | True strictly when status is `VERIFIED` |
| `verification_notes`| TEXT | Blank, Default: `""` | Super Admin review notes or rejection reason |
| `submitted_at` | TIMESTAMPTZ | Nullable | Submission timestamp for admin review |
| `verified_at` | TIMESTAMPTZ | Nullable | Timestamp of verification decision |
| `verified_by` | UUID | FK -> `users_user(id)`, Nullable, OnDelete: SET_NULL | Verifying Super Admin user |
| `created_at` | TIMESTAMPTZ | Default: `now()`, Index | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | Auto-now | Record last update timestamp |
| *Constraints* | UniqueConstraint | `(normalized_registration_council, normalized_registration_number)` | Council-scoped registration uniqueness |
| *Constraints* | CheckConstraint | `verification_status IN ('DRAFT', 'PENDING', 'VERIFIED', 'REJECTED', 'SUSPENDED')` | Valid lifecycle status |
| *Constraints* | CheckConstraint | `years_of_experience >= 0` | Non-negative experience |

#### `doctors_doctordocument`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Document ID |
| `doctor` | UUID | FK -> `doctors_doctor(id)`, OnDelete: CASCADE | Owning doctor profile |
| `document_type` | VARCHAR(50) | Not Null | `REGISTRATION_CERTIFICATE`, `DEGREE_CERTIFICATE`, `GOVERNMENT_ID`, `OTHER` |
| `file` | VARCHAR(500) | FileField, Private Storage | Encrypted/Private file storage path (max 5MB, PDF/JPG/PNG) |
| `file_name` | VARCHAR(255) | Not Null | Original filename |
| `file_size` | INTEGER | Not Null | File size in bytes |
| `mime_type` | VARCHAR(100) | Blank, Default: `""` | File MIME content type |
| `uploaded_at` | TIMESTAMPTZ | Default: `now()` | Upload timestamp |

#### `doctor_clinics_doctorclinic`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Association ID |
| `doctor` | UUID | FK -> `doctors_doctor(id)`, OnDelete: CASCADE | Reusable global Doctor reference |
| `clinic` | UUID | FK -> `clinics_clinic(id)`, OnDelete: CASCADE | Clinic establishment reference |
| `status` | VARCHAR(20) | Default: `'INVITED'`, Index | Association status (`INVITED`, `ACTIVE`, `REJECTED`, `REMOVED`, `SUSPENDED`) |
| `invited_by` | UUID | FK -> `accounts_user(id)`, OnDelete: SET_NULL, Nullable | Clinic owner who initiated the invitation |
| `invitation_message` | TEXT | Blank, Default: `""` | Optional welcome note or affiliation terms |
| `consultation_fee` | DECIMAL(10,2)| Not Null, Default: `0.00`, Check: `>= 0` | Clinic-specific in-person consultation fee (INR) |
| `follow_up_fee` | DECIMAL(10,2)| Not Null, Default: `0.00`, Check: `>= 0` | Optional clinic-specific follow-up consultation fee (INR) |
| `appointment_duration_minutes`| INTEGER | Default: `15`, Check: `>= 5 AND <= 240` | Slot duration in minutes |
| `accepted_at` | TIMESTAMPTZ | Nullable | Timestamp when doctor accepted the invitation |
| `rejected_at` | TIMESTAMPTZ | Nullable | Timestamp when doctor declined the invitation |
| `removed_at` | TIMESTAMPTZ | Nullable | Timestamp when clinic owner ended active association |
| `created_at` | TIMESTAMPTZ | Default: `now()` | Initial invitation creation timestamp |
| `updated_at` | TIMESTAMPTZ | Default: `now()`, on update | Timestamp of last modification |
| *Constraints* | UniqueConstraint | `(doctor, clinic)` | Strictly one association record per doctor-clinic pair |
| *Constraints* | CheckConstraint | `status IN ('INVITED','ACTIVE','REJECTED','REMOVED','SUSPENDED')` | Valid lifecycle statuses |
| *Constraints* | CheckConstraint | `consultation_fee >= 0` | Non-negative in-clinic fee |
| *Constraints* | CheckConstraint | `follow_up_fee >= 0` | Non-negative follow-up fee |
| *Constraints* | CheckConstraint | `appointment_duration_minutes >= 5 AND appointment_duration_minutes <= 240` | Valid slot duration range |
| *Indexes* | B-Tree Index | `(clinic, status)` | Filter clinic doctors by active/pending |
| *Indexes* | B-Tree Index | `(doctor, status)` | Filter doctor affiliations by active/pending |
| *Indexes* | B-Tree Index | `(status, created_at)` | Temporal indexing of association status |

---

### 3.4. Schedules & Availability

#### `schedules_schedule`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Schedule ID |
| `doctor_clinic` | UUID | FK -> `doctor_clinics_doctorclinic(id)`, CASCADE | Scoped association |
| `day_of_week` | SMALLINT | Check: `>= 0 AND <= 6`, Index | 0=Monday, 6=Sunday |
| `start_time` | TIME | Not Null | Shift start time (e.g. 09:00:00) |
| `end_time` | TIME | Not Null | Shift end time (e.g. 13:00:00) |
| `slot_duration_minutes`| INTEGER | Default: `15`, Check: `> 0` | Duration per appointment slot |
| `max_patients_per_slot`| INTEGER | Default: `1` | Capacity per slot (1 for individual) |
| `is_active` | BOOLEAN | Default: `true` | Schedule toggle |
| *Constraints* | CheckConstraint | `start_time < end_time` | Logical shift hours |

#### `schedules_doctorunavailability`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Leave / Unavailability ID |
| `doctor` | UUID | FK -> `doctors_doctor(id)`, CASCADE | Doctor reference |
| `clinic` | UUID | FK -> `clinics_clinic(id)`, Nullable, CASCADE | Null = all clinics, or specific clinic |
| `start_datetime` | TIMESTAMPTZ | Not Null, Index | Unavailability begin (UTC) |
| `end_datetime` | TIMESTAMPTZ | Not Null, Index | Unavailability end (UTC) |
| `reason` | VARCHAR(50) | Not Null | `SICK_LEAVE`, `EMERGENCY`, `CONFERENCE`, `PERSONAL`, `CLINIC_CLOSURE`, `OTHER` |
| `notes` | TEXT | Nullable | Internal explanation |
| *Constraints* | CheckConstraint | `start_datetime < end_datetime`| Chronological ordering |

#### `schedules_blockedslot`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Blocked slot ID |
| `doctor_clinic` | UUID | FK -> `doctor_clinics_doctorclinic(id)`, CASCADE | Scoped association |
| `date` | DATE | Not Null, Index | Blocked date |
| `start_time` | TIME | Not Null | Blocked slot time |
| `reason` | VARCHAR(255) | Nullable | e.g. 'VIP patient', 'Maintenance' |
| *Constraints* | UniqueConstraint | `(doctor_clinic, date, start_time)` | Unique per slot |

---

### 3.5. Appointments & Payments

#### `appointments_appointment`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Appointment ID |
| `booking_reference` | VARCHAR(32) | Unique, Index | Human readable code (e.g. `EZD-202610-ABCD`) |
| `doctor_clinic` | UUID | FK -> `doctor_clinics_doctorclinic(id)`, PROTECT | Scoped Doctor & Clinic |
| `patient` | UUID | FK -> `patients_patient(id)`, PROTECT | Booking patient |
| `appointment_date` | DATE | Not Null, Index | Date of visit |
| `appointment_time` | TIME | Not Null, Index | Slot start time |
| `end_time` | TIME | Not Null | Slot end time |
| `appointment_type` | VARCHAR(20) | Default: `'IN_PERSON'` | `IN_PERSON`, `VIDEO_CONSULT` |
| `status` | VARCHAR(30) | Not Null, Index | `PENDING`, `CONFIRMED`, `CHECKED_IN`, `IN_CONSULTATION`, `COMPLETED`, `CANCELLED_BY_PATIENT`, `CANCELLED_BY_DOCTOR`, `CANCELLED_BY_CLINIC`, `RESCHEDULED`, `NO_SHOW` |
| `token_number` | INTEGER | Nullable | Daily queue token at the clinic |
| `cancellation_reason`| TEXT | Nullable | Reason for cancellation |
| `cancelled_at` | TIMESTAMPTZ | Nullable | Timestamp of cancellation |
| `cancelled_by` | UUID | FK -> `users_user(id)`, Nullable | User who performed cancellation |
| `original_appointment`| UUID | FK -> self, Nullable | If rescheduled, link to previous appt |
| `created_at` | TIMESTAMPTZ | Default: `now()` | Created timestamp |
| `updated_at` | TIMESTAMPTZ | Auto-now | Updated timestamp |

#### `payments_payment`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Payment record ID |
| `appointment` | UUID | FK -> `appointments_appointment(id)`, 1:1, PROTECT | Associated appointment |
| `patient` | UUID | FK -> `patients_patient(id)`, PROTECT | Payer |
| `clinic` | UUID | FK -> `clinics_clinic(id)`, PROTECT | Beneficiary clinic (for fast reporting) |
| `razorpay_order_id` | VARCHAR(100) | Unique, Index, Not Null | Razorpay Order ID |
| `razorpay_payment_id`| VARCHAR(100) | Unique, Index, Nullable | Razorpay Payment ID |
| `razorpay_signature` | VARCHAR(255) | Nullable | Cryptographic signature |
| `currency` | VARCHAR(10) | Default: `'INR'` | Currency code |
| `gross_amount` | DECIMAL(10,2)| Not Null, Check: `> 0` | Total patient consultation fee |
| `platform_commission_rate`| DECIMAL(5,2)| Not Null | Commission percentage (e.g. 5.00) |
| `platform_commission_amount`| DECIMAL(10,2)| Not Null | Computed platform revenue |
| `clinic_settlement_amount`| DECIMAL(10,2)| Not Null | Net payout to clinic |
| `gateway_fee_amount` | DECIMAL(10,2)| Default: `0.00` | Estimated gateway fee |
| `status` | VARCHAR(20) | Default: `'INITIATED'`, Index | `INITIATED`, `SUCCESS`, `FAILED`, `REFUNDED`, `PARTIALLY_REFUNDED` |
| `settlement_status` | VARCHAR(20) | Default: `'PENDING'`, Index | `PENDING`, `BATCHED`, `SETTLED` |
| `verified_at` | TIMESTAMPTZ | Nullable | Server-side verification timestamp |
| `refund_id` | VARCHAR(100) | Nullable | Razorpay refund identifier |
| `refund_amount` | DECIMAL(10,2)| Nullable | Amount refunded |
| `created_at` | TIMESTAMPTZ | Default: `now()` | Creation timestamp |

---

### 3.6. Consultations & Digital Prescriptions

#### `consultations_consultation`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Consultation ID |
| `appointment` | UUID | FK -> `appointments_appointment(id)`, 1:1, PROTECT | Associated appointment |
| `doctor` | UUID | FK -> `doctors_doctor(id)`, PROTECT | Attending doctor |
| `clinic` | UUID | FK -> `clinics_clinic(id)`, PROTECT | Clinic venue |
| `patient` | UUID | FK -> `patients_patient(id)`, PROTECT | Patient |
| `chief_complaint` | TEXT | Not Null | Primary presenting symptoms |
| `clinical_notes` | TEXT | Nullable | Examination and clinical findings |
| `diagnosis` | TEXT | Not Null | Provisional / Confirmed diagnosis |
| `vitals` | JSONB | Default: `'{}'` | `{ bp: '120/80', pulse: 72, temp: 98.6, spo2: 99, weight: 68 }` |
| `follow_up_date` | DATE | Nullable | Recommended follow-up date |
| `created_at` | TIMESTAMPTZ | Default: `now()` | Timestamp |

#### `consultations_prescription`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Prescription ID |
| `consultation` | UUID | FK -> `consultations_consultation(id)`, 1:1, PROTECT | Linked consultation |
| `prescription_number`| VARCHAR(50)| Unique, Index | Unique identifier (e.g. `RX-202610-00123`) |
| `general_advice` | TEXT | Nullable | Dietary, lifestyle instructions |
| `pdf_file_url` | VARCHAR(500) | Nullable | Secure S3 URL of generated PDF |
| `created_at` | TIMESTAMPTZ | Default: `now()` | Timestamp |

#### `consultations_prescriptionitem`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Item ID |
| `prescription` | UUID | FK -> `consultations_prescription(id)`, CASCADE | Parent prescription |
| `medicine_name` | VARCHAR(255) | Not Null | Generic or brand name |
| `dosage` | VARCHAR(50) | Not Null | e.g. '500 mg', '10 ml' |
| `frequency` | VARCHAR(50) | Not Null | e.g. '1-0-1' (Morning - Afternoon - Night) |
| `duration` | VARCHAR(50) | Not Null | e.g. '5 days', '1 month' |
| `route` | VARCHAR(30) | Default: `'ORAL'` | `ORAL`, `TOPICAL`, `INHALATION`, `IV`, `IM` |
| `instructions` | VARCHAR(255) | Nullable | e.g. 'After food with warm water' |

---

### 3.7. Reviews, Documents, Audit & Platform Config

#### `reviews_review`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Review ID |
| `appointment` | UUID | FK -> `appointments_appointment(id)`, 1:1, CASCADE | Verifiable booking link |
| `patient` | UUID | FK -> `patients_patient(id)`, CASCADE | Author |
| `doctor` | UUID | FK -> `doctors_doctor(id)`, CASCADE | Rated doctor |
| `clinic` | UUID | FK -> `clinics_clinic(id)`, CASCADE | Rated clinic |
| `rating` | SMALLINT | Check: `>= 1 AND <= 5` | Star rating (1 to 5) |
| `comment` | TEXT | Nullable | Patient feedback |
| `is_published` | BOOLEAN | Default: `true` | Public visibility flag |

#### `documents_medicaldocument`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Default: `uuid4` | Document ID |
| `patient` | UUID | FK -> `patients_patient(id)`, CASCADE | Patient owner |
| `appointment` | UUID | FK -> `appointments_appointment(id)`, Nullable, SET_NULL | Optional consultation link |
| `document_type` | VARCHAR(30) | Not Null | `LAB_REPORT`, `PRESCRIPTION`, `DISCHARGE_SUMMARY`, `IMAGING` |
| `title` | VARCHAR(255) | Not Null | Document title |
| `file_key` | VARCHAR(500) | Not Null | Private S3 storage key |
| `file_size_bytes` | BIGINT | Check: `> 0` | File size |
| `mime_type` | VARCHAR(100) | Not Null | e.g. `application/pdf`, `image/jpeg` |

#### `audit_auditlog`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | BIGSERIAL | Primary Key | Sequential append-only ID |
| `actor` | UUID | FK -> `users_user(id)`, Nullable, SET_NULL | User who performed action |
| `clinic` | UUID | FK -> `clinics_clinic(id)`, Nullable, CASCADE | Associated clinic tenant |
| `action` | VARCHAR(100) | Not Null, Index | e.g., `APPOINTMENT_CANCELLED`, `REFUND_ISSUED` |
| `resource_type` | VARCHAR(50) | Not Null, Index | e.g., `Appointment`, `Payment` |
| `resource_id` | VARCHAR(100) | Not Null | UUID of modified record |
| `ip_address` | INET | Nullable | Client IP |
| `user_agent` | VARCHAR(500) | Nullable | Browser User Agent |
| `details` | JSONB | Default: `'{}'` | Snapshot of changes / payload |
| `created_at` | TIMESTAMPTZ | Default: `now()`, Index | Immutable timestamp |

#### `platform_platformsetting`
| Field Name | Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `key` | VARCHAR(100) | Primary Key | e.g., `DEFAULT_COMMISSION_PERCENTAGE` |
| `value` | VARCHAR(255) | Not Null | e.g., `'5.00'` |
| `data_type` | VARCHAR(20) | Default: `'STRING'` | `DECIMAL`, `INTEGER`, `BOOLEAN`, `STRING` |
| `description` | TEXT | Nullable | Human readable explanation |
| `updated_at` | TIMESTAMPTZ | Auto-now | Last modified timestamp |
