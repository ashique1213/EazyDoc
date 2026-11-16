# EazyDoc SaaS Analytics & Business Intelligence API Specification

This document provides the complete API specification for the SaaS Analytics and Business Intelligence module of EazyDoc.

---

## 1. Overview & Architecture

The Analytics API exposes real-time and cached business intelligence metrics for:
1. **Platform Super Administrators**: High-level platform KPIs, revenue recognition, multi-clinic doctor performance, clinic comparative analytics, financial reconciliation ledgers, and platform-wide CSV exports.
2. **Clinic Owners & Authorized Staff**: Tenant-isolated operational analytics, clinic earnings, doctor practice breakdowns, peak consultation hours, cancellation audits, and scoped CSV exports.

### Base URLs
- Super Admin: `/api/v1/admin/analytics/`
- Clinic Scoped: `/api/v1/clinics/<clinic_id>/analytics/`

### Authentication & Authorization
- **Header**: `Authorization: Bearer <JWT_ACCESS_TOKEN>` or HttpOnly Cookie `access_token`
- **Super Admin Endpoints**: Restricted to users with `role: SUPER_ADMIN`. Any other authenticated user receives `403 Forbidden`. Unauthenticated requests receive `401 Unauthorized`.
- **Clinic Scoped Endpoints**: Restricted to the clinic owner or active clinic staff with appropriate operational/financial permissions. Cross-tenant access attempts receive `403 Forbidden`.

### Caching Strategy
- **Layer**: Redis caching with SHA-256 parameter hashing.
- **Cache TTL**: Default 180 seconds (3 minutes).
- **Tenant-Isolated Keys**:
  - Admin: `eazydoc:analytics:admin:<metric_type>:<hash>`
  - Clinic: `eazydoc:analytics:clinic:<clinic_id>:<metric_type>:<hash>`
- **Cache Invalidation / Bypass**: Pass `?refresh=true` to force cache bypass and recomputation.

---

## 2. Common Query Parameters

All analytics endpoints accept standard date range filtering:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `period` | string | No | `last_30_days` | Preset timeframe. Values: `today`, `yesterday`, `last_7_days`, `last_30_days`, `last_90_days`, `this_month`, `previous_month`, `this_year`, `custom`. |
| `date_from` | string | No | `null` | Start date in `YYYY-MM-DD` (used when `period=custom`). |
| `date_to` | string | No | `null` | End date in `YYYY-MM-DD` (used when `period=custom`). |
| `clinic_id` | UUID | No | `null` | Filter platform-wide analytics by a specific clinic (Super Admin only). |
| `doctor_id` | UUID | No | `null` | Filter analytics by a specific doctor practitioner. |
| `refresh` | boolean | No | `false` | When `true`, bypasses Redis cache and re-aggregates live database data. |

---

## 3. Super Admin Endpoints

