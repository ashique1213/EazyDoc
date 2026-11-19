# SaaS Entitlement Enforcement & Quota Architecture

**Document Reference:** `docs/subscription-entitlements.md`  
**Status:** Active Production Specification  
**Author:** Senior Security Architect & Backend Lead  
**Scope:** Declarative Quotas, License Seat Boundaries, Non-Destructive Enforcement, and Feature Flags

---

## 1. Principles of Entitlement Enforcement

EazyDoc enforces platform resource limits and feature access through a centralized service: `EntitlementService` (`apps.subscriptions.services.entitlements`).

### The Golden Rule: Non-Destructive Enforcement
> [!IMPORTANT]
> **Zero Data Destruction:** When a clinic downgrades, expires, or cancels, the platform **NEVER** deletes existing doctors, staff accounts, past appointments, medical records, or consultation notes.

Instead, the platform enforces **Creation and Association Boundaries**:
- Existing resources remain accessible for historical consultation and reporting.
- Creating or inviting *new* resources beyond plan limits is blocked with HTTP 403 Forbidden (`PLAN_LIMIT_EXCEEDED`).

---

## 2. Resource Limits & Quota Counting Logic

### 1. Doctor License Quotas (`can_add_doctor`)
- **Definition:** The number of medical practitioners affiliated with the clinic facility.
- **Counting Rule:** Counts records in `DoctorClinic` where status is `ACTIVE` or `INVITED`.
  ```python
  DoctorClinic.objects.filter(
      clinic=clinic,
      status__in=[DoctorClinicStatus.ACTIVE, DoctorClinicStatus.INVITED],
  ).count()
  ```
- **Exclusions:** Doctors whose association status is `REMOVED` or `REJECTED` do **not** consume license seats.
- **Enforcement Point:** `DoctorClinicInviteView.post` in `apps.clinics.views`.

### 2. Clinic Staff Seat Quotas (`can_add_staff`)
- **Definition:** Delegated administrative staff accounts linked to the clinic.
- **Counting Rule:** Counts records in `ClinicStaff` where `is_active = True`.
- **Enforcement Point:** `ClinicStaffListCreateView.post` in `apps.clinics.staff_views`.

### 3. Monthly Appointment Limits (`can_book_appointment`)
- **Definition:** Total patient appointments booked across all affiliated doctors in the current calendar month.
- **Counting Rule:** Counts `Appointment` records where `clinic = clinic` and `created_at` falls in the current month.
- **Enforcement Point:** Appointment booking creation service in `apps.appointments`.

---

## 3. Administrative Overrides

A Super Admin can grant custom license overrides to specific clinics (e.g. for enterprise pilot agreements, institutional discounts, or grandfathered facilities):

- `custom_doctor_limit`: Overrides `plan.max_doctors`.
- `custom_staff_limit`: Overrides `plan.max_staff`.

```python
@property
def effective_max_doctors(self) -> int | None:
    if self.custom_doctor_limit is not None:
        return self.custom_doctor_limit
    return self.plan.max_doctors
```

---

## 4. Reusable DRF Permission Classes

Backend views declare subscription feature dependencies using `HasSubscriptionFeature`:

```python
from apps.subscriptions.permissions import HasSubscriptionFeature

class FinancialLedgerExportView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasSubscriptionFeature]
    required_subscription_feature = "export_reports"

    def get(self, request, clinic_id):
        # Generates export
```

If the clinic's plan does not include `"export_reports"`, the request is rejected immediately:

```json
{
  "detail": "Your subscription plan does not include the 'export_reports' capability. Please upgrade your plan to unlock this feature."
}
```

---

## 5. Entitlement Summary API Response

`GET /api/v1/subscriptions/clinics/{clinic_id}/`

```json
{
  "success": true,
  "data": {
    "clinic_id": "928d48bd-df24-433e-9994-9e2cd41533bd",
    "clinic_name": "Apollo Polyclinic",
    "subscription": {
      "id": "e44b82d1-55bb-411a-8219-c119280a82b4",
      "status": "ACTIVE",
      "tier": "STARTER",
      "plan_name": "Starter Plan",
      "plan_code": "starter-monthly",
      "price": 1499.0,
      "billing_interval": "MONTHLY",
      "current_period_start": "2026-11-19T07:30:00Z",
      "current_period_end": "2026-12-19T07:30:00Z",
      "is_in_trial": false,
      "days_remaining": 30,
      "cancel_at_period_end": false
    },
    "doctors": {
      "current": 2,
      "limit": 3,
      "is_unlimited": false,
      "percentage": 66,
      "can_add": true,
      "restriction_message": ""
    },
    "staff": {
      "current": 1,
      "limit": 3,
      "is_unlimited": false,
      "percentage": 33,
      "can_add": true,
      "restriction_message": ""
    },
    "appointments": {
      "current_monthly": 42,
      "limit": 300,
      "is_unlimited": false,
      "percentage": 14,
      "can_book": true,
      "restriction_message": ""
    },
    "feature_flags": {
      "advanced_analytics": true,
      "export_reports": true,
      "export_pdf": false
    }
  }
}
```
