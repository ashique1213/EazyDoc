# Clinic Owner Dashboard & Clinic Operations Documentation

## 1. Overview & Multi-Tenant Architecture

The Clinic Operations module empowers authorized Clinic Owners and designated Staff members to manage approved medical clinics and day-to-day healthcare workflows on the EazyDoc multi-tenant SaaS platform.

### Tenant Isolation & Scoping Guarantees
- **Strict User & Clinic Scoping**: Every backend request requires a valid JWT and verifies that the authenticated user is either the registered owner of the clinic or an active staff member assigned to that clinic with the relevant permission.
- **Zero Cross-Clinic Data Leaks**: Clinic A cannot inspect, modify, or query Clinic B's metrics, doctor associations, appointments, staff list, or financial transactions. Direct Object Reference (IDOR/BOLA) vulnerabilities are systematically prevented by object-level permission checks (`check_clinic_access`).
- **Role Boundary Enforcement**:
  - Clinic Owners and Staff **cannot** self-approve clinics or modify clinic verification statuses (managed exclusively by Super Administrators).
  - Clinic Owners and Staff **cannot** alter doctor global verification statuses.
  - Clinic Owners and Staff **cannot** modify default or clinic-specific platform commission rates.
  - Staff members **cannot** escalate their own privileges or promote themselves to Clinic Owner or Super Admin.

---

## 2. Staff Roles & Permission Matrix

The system supports a granular, role-based permission system scoped to individual clinics via the `ClinicStaff` model. Staff members only possess privileges explicitly granted by the clinic owner.

| Permission Key | Description | Accessible Endpoints & UI Views |
| :--- | :--- | :--- |
| `VIEW_APPOINTMENTS` | View clinic appointment desk, filters, booking details, and historical timeline | `GET /api/v1/clinics/{id}/appointments/`, `GET /api/v1/clinics/{id}/appointments/{aid}/` |
| `MANAGE_APPOINTMENTS` | Execute lifecycle actions: confirm, complete, mark no-show, initiate clinic exception cancellation/rescheduling | `POST .../{aid}/confirm/`, `POST .../{aid}/complete/`, `POST .../{aid}/no-show/`, `POST .../{aid}/cancel/` |
| `VIEW_DOCTORS` | Browse associated doctors, check active associations, and view public fees | `GET /api/v1/clinics/{id}/doctors/`, `GET /api/v1/clinics/{id}/doctor-invitations/` |
| `MANAGE_DOCTOR_ASSOCIATIONS` | Invite verified doctors, configure clinic consultation and follow-up fees, remove affiliations | `POST .../doctor-invitations/`, `PATCH .../doctors/{did}/settings/`, `DELETE .../doctors/{did}/` |
| `MANAGE_SCHEDULES` | Configure clinic shift hours, manage doctor working windows, and view master calendar | `GET /api/v1/clinics/{id}/calendar/`, `POST /api/v1/schedules/` |
| `VIEW_FINANCIAL_SUMMARY` | Access gross revenue reports, platform commission splits, and payment transaction ledger | `GET /api/v1/clinics/{id}/finance/summary/`, `GET /api/v1/clinics/{id}/finance/payments/` |
| `MANAGE_CLINIC_PROFILE` | Update clinic address, public contact details, timezone, and operational closure dates | `PATCH /api/v1/clinics/{id}/management/`, `POST /api/v1/clinics/{id}/closures/` |
| `MANAGE_STAFF` | Invite new staff members, modify operational permissions, or revoke staff access | `GET /api/v1/clinics/{id}/staff/`, `POST .../staff/`, `PATCH .../staff/{sid}/`, `DELETE .../staff/{sid}/` |

> [!NOTE]
> Clinic owners implicitly hold all 8 permissions across their owned clinics. Staff invitations create or link a user account with role `STAFF`, scoped strictly to that specific clinic via `ClinicStaff.user.staff_profile`.

---

## 3. Clinic Operations Workflows

### 3.1 Clinic Dashboard Overview (`/clinic/dashboard`)
Displays operational metrics aggregated via PostgreSQL database queries:
- **Doctor Metrics**: Active affiliated doctors and pending invitations.
- **Appointment Metrics**: Today's, upcoming, completed, cancelled, and appointments requiring attention.
- **Financial Snapshot**: Gross collections and calculated clinic share.
- **Appointment Trends**: Daily grouped volume of booked, completed, and cancelled consultations.
- **Date Range Filters**: Supports `today`, `this_week`, `this_month`, and custom date ranges. All date bounds are evaluated within the **clinic's configured local timezone**.

### 3.2 Clinic Profile & Operating Settings (`/clinic/settings`)
Authorized owners and staff with `MANAGE_CLINIC_PROFILE` can update:
- Clinic name and public description
- Contact email and phone number
- Complete physical address (lines, city, state, pincode, country)
- Operational timezone (e.g., `Asia/Kolkata`, `America/New_York`, `UTC`)

**Security Rules**:
- Read-only fields (`status`, `is_verified`, `commission_rate`) cannot be updated by clinic owners. Attempts to submit modifications are rejected or safely ignored by `ClinicManagementUpdateSerializer`.

### 3.3 Clinic Closure & Facility Unavailability Workflow
When a clinic needs to close for public holidays, maintenance, or emergencies:
1. **Interactive Conflict Preview** (`POST /api/v1/clinics/{id}/closures/preview/`):
   - Evaluates the date interval in the clinic timezone.
   - Identifies any active, non-cancelled appointments (`BOOKED`, `CONFIRMED`, `RESCHEDULED`).
   - Returns a structured preview containing affected count and booking references.