### 3.1 Overview KPIs
- **Endpoint**: `GET /api/v1/admin/analytics/overview/`
- **Permissions**: `IsSuperAdminOnly`
- **Description**: Returns overall system KPIs across users, clinics, practitioners, appointments, and finances.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "period": {
      "name": "last_30_days",
      "start_date": "2026-10-18",
      "end_date": "2026-11-16",
      "days_count": 30,
      "timezone": "Asia/Kolkata"
    },
    "users": {
      "total_users": 1540,
      "total_patients": 1420
    },
    "clinics": {
      "total": 45,
      "approved": 38,
      "active": 36,
      "pending": 5,
      "rejected": 2,
      "suspended": 0
    },
    "doctors": {
      "total": 120,
      "verified": 105,
      "pending": 10,
      "rejected": 3,
      "suspended": 2
    },
    "appointments": {
      "total": 3450,
      "completed": 2980,
      "confirmed": 240,
      "cancelled": 180,
      "no_show": 50,
      "pending": 0,
      "reschedule_required": 12,
      "today": 115,
      "upcoming": 210,
      "completion_rate": 86.38,
      "cancellation_rate": 5.22
    },
    "finance": {
      "gross_collected": "2450000.00",
      "platform_commission": "142500.00",
      "clinic_payable": "2307500.00",
      "failed_volume": "45000.00",
      "refund_volume": "12000.00",
      "successful_payments_count": 3220,
      "failed_payments_count": 48,
      "pending_payments_count": 12,
      "refunded_payments_count": 14,
      "conversion_rate": 93.33,
      "accounting_invariant_valid": true,
      "actual_payouts_disbursed": "0.00",
      "payout_notice": "Platform calculates accrued payable liability. Automated bank settlement module is currently off."
    }
  }
}
```

---

### 3.2 Revenue Analytics
- **Endpoint**: `GET /api/v1/admin/analytics/revenue/`
- **Permissions**: `IsSuperAdminOnly`
- **Description**: Returns daily and monthly revenue volume trends, payment status distribution, and clinic breakdown.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "totals": {
      "gross_revenue": "2450000.00",
      "platform_commission": "142500.00",
      "clinic_share": "2307500.00",
      "failed_volume": "45000.00",
      "refund_volume": "12000.00",
      "average_commission_rate": 5.82,
      "successful_payments_count": 3220,
      "failed_payments_count": 48,
      "pending_payments_count": 12,
      "refunded_payments_count": 14
    },
    "daily_trend": [
      {
        "date": "2026-11-15",
        "gross_revenue": "82500.00",
        "platform_commission": "4950.00",
        "clinic_share": "77550.00",
        "successful_payments": 110,
        "failed_payments": 2
      }
    ],
    "monthly_trend": [
      {
        "month": "2026-11",
        "gross_revenue": "1340000.00",
        "platform_commission": "78200.00",
        "clinic_share": "1261800.00",
        "successful_payments": 1750
      }
    ],
    "payment_status_distribution": [
      { "status": "PAID", "count": 3220, "percentage": 97.75 },
      { "status": "FAILED", "count": 48, "percentage": 1.46 },
      { "status": "PENDING", "count": 12, "percentage": 0.36 },
      { "status": "REFUNDED", "count": 14, "percentage": 0.43 }
    ],
    "clinic_revenue_breakdown": [
      {
        "clinic_id": "c1f2b3a4-...",
        "clinic_name": "Apollo Clinic Indiranagar",
        "gross_revenue": "450000.00",
        "platform_commission": "22500.00",
        "clinic_share": "427500.00",
        "settled_appointments": 540
      }
    ]
  }
}
```

---

### 3.3 Appointment Analytics
- **Endpoint**: `GET /api/v1/admin/analytics/appointments/`
- **Permissions**: `IsSuperAdminOnly`
- **Description**: Booking volume, completion & cancellation rates, peak days, and peak hours.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "totals": {
      "total_bookings": 3450,
      "completed": 2980,
      "confirmed": 240,
      "cancelled": 180,
      "no_show": 50,
      "pending": 0,
      "rescheduled": 12,
      "completion_rate": 86.38,
      "cancellation_rate": 5.22,
      "reschedule_rate": 0.35,
      "no_show_rate": 1.45
    },
    "status_distribution": [
      { "status": "COMPLETED", "count": 2980, "percentage": 86.38 },
      { "status": "CONFIRMED", "count": 240, "percentage": 6.96 },
      { "status": "CANCELLED", "count": 180, "percentage": 5.22 },
      { "status": "NO_SHOW", "count": 50, "percentage": 1.45 }
    ],
    "daily_trend": [
      {
        "date": "2026-11-15",
        "total": 125,
        "completed": 110,
        "confirmed": 10,
        "cancelled": 4,
        "no_show": 1
      }
    ],
    "peak_days": [
      { "day": "Monday", "day_index": 0, "count": 680, "percentage": 19.71 },
      { "day": "Saturday", "day_index": 5, "count": 720, "percentage": 20.87 }
    ],
    "peak_hours": [
      { "hour": 10, "label": "10:00 - 11:00", "count": 480, "percentage": 13.91 },
      { "hour": 17, "label": "17:00 - 18:00", "count": 540, "percentage": 15.65 }
    ]
  }
}
```

---

### 3.4 Clinic Performance Comparison
- **Endpoint**: `GET /api/v1/admin/analytics/clinics/`
- **Permissions**: `IsSuperAdminOnly`
- **Query Params**: `status`, `search`, standard date bounds
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": [
    {
      "clinic_id": "c1f2b3a4-...",
      "name": "Apollo Clinic Indiranagar",
      "slug": "apollo-clinic-indiranagar",
      "status": "APPROVED",
      "is_active": true,
      "city": "Bengaluru",
      "state": "Karnataka",
      "total_doctors": 12,
      "active_doctors": 10,
      "total_appointments": 540,
      "completed_appointments": 490,
      "cancelled_appointments": 35,
      "completion_rate": 90.74,
      "gross_volume": "450000.00",
      "platform_commission": "22500.00",
      "clinic_share": "427500.00",
      "avg_consultation_value": "833.33",
      "commission_rate_override": null
    }
  ]
}
```

