# EazyDoc SaaS Analytics Data Dictionary

This document provides a comprehensive data dictionary for the EazyDoc multi-tenant doctor booking SaaS platform. It defines every key business metric, operational KPI, financial formula, underlying model, database fields, aggregation method, tenant-isolation rules, and business interpretation.

---

## 1. Core Financial Principles & Accounting Invariants

EazyDoc enforces strict double-entry ledger style invariants across all transactional, commission, and reporting queries.

### Fundamental Accounting Invariant
```
gross_amount = commission_amount + clinic_share
```
- **Rounding Rule**: Standard Indian Financial Precision — Decimal arithmetic with `ROUND_HALF_UP` to two decimal places (`0.01`).
- **Historical Snapshot Rule**: All historical revenue and commission calculations **MUST** use the historical `commission_rate` frozen in `CommissionRecord.commission_rate` at transaction settlement time. Modifying the clinic's commission override or the platform default commission rate in `PlatformSetting` will never retroactively modify or recalculate historical revenue.
- **Payable vs. Disbursed Distinction**: `clinic_share` represents calculated internal platform payable liability owed to the clinic. It is **NOT** proof of automated bank settlement or payout. The platform currently tracks payable amounts; disbursement requires verified clinic bank accounts and manual or scheduled gateway settlements.

---

## 2. Metric Specifications

### A. User & Entity Metrics

| Metric Name | Source Model | Database Fields & Filter | Calculation / Aggregation | Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Total Registered Users** | `apps.accounts.models.User` | `is_active=True` (or total rows) | `COUNT(User.id)` | Total customer and staff accounts created across the entire SaaS platform. |
| **Total Patients** | `apps.accounts.models.User` | `role='patient'` | `COUNT(User.id WHERE role='patient')` | Total patient accounts registered to discover and book appointments. |
| **Total Doctors** | `apps.doctors.models.Doctor` | All doctor profiles | `COUNT(Doctor.id)` | Total medical practitioners registered on the platform. |
| **Verified Doctors** | `apps.doctors.models.Doctor` | `verification_status='verified'` | `COUNT(Doctor.id WHERE verification_status='verified')` | Licensed doctors who have passed credential and medical registration verification and can consult. |
| **Pending Doctors** | `apps.doctors.models.Doctor` | `verification_status='pending'` | `COUNT(Doctor.id WHERE verification_status='pending')` | Doctors awaiting administrator verification. |
| **Total Registered Clinics** | `apps.clinics.models.Clinic` | All clinic entities | `COUNT(Clinic.id)` | Total healthcare facilities registered on the platform. |
| **Approved Clinics** | `apps.clinics.models.Clinic` | `status='approved'` | `COUNT(Clinic.id WHERE status='approved')` | Clinics verified and approved by Super Admin. |
| **Active Clinics** | `apps.clinics.models.Clinic` | `status='approved', is_active=True` | `COUNT(Clinic.id WHERE status='approved' AND is_active=True)` | Operational clinics actively accepting appointments and managing staff. |

---

### B. Appointment Operational Metrics

| Metric Name | Source Model | Database Fields & Filter | Calculation / Aggregation | Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Total Appointments** | `apps.appointments.models.Appointment` | Scoped by tenant/date | `COUNT(Appointment.id)` | All appointment bookings within the selected timeframe. |
| **Completed Appointments** | `apps.appointments.models.Appointment` | `status='completed'` | `COUNT(Appointment.id WHERE status='completed')` | Consultations successfully conducted and closed. |
| **Confirmed Appointments** | `apps.appointments.models.Appointment` | `status='confirmed'` | `COUNT(Appointment.id WHERE status='confirmed')` | Paid and confirmed bookings awaiting consultation. |
| **Cancelled Appointments** | `apps.appointments.models.Appointment` | `status='cancelled'` | `COUNT(Appointment.id WHERE status='cancelled')` | Appointments cancelled by patient, doctor, or clinic. |
| **No-Show Appointments** | `apps.appointments.models.Appointment` | `status='no_show'` | `COUNT(Appointment.id WHERE status='no_show')` | Patients who failed to attend their scheduled consultation slot. |
| **Pending Appointments** | `apps.appointments.models.Appointment` | `status='pending'` | `COUNT(Appointment.id WHERE status='pending')` | Slot reservations awaiting payment completion or confirmation. |
| **Completion Rate (%)** | `apps.appointments.models.Appointment` | Resolved appointments | `(completed / total) * 100` | Percentage of total booked appointments that resulted in a completed consultation. |
| **Cancellation Rate (%)** | `apps.appointments.models.Appointment` | Total appointments | `(cancelled / total) * 100` | Percentage of bookings that were cancelled prior to consultation. |
| **Rescheduling Rate (%)** | `apps.appointments.models.Appointment` | `reschedule_required=True` or reschedule history | `(reschedule_required / total) * 100` | Proportion of appointments that experienced schedule changes or doctor unavailability. |

---

### C. Revenue & Financial Metrics

