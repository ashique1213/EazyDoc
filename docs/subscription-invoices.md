# SaaS Invoicing & Billing History Architecture

**Document Reference:** `docs/subscription-invoices.md`  
**Status:** Active Production Specification  
**Author:** SaaS Finance & Compliance Lead  
**Scope:** Sequential Numbering, Immutable Snapshots, Statutory GST Breakdown, and Printable Tax Invoices

---

## 1. Statutory Compliance & Immutable Snapshots

B2B SaaS subscription charges generate legally binding tax invoices adhering to statutory standards (e.g., Indian Goods and Services Tax / GST).

### Key Architectural Requirements
1. **Sequential Invoice Numbers:** Invoices follow the deterministic sequence: `INV-YYYYMM-XXXX` (e.g. `INV-202611-0001`). Gaps or duplicates are prevented via atomic database queries.
2. **Immutable Snapshotting:** If a clinic changes its name, address, or phone number next year, past invoices must remain unchanged. Clinic details and plan pricing are serialized into JSON columns (`billing_details`, `line_items`) at invoice generation time.
3. **Statutory Tax Transparency:** Digital SaaS in India is subject to standard 18.00% GST. The invoice explicitly itemizes taxable subtotal, applicable taxes (CGST 9% + SGST 9%), and total gross amount paid.

---

## 2. Database Schema: `SubscriptionInvoice`

```python
class SubscriptionInvoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    subscription = models.ForeignKey(ClinicSubscription, on_delete=models.CASCADE, related_name="invoices")
    clinic = models.ForeignKey("clinics.Clinic", on_delete=models.CASCADE, related_name="subscription_invoices")
    payment = models.OneToOneField(SubscriptionPayment, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice")
    plan_name = models.CharField(max_length=100)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("18.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.PAID)
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    line_items = models.JSONField(default=list)
    billing_details = models.JSONField(default=dict)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 3. GST Calculation Methodology

EazyDoc plan pricing is displayed to clinic owners inclusive of all taxes. For example, a ₹3,999.00 Professional Suite plan breaks down as:

$$\text{Taxable Subtotal} = \frac{\text{Total Amount}}{1 + \frac{\text{Tax Rate}}{100}} = \frac{3999.00}{1.18} = \text{₹3,388.98}$$

$$\text{Total GST (18\%)} = 3999.00 - 3388.98 = \text{₹610.02}$$

- **Intra-state (same state):** CGST (9%) = ₹305.01, SGST (9%) = ₹305.01
- **Inter-state:** IGST (18%) = ₹610.02

---

## 4. Invoice Snapshot Structure

```json
{
  "billing_details": {
    "clinic_name": "Apollo Polyclinic",
    "owner_name": "Dr. Rajesh Kumar",
    "owner_email": "rajesh@apollo.com",
    "phone": "9876543210",
    "address_line_1": "100 Medical Enclave",
    "address_line_2": "Suite 401",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
    "country": "India"
  },
  "line_items": [
    {
      "item_id": 1,
      "description": "EazyDoc SaaS Subscription: Professional Suite (Monthly)",
      "quantity": 1,
      "unit_price": "3388.98",
      "tax_rate_percent": "18.00",
      "tax_amount": "610.02",
      "total_amount": "3999.00"
    }
  ]
}
```

---

## 5. Printable HTML & PDF Generation

Invoices can be viewed directly in the browser or saved as PDF using the printable HTML endpoint:

- **Endpoint:** `GET /api/v1/subscriptions/clinics/{clinic_id}/invoices/{invoice_id}/html/`
- **Output:** Fully self-contained, responsive HTML with print-optimized CSS `@media print` styles and a "Print / Save PDF" trigger.
- **Frontend Action:** The Clinic Owner Billing History table provides a single-click "View / Print" button opening this view in a dedicated browser tab.