---

### 3.5 Doctor Practice Performance
- **Endpoint**: `GET /api/v1/admin/analytics/doctors/`
- **Permissions**: `IsSuperAdminOnly`
- **Query Params**: `clinic_id`, `verification_status`, `search`
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": [
    {
      "doctor_id": "d98e7f6a-...",
      "name": "Dr. Gregory House",
      "email": "house@example.com",
      "specialization": "Diagnostic Medicine",
      "verification_status": "VERIFIED",
      "affiliations": [
        {
          "clinic_id": "c1f2b3a4-...",
          "clinic_name": "Apollo Clinic",
          "consultation_fee": "1000.00",
          "is_active": true
        },
        {
          "clinic_id": "c2b3a4d5-...",
          "clinic_name": "City Care",
          "consultation_fee": "600.00",
          "is_active": true
        }
      ],
      "total_appointments": 320,
      "completed_appointments": 305,
      "cancelled_appointments": 12,
      "completion_rate": 95.31,
      "avg_appointments_per_day": 12.8,
      "gross_revenue": "285000.00",
      "platform_commission": "17100.00",
      "clinic_share": "267900.00"
    }
  ]
}
```

---

### 3.6 Financial Reconciliation Ledger
- **Endpoint**: `GET /api/v1/admin/analytics/reconciliation/`
- **Permissions**: `IsSuperAdminOnly`
- **Description**: Cross-verifies database consistency between appointments, payments, and commission records.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "period": {
      "start_date": "2026-10-18",
      "end_date": "2026-11-16"
    },
    "health_status": "HEALTHY",
    "total_reconciled_transactions": 3220,
    "discrepancy_count": 0,
    "total_discrepancy_value": "0.00",
    "discrepancies": []
  }
}
```

---

### 3.7 Super Admin CSV Report Export
- **Endpoint**: `GET /api/v1/admin/analytics/reports/export/`
- **Permissions**: `IsSuperAdminOnly`
- **Query Params**:
  - `report_type`: `revenue` | `clinics` | `doctors` | `appointments` | `reconciliation`
  - `period`, `date_from`, `date_to`, `clinic_id`, `doctor_id`
- **Response `200 OK`**:
  - `Content-Type`: `text/csv; charset=utf-8`
  - `Content-Disposition`: `attachment; filename="eazydoc-admin-<report_type>-<date>.csv"`

---

## 4. Clinic Scoped Endpoints

### 4.1 Clinic Overview KPIs
- **Endpoint**: `GET /api/v1/clinics/<clinic_id>/analytics/overview/`
- **Permissions**: `HasClinicStaffOrOwnerPermission`
- **Response `200 OK`**: Returns scoped clinic stats (appointments, finances, active doctors).

### 4.2 Clinic Revenue Analytics
- **Endpoint**: `GET /api/v1/clinics/<clinic_id>/analytics/revenue/`
- **Permissions**: `HasClinicStaffOrOwnerPermission`
- **Response `200 OK`**: Daily clinic collections, commission deducted, and doctor revenue breakdown.

### 4.3 Clinic Appointment Analytics
- **Endpoint**: `GET /api/v1/clinics/<clinic_id>/analytics/appointments/`
- **Permissions**: `HasClinicStaffOrOwnerPermission`
- **Response `200 OK`**: Daily volume trends, hourly peak demand (in clinic local timezone), and cancellation reasons summary.

### 4.4 Clinic Doctor Performance
- **Endpoint**: `GET /api/v1/clinics/<clinic_id>/analytics/doctors/`
- **Permissions**: `HasClinicStaffOrOwnerPermission`
- **Response `200 OK`**: List of doctors practicing at this clinic, consultation fee snapshots, completed visits, and generated clinic share.

### 4.5 Clinic CSV Export
- **Endpoint**: `GET /api/v1/clinics/<clinic_id>/analytics/reports/export/`
- **Permissions**: `HasClinicStaffOrOwnerPermission`
- **Query Params**: `report_type`: `revenue` | `doctors` | `appointments` | `cancellations`
- **Response `200 OK`**: Streaming CSV file with masked patient PII.

