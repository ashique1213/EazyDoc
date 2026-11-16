# EazyDoc SaaS Analytics & BI Automated Testing Strategy

This document describes the automated test suite, coverage verification, accounting invariant validation, multi-tenant isolation assertions, and testing commands for EazyDoc's Analytics and Business Intelligence module.

---

## 1. Test Suite Architecture

The analytics test suite is located at:
```
backend/tests/test_saas_analytics_and_bi.py
```

It contains 14 comprehensive test cases verifying:
1. Super Admin KPI calculations.
2. Double-entry accounting invariant: `gross_amount == commission_amount + clinic_share`.
3. Historical commission snapshot immutability.
4. Appointment analytics (completion, cancellation, peak days, peak hours).
5. Clinic comparative performance metrics.
6. Doctor practice analytics with multi-clinic affiliation fee tracking.
7. Automated financial reconciliation and discrepancy detection.
8. Super Admin CSV report exports.
9. RBAC permission denial for non-superadmin users (Patients, Clinic Owners, unauthenticated callers).
10. Clinic Owner scoped overview metrics.
11. Multi-tenant isolation (preventing cross-clinic analytics access).
12. Clinic Owner revenue analytics and doctor breakdown.
13. Clinic Doctor performance within the facility.
14. Clinic Owner CSV export with patient PII masking.

---

## 2. Key Test Implementations

### Accounting Invariant Verification Test
```python
def test_super_admin_revenue_accounting_invariant(self):
    self.client.force_authenticate(user=self.super_admin)
    res = self.client.get("/api/v1/admin/analytics/revenue/?period=last_30_days")
    self.assertEqual(res.status_code, status.HTTP_200_OK)
    totals = res.json()["data"]["totals"]

    gross = Decimal(totals["gross_revenue"])
    commission = Decimal(totals["platform_commission"])
    clinic_share = Decimal(totals["clinic_share"])

    # Enforce strict equality: gross == commission + clinic_share
    self.assertEqual(gross, commission + clinic_share)
```

### Historical Rate Snapshot Immutability Test
```python
def test_historical_commission_snapshot_immutability(self):
    # Alter Clinic A's override from 10% to 20%
    self.clinic_a.commission_rate = Decimal("20.00")
    self.clinic_a.save()

    # Alter global platform setting from 5% to 15%
    PlatformSetting.objects.update_or_create(
        key="default_commission_rate",
        defaults={"value": "15.00"}
    )

    self.client.force_authenticate(user=self.super_admin)
    res = self.client.get("/api/v1/admin/analytics/revenue/?period=last_30_days")
    totals = res.json()["data"]["totals"]

    # Historical settlement figures must remain completely unchanged
    self.assertEqual(totals["platform_commission"], "125.00")
    self.assertEqual(totals["clinic_share"], "1375.00")
```

### Multi-Tenant Isolation Test
```python
def test_clinic_owner_multi_tenant_isolation(self):
    # Owner of Clinic A attempts to access Clinic B's analytics
    self.client.force_authenticate(user=self.owner_a)
    res = self.client.get(f"/api/v1/clinics/{self.clinic_b.id}/analytics/overview/")
    self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
```

---

## 3. Test Execution Commands

### Run Analytics & BI Test Suite
```bash
cd backend
python manage.py test tests.test_saas_analytics_and_bi
```
*Expected Result*: `Ran 14 tests in ~0.35s - OK`

### Run Complete Platform Backend Test Suite
```bash
cd backend
python manage.py test
```
*Expected Result*: `Ran 336 tests in ~5.8s - OK`

### Verify Frontend Production Build
```bash
cd frontend
npm run build
```
*Expected Result*: `tsc -b && vite build` succeeds with `0` errors.