2. **Confirmation & Creation** (`POST /api/v1/clinics/{id}/closures/`):
   - Requires explicit confirmation (`confirmed: true`) if existing appointments exist.
   - Records the closure with start date, end date, reason, notes, and the creating user for auditing.
   - Prevents patients from booking slots on those dates via schedule availability checks.
3. **Reopening** (`DELETE /api/v1/clinics/{id}/closures/{closure_id}/`):
   - Removes the closure record and restores availability.

### 3.4 Doctor Association & Fee Management (`/clinic/doctors`)
- Allows searching and issuing invitations to verified doctors.
- Customizes clinic-specific consultation fee, follow-up fee, and appointment slot duration.
- Clinic-specific fees are isolated per clinic and do not affect a doctor's fees at other clinics.
- Removing an association preserves all existing appointment history, financial logs, and audit records.

---

## 4. Appointment Desk & Exception Lifecycle

Clinic staff and owners manage patient bookings through `/clinic/appointments`:

### Supported Lifecycle Actions
1. **Confirm Appointment** (`POST /api/v1/clinics/{id}/appointments/{aid}/confirm/`):
   - Transitions an appointment from `BOOKED` to `CONFIRMED`.
   - Records actor and appends to the appointment history timeline.
2. **Complete Appointment** (`POST /api/v1/clinics/{id}/appointments/{aid}/complete/`):
   - Transitions an appointment from `CONFIRMED` to `COMPLETED`.
3. **Mark No-Show** (`POST /api/v1/clinics/{id}/appointments/{aid}/no-show/`):
   - Marks appointment as `NO_SHOW` when a patient fails to arrive.
4. **Exception Cancellation & Doctor Unavailability**:
   - Authorized clinic staff can initiate exception cancellations when a doctor is ill or emergency clinic closure occurs.
   - Bypasses standard patient cancellation cutoffs while preserving the full audit trail and reason.
5. **Rescheduling Desk**:
   - Reuses availability calculation service to identify valid alternative slots without cross-clinic double booking.

---

## 5. Master Calendar & Availability Behavior (`/clinic/calendar`)

- Provides an interactive Day and Week view of:
  - Working doctor shifts and consultation windows.
  - Confirmed and booked patient appointments.
  - Doctor leaves and reported unavailability periods.
  - Facility closure dates and public holidays.
- **Timezone Awareness**: All calendar slots and appointments are translated to the clinic's local timezone.
- **Authoritative Booking**: The visual empty space on the calendar is purely informational; booking eligibility remains strictly enforced by the backend availability engine.

---

## 6. Financial Summary Definitions & Settlement Policy (`/clinic/finance`)

### Financial Rulebook & Metrics
1. **Gross Patient Collections**: Total funds paid by patients for appointments at this clinic (`status = PAID`).
2. **Platform Commission Split**: Platform SaaS fees retained, calculated from **immutable commission snapshots** stored at the time each transaction was completed.
3. **Calculated Clinic Share**: Net revenue allocated to the clinic (`gross - commission`).
4. **Historical Snapshot Integrity**: Historical commissions are never recalculated when platform default rates change.
5. **Settlement & Payout Disclaimer**:
   > [!IMPORTANT]
   > The "Calculated Clinic Share" displayed in reports represents accounting entitlement. Automated bank payouts and bank transfer integrations are not active on this platform. The interface explicitly communicates this to prevent confusing recorded entitlement with completed bank transfers.

---

## 7. API Reference

All clinic operational endpoints follow the `/api/v1/clinics/{clinic_id}/` structure:

### Dashboard
- `GET /api/v1/clinics/{clinic_id}/dashboard/summary/?period={period}&from_date={date}&to_date={date}`
- `GET /api/v1/clinics/{clinic_id}/dashboard/appointment-trends/?period={period}`
- `GET /api/v1/clinics/{clinic_id}/dashboard/financial-summary/?period={period}`

### Clinic Profile & Management
- `GET /api/v1/clinics/{clinic_id}/management/`
- `PATCH /api/v1/clinics/{clinic_id}/management/`

### Operational Closures
- `GET /api/v1/clinics/{clinic_id}/closures/`
- `POST /api/v1/clinics/{clinic_id}/closures/`
- `POST /api/v1/clinics/{clinic_id}/closures/preview/`
- `DELETE /api/v1/clinics/{clinic_id}/closures/{closure_id}/`

### Staff Management
- `GET /api/v1/clinics/{clinic_id}/staff/`
- `POST /api/v1/clinics/{clinic_id}/staff/`
- `PATCH /api/v1/clinics/{clinic_id}/staff/{staff_id}/`
- `DELETE /api/v1/clinics/{clinic_id}/staff/{staff_id}/`

### Clinic Appointments
- `GET /api/v1/clinics/{clinic_id}/appointments/`
- `GET /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/`
- `POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/confirm/`
- `POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/complete/`
- `POST /api/v1/clinics/{clinic_id}/appointments/{appointment_id}/no-show/`

### Calendar
- `GET /api/v1/clinics/{clinic_id}/calendar/?start_date={date}&end_date={date}&doctor_id={id}`

### Finance
- `GET /api/v1/clinics/{clinic_id}/finance/summary/?period={period}`
- `GET /api/v1/clinics/{clinic_id}/finance/payments/?status={status}&search={query}&page={page}`