| Metric Name | Source Model | Database Fields & Filter | Calculation / Aggregation | Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Gross Revenue (Collected)** | `apps.payments.models.Payment` | `status='paid'` | `SUM(Payment.amount WHERE status='paid')` | Total payments collected from patients via Razorpay gateway. Payment initiation is **never** counted as revenue. |
| **Platform Commission Earned** | `apps.payments.models.CommissionRecord` | `status='recorded'` | `SUM(CommissionRecord.commission_amount)` | Net platform revenue retained by EazyDoc based on snapshot percentage at time of booking. |
| **Clinic Payable Amount** | `apps.payments.models.CommissionRecord` | `status='recorded'` | `SUM(CommissionRecord.clinic_share)` | Total earnings allocated to clinics after deducting platform commission. Represents accrued liability. |
| **Average Commission Rate (%)** | `apps.payments.models.CommissionRecord` | `status='recorded'` | `(SUM(commission_amount) / SUM(gross_amount)) * 100` | Effective platform commission realized across all settled bookings. Default is 5.00% unless overridden. |
| **Failed Payments Volume** | `apps.payments.models.Payment` | `status='failed'` | `SUM(Payment.amount WHERE status='failed')` | Monetary volume of payment attempts rejected by bank or gateway. |
| **Failed Payments Count** | `apps.payments.models.Payment` | `status='failed'` | `COUNT(Payment.id WHERE status='failed')` | Number of unsuccessful payment checkout attempts. |
| **Refund Volume** | `apps.payments.models.Payment` / `RefundRecord` | `status='refunded'` | `SUM(refund_amount)` | Value of funds returned to patients due to cancellation or dispute. |
| **Appointment-to-Payment Conversion Rate (%)** | Cross-model | `Appointment` & `Payment` | `(successful_payments / total_appointments) * 100` | Proportion of booked appointments successfully backed by settled funds. |

---

### D. Multi-Clinic Doctor Metrics

| Metric Name | Source Model | Database Fields & Filter | Calculation / Aggregation | Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Doctor Total Appointments** | `apps.appointments.models.Appointment` | `doctor_id=D, [clinic_id=C]` | `COUNT(Appointment.id)` | Volume of patients scheduled with the doctor. Filterable per clinic association or aggregate. |
| **Doctor Gross Revenue** | `apps.payments.models.Payment` | `appointment.doctor_id=D, status='paid'` | `SUM(Payment.amount)` | Total revenue generated by consultations with this doctor. |
| **Doctor Clinic Share** | `apps.payments.models.CommissionRecord` | `appointment.doctor_id=D, status='recorded'` | `SUM(CommissionRecord.clinic_share)` | Earnings generated for clinic operations by this doctor. |
| **Doctor Completion Rate (%)** | `apps.appointments.models.Appointment` | `doctor_id=D` | `(completed / total) * 100` | Reliability indicator measuring completed visits vs total booked. |
| **Average Daily Appointments** | `apps.appointments.models.Appointment` | Grouped by consultation date | `total_completed / distinct_practice_days` | Workload density metric showing typical consultations per active day. |
| **Consultation Fee Consistency** | `apps.clinics.models.DoctorClinic` | `doctor_id=D, clinic_id=C` | `DoctorClinic.consultation_fee` | Contracted fee for that specific clinic. Must not be averaged or merged across different clinics. |

---

## 3. Temporal Granularity & Timezone Normalization

- **Default Platform Timezone**: `Asia/Kolkata` (configured in Django `settings.TIME_ZONE`).
- **Clinic Timezone**: Each clinic entity maintains its own `timezone` string (e.g. `Asia/Kolkata`).
- **Date Boundary Conversion**:
  - All date-based filtering receives date parameters in local calendar format (`YYYY-MM-DD`).
  - Dates are converted to localized midnight boundaries:
    - `start_bound = local_tz.localize(datetime.combine(start_date, time.min))`
    - `end_bound = local_tz.localize(datetime.combine(end_date, time.max))`
  - Bounds are converted to UTC (`astimezone(pytz.UTC)`) before executing database queries on `DateTimeField` columns (`created_at`, `start_at`).

---

## 4. Preset Date Ranges

| Preset Code | Definition | Boundary Logic (Local Timezone) |
| :--- | :--- | :--- |
| `today` | Current calendar day | `today 00:00:00` to `today 23:59:59.999999` |
| `yesterday` | Previous calendar day | `(today - 1d) 00:00:00` to `(today - 1d) 23:59:59.999999` |
| `last_7_days` | Rolling last 7 days | `(today - 6d) 00:00:00` to `today 23:59:59.999999` |
| `last_30_days` | Rolling last 30 days | `(today - 29d) 00:00:00` to `today 23:59:59.999999` |
| `last_90_days` | Rolling last 90 days | `(today - 89d) 00:00:00` to `today 23:59:59.999999` |
| `this_month` | Month-to-date | `1st of current month 00:00:00` to `today 23:59:59.999999` |
| `previous_month` | Entire prior calendar month | `1st of prior month 00:00:00` to `last day of prior month 23:59:59.999999` |
| `this_year` | Year-to-date | `Jan 1 of current year 00:00:00` to `today 23:59:59.999999` |
| `custom` | User specified range | `date_from 00:00:00` to `date_to 23:59:59.999999` |

---

## 5. Tenant Isolation & Access Control Rules

1. **Super Admin**:
   - Access to platform-wide summaries, comparative clinic analytics, reconciliation ledger, and system operations.
   - Cache keys: `eazydoc:analytics:admin:<metric_type>:<hash_of_params>`.
2. **Clinic Owner & Authorized Staff**:
   - Strictly scoped to clinics owned by or staffed by the requesting user.
   - Queries **MUST** inject `clinic_id=<user_authorized_clinic_id>`.
   - Any query attempting to query another clinic's data returns `403 Forbidden`.
   - Multi-clinic owners can switch between their verified clinics using the clinic switcher.
   - Cache keys: `eazydoc:analytics:clinic:<clinic_id>:<metric_type>:<hash_of_params>`.
3. **Patients & Regular Doctors**:
   - Forbidden from accessing administrative and tenant-wide financial analytics endpoints.
