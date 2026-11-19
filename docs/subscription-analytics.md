# SaaS Subscription Analytics & Monetization BI

**Document Reference:** `docs/subscription-analytics.md`  
**Status:** Active Production Specification  
**Author:** Senior SaaS Data Architect & BI Specialist  
**Scope:** MRR, ARR, Churn Rate Calculations, Plan Distribution, and Executive Dashboards

---

## 1. Executive SaaS KPI Metrics

The Super Admin console monitors the financial health and recurring revenue velocity of EazyDoc using standardized SaaS business intelligence metrics.

| Metric | Business Definition | Formula / Derivation | Target Benchmark |
| :--- | :--- | :--- | :--- |
| **MRR** | Monthly Recurring Revenue from all active, paid clinic subscriptions. | $\sum \text{Monthly Plans} + \sum \frac{\text{Yearly Plans}}{12}$ | High Month-over-Month growth |
| **ARR** | Annual Recurring Revenue normalized run-rate. | $\text{MRR} \times 12$ | Long-term valuation anchor |
| **Active Paid Clinics** | Facilities on Starter, Professional, or Enterprise paid tiers with status `ACTIVE`. | $\text{Count}(\text{ClinicSubscription}) \text{ where status=ACTIVE and tier}\ne\text{FREE}$ | High conversion from Free/Trial |
| **Trialing Clinics** | Facilities evaluating the platform during the 14-day evaluation window. | $\text{Count}(\text{ClinicSubscription}) \text{ where status=TRIALING}$ | Pipeline health indicator |
| **30-Day Churn Rate** | Percentage of paid facilities that cancelled or expired over the last 30 days. | $\frac{\text{Churned Paid (30d)}}{\text{Active Paid} + \text{Churned Paid (30d)}} \times 100$ | $< 3.0\%$ monthly churn |
| **Past Due Clinics** | Facilities in the 5-day grace period following a payment failure. | $\text{Count}(\text{ClinicSubscription}) \text{ where status=PAST\_DUE}$ | Actionable dunning pipeline |

---

## 2. Mathematical Calculation Rules

### 1. Monthly Recurring Revenue (MRR)
Free Community tier subscriptions (₹0) are excluded from MRR calculations. Subscriptions billed annually are normalized to their monthly contribution:

$$\text{MRR} = \sum_{s \in \text{Monthly}} \text{Price}_s + \sum_{s \in \text{Yearly}} \frac{\text{Price}_s}{12}$$

### 2. Annual Recurring Revenue (ARR)
$$\text{ARR} = \text{MRR} \times 12$$

### 3. Customer Churn Rate
$$\text{Churn Rate} = \left( \frac{\text{Cancelled or Expired Paid Subscriptions in last 30 days}}{\text{Active Paid Subscriptions} + \text{Cancelled/Expired in last 30 days}} \right) \times 100$$

---

## 3. Super Admin SaaS Metrics API

- **Endpoint:** `GET /api/v1/admin/subscriptions/metrics/`
- **Permission:** `SUPER_ADMIN` only

### Sample JSON Response
```json
{
  "success": true,
  "data": {
    "mrr": 89450.0,
    "arr": 1073400.0,
    "total_saas_revenue": 358200.0,
    "active_paid_subscriptions": 34,
    "trialing_subscriptions": 12,
    "past_due_subscriptions": 2,
    "cancelled_subscriptions": 3,
    "expired_subscriptions": 5,
    "total_clinics_enrolled": 56,
    "churn_rate_percentage": 2.78,
    "plan_distribution": [
      {
        "plan_id": "848a318e-4a6f-4cd2-b7e8-f71691234567",
        "plan_name": "Free Community",
        "tier": "FREE",
        "billing_interval": "MONTHLY",
        "price": 0.0,
        "active_clinics": 18
      },
      {
        "plan_id": "959b429f-5b7a-5de3-c8f9-a82702345678",
        "plan_name": "Starter Plan",
        "tier": "STARTER",
        "billing_interval": "MONTHLY",
        "price": 1499.0,
        "active_clinics": 20
      },
      {
        "plan_id": "a60c53a0-6c8b-6ef4-d90a-b93813456789",
        "plan_name": "Professional Suite",
        "tier": "PROFESSIONAL",
        "billing_interval": "MONTHLY",
        "price": 3999.0,
        "active_clinics": 12
      },
      {
        "plan_id": "b71d64b1-7d9c-7f05-ea1b-ca4924567890",
        "plan_name": "Enterprise Hospital",
        "tier": "ENTERPRISE",
        "billing_interval": "YEARLY",
        "price": 99990.0,
        "active_clinics": 2
      }
    ]
  }
}
```

---

## 4. Frontend Executive Dashboard Components

1. **KPI Stat Cards:** MRR, ARR, Active Paid Clinics, and 30-Day Churn Rate displayed with trends and contextual badges.
2. **Plan Distribution Table:** Active clinic adoption across tiers, comparing monthly vs annual uptake.
3. **Clinic Oversight Grid:** Searchable table of all clinic facilities with tier, license usage, period end dates, and administrative override controls.
4. **Audit Activity Stream:** Real-time stream of subscription events (upgrades, downgrades, past-due notices, cancellations, and overrides).
