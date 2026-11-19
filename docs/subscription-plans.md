# SaaS Subscription Plans & Monetization Strategy

**Document Reference:** `docs/subscription-plans.md`  
**Status:** Active Production Specification  
**Author:** Senior SaaS Product Architect & Monetization Lead  
**Scope:** Configurable Tier Definitions, Pricing Structures, Resource Quotas, and Feature Matrices

---

## 1. Monetization Philosophy & Pricing Tiers

EazyDoc provides multi-tier SaaS subscriptions tailored for healthcare establishments ranging from solo medical practices to multi-specialty polyclinics and enterprise hospital chains.

### Core Pricing Principles
1. **Dynamic Database Management:** Plan pricing, doctor limits, and staff allowances are managed dynamically via the `SubscriptionPlan` model. No pricing or quota numbers are hardcoded into business logic or frontend code.
2. **Annual Discounting:** Annual billing plans offer an automatic ~17% cost savings (equivalent to 2 free months per year).
3. **Statutory Tax Clarity:** All displayed consumer plan pricing in India is inclusive of 18% GST with transparent line-item tax breakdowns on generated B2B tax invoices.
4. **Independent Clinic Facilities:** Subscriptions bind directly to the `Clinic` entity (`Clinic.id`). Multi-clinic owners select distinct tiers per facility according to individual operational scale.

---

## 2. Standard SaaS Plans Catalog

| Dimension | Free Community (`FREE`) | Starter Plan (`STARTER`) | Professional Suite (`PROFESSIONAL`) | Enterprise Hospital (`ENTERPRISE`) |
| :--- | :--- | :--- | :--- | :--- |
| **Plan Code (Monthly)** | `free-monthly` | `starter-monthly` | `professional-monthly` | `enterprise-monthly` |
| **Plan Code (Annual)** | `free-monthly` (Perpetual) | `starter-yearly` | `professional-yearly` | `enterprise-yearly` |
| **Monthly Pricing** | ₹0 / month | ₹1,499 / month | ₹3,999 / month | ₹9,999 / month |
| **Annual Pricing** | ₹0 / year | ₹14,990 / year | ₹39,990 / year | ₹99,990 / year |
| **Effective Annual Rate** | ₹0 / month | ₹1,249 / month | ₹3,332 / month | ₹8,332 / month |
| **Trial Duration** | 0 Days (Default tier) | 14 Days Free Trial | 14 Days Free Trial | 14 Days Free Trial |
| **Max Doctor Licenses** | 1 Doctor | 3 Doctors | 10 Doctors | Unlimited (`null`) |
| **Max Staff Seats** | 1 Staff Account | 3 Staff Accounts | 10 Staff Accounts | Unlimited (`null`) |
| **Monthly Bookings** | 50 Appointments / mo | 300 Appointments / mo | 1,500 Appointments / mo | Unlimited (`null`) |
| **Practice Dashboard** | Standard Overview | Standard Overview | Advanced Ledger & Trends | Custom Executive BI |
| **Export Formats** | None | CSV Only | CSV + Official PDF | CSV + PDF + Audit Stream |
| **Support SLA** | Community Forums | 24-Hour Email Support | 4-Hour Priority SLA | Dedicated Account Manager |

---

## 3. Machine-Readable Feature Flags

Feature flags are serialized into the `feature_flags` JSON column of `SubscriptionPlan` to govern declarative DRF permissions and UI component gates.

```json
{
  "advanced_analytics": true,
  "export_reports": true,
  "export_pdf": true,
  "priority_support": true,
  "custom_branding": false,
  "dedicated_account_manager": false,
  "unlimited_capacity": false
}
```

### Feature Flag Matrix

| Feature Flag Key | Free | Starter | Professional | Enterprise | Enforcing Class / Component |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `advanced_analytics` | ❌ | ✅ | ✅ | ✅ | `HasSubscriptionFeature("advanced_analytics")` |
| `export_reports` | ❌ | ✅ (CSV) | ✅ (CSV/PDF) | ✅ (All) | `ReportExportDialog.tsx` |
| `export_pdf` | ❌ | ❌ | ✅ | ✅ | `ReportExportDialog` PDF toggle |
| `priority_support` | ❌ | ❌ | ✅ | ✅ | Clinic Settings & Support Portal |
| `dedicated_account_manager` | ❌ | ❌ | ❌ | ✅ | Super Admin Support Dispatch |
| `unlimited_capacity` | ❌ | ❌ | ❌ | ✅ | Quota boundary checks (`effective_max_*`) |

---

## 4. Database Schema: `SubscriptionPlan`

```python
class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100, unique=True, db_index=True)
    tier = models.CharField(max_length=20, choices=SubscriptionTier.choices, db_index=True)
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    description = models.TextField(blank=True, default="")
    max_doctors = models.PositiveIntegerField(null=True, blank=True)
    max_staff = models.PositiveIntegerField(null=True, blank=True)
    max_appointments_per_month = models.PositiveIntegerField(null=True, blank=True)
    features = models.JSONField(default=list)
    feature_flags = models.JSONField(default=dict)
    trial_days = models.PositiveIntegerField(default=14)
    is_active = models.BooleanField(default=True, db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 5. Idempotent Plan Seeding Command

Plans are initialized and kept up-to-date in any staging or production environment via the Django management command:

```bash
python manage.py seed_subscription_plans
```

The command uses `SubscriptionPlan.objects.update_or_create(code=code, defaults=...)`, ensuring existing clinic foreign key associations are preserved while updating marketing copy, pricing, or feature flag definitions.

---

## 6. Super Admin Plan Management APIs

Super Admins can view, edit, activate, or deactivate subscription plans through dedicated REST endpoints:

- `GET /api/v1/admin/subscriptions/plans/`: List all plans including inactive or archived tiers.
- `POST /api/v1/admin/subscriptions/plans/`: Create a new custom or promotional tier.
- `PATCH /api/v1/admin/subscriptions/plans/{id}/`: Update pricing, doctor allowances, or display order.
- `DELETE /api/v1/admin/subscriptions/plans/{id}/`: Soft-deactivation (`is_active = False`) to protect historical clinic billing foreign keys.
