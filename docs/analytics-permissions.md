# EazyDoc Analytics Permissions & Multi-Tenant Isolation

This document outlines the role-based access control (RBAC) rules, tenant isolation guarantees, and security policies governing the EazyDoc Analytics and Reporting module.

---

## 1. Role-Based Access Control Matrix

| Endpoint / Capability | Super Admin | Clinic Owner | Clinic Staff | Doctor | Patient |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Admin Overview KPIs** (`/admin/analytics/overview/`) | Allowed | Denied (`403`) | Denied (`403`) | Denied (`403`) | Denied (`403`) |
| **Admin Revenue Analytics** (`/admin/analytics/revenue/`) | Allowed | Denied (`403`) | Denied (`403`) | Denied (`403`) | Denied (`403`) |
| **Admin Appointments** (`/admin/analytics/appointments/`) | Allowed | Denied (`403`) | Denied (`403`) | Denied (`403`) | Denied (`403`) |
| **Admin Clinic Performance** (`/admin/analytics/clinics/`) | Allowed | Denied (`403`) | Denied (`403`) | Denied (`403`) | Denied (`403`) |
| **Admin Doctor Practice** (`/admin/analytics/doctors/`) | Allowed | Denied (`403`) | Denied (`403`) | Denied (`403`) | Denied (`403`) |
| **Admin Financial Reconciliation** (`/admin/analytics/reconciliation/`) | Allowed | Denied (`403`) | Denied (`403`) | Denied (`403`) | Denied (`403`) |
| **Admin CSV Reports** (`/admin/analytics/reports/export/`) | Allowed | Denied (`403`) | Denied (`403`) | Denied (`403`) | Denied (`403`) |
| **Clinic Overview** (`/clinics/<id>/analytics/overview/`) | Allowed | Allowed (Owned) | Allowed (Affiliated) | Denied (`403`) | Denied (`403`) |
| **Clinic Revenue** (`/clinics/<id>/analytics/revenue/`) | Allowed | Allowed (Owned) | Allowed (Affiliated) | Denied (`403`) | Denied (`403`) |
| **Clinic Appointments** (`/clinics/<id>/analytics/appointments/`) | Allowed | Allowed (Owned) | Allowed (Affiliated) | Denied (`403`) | Denied (`403`) |
| **Clinic Doctors** (`/clinics/<id>/analytics/doctors/`) | Allowed | Allowed (Owned) | Allowed (Affiliated) | Denied (`403`) | Denied (`403`) |
| **Clinic CSV Export** (`/clinics/<id>/analytics/reports/export/`) | Allowed | Allowed (Owned) | Allowed (Affiliated) | Denied (`403`) | Denied (`403`) |

---

## 2. Multi-Tenant Isolation Enforcement

### A. Strict Tenant Scoping in ORM Queries
All clinic-scoped endpoints enforce tenant boundaries directly at the database query level:
```python
# Every query strictly filters by clinic
appt_qs = Appointment.objects.filter(clinic=clinic, ...)
comm_qs = CommissionRecord.objects.filter(clinic=clinic, ...)
pay_qs = Payment.objects.filter(clinic=clinic, ...)
```

### B. Ownership & Affiliation Verification
Before any analytics query executes, the request passes through `check_clinic_access`:
1. **Super Admin**: Automatically authorized across any clinic.
2. **Clinic Owner**: Validated against `clinic.owner_id == request.user.id`.
3. **Clinic Staff**: Validated against `request.user.staff_profile.clinic_id == clinic.id` and `is_active == True`.
4. **Foreign Tenant Rejection**: If Clinic Owner A attempts to query Clinic B's analytics by passing Clinic B's UUID in the URL, `PermissionDenied` is raised immediately, returning HTTP `403 Forbidden`.

### C. Redis Cache Key Tenant Separation
Cache keys strictly partition cached payloads by tenant scope:
```
# Admin scope
eazydoc:analytics:admin:revenue:<hash>

# Clinic scope
eazydoc:analytics:clinic:<clinic_id>:revenue:<hash>
```
This prevents cache poisoning or cross-tenant data leakage via shared cache keys.

---

## 3. Patient Privacy & Data Masking in Reports

To prevent patient identifiable information (PII) leakage in analytics exports:
1. Patient full names are masked in all CSV exports (e.g., `John Doe` -> `John D.`).
2. Phone numbers and email addresses of patients are strictly excluded from tabular exports.
3. Only authorized doctors and treating staff can view patient details in clinical record views.

