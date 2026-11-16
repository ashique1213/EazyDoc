# EazyDoc Financial Reconciliation & Anomaly Detection Guide

This document details the automated financial reconciliation engine, anomaly detection heuristics, discrepancy classification, investigation runbooks, and audit logging for the EazyDoc multi-tenant healthcare platform.

---

## 1. Reconciliation Architecture & Overview

The Financial Reconciliation engine continuously verifies the integrity of the transactional ledger by cross-referencing three primary data models:
1. `apps.appointments.models.Appointment`: Consultation schedules, statuses, and booking references.
2. `apps.payments.models.Payment`: Payment attempts, amounts, gateway signatures, and payment statuses.
3. `apps.payments.models.CommissionRecord`: Internal revenue split ledgers between the platform and clinic partners.

---

## 2. Automated Anomaly Detection Heuristics

The reconciliation service runs four primary automated anomaly detection checks:

### Heuristic 1: Missing Commission Record (`MISSING_COMMISSION_RECORD`)
- **Severity**: `CRITICAL`
- **Condition**: A `Payment` has `status = PAID`, but has no corresponding `CommissionRecord` attached.
- **Root Cause**: Webhook handler failed after updating `Payment` status but before executing `create_commission_record`, or an asynchronous Celery task failed midway.
- **Business Impact**: Platform fails to record commission earned; clinic payable share is not recognized.

### Heuristic 2: Ledger Math Invariant Mismatch (`COMMISSION_MATH_MISMATCH`)
- **Severity**: `CRITICAL`
- **Condition**: `abs(Payment.amount - (CommissionRecord.commission_amount + CommissionRecord.clinic_share)) > 0.01`
- **Root Cause**: Manual database edit, incorrect rounding logic, or corrupted transaction record.
- **Business Impact**: Double-entry ledger imbalance; discrepancies in accounting and tax filings.

### Heuristic 3: Unpaid Confirmed/Completed Appointment (`UNPAID_CONFIRMED_APPOINTMENT`)
- **Severity**: `WARNING`
- **Condition**: An `Appointment` is marked `CONFIRMED` or `COMPLETED`, but has no associated `Payment` with `status = PAID`.
- **Root Cause**: Manual administrative appointment status override, offline cash consultation recorded without proper payment entry, or failed payment webhook.
- **Business Impact**: Doctor provided consultation without settled payment verification.

### Heuristic 4: Duplicate Paid Records (`DUPLICATE_PAID_RECORDS`)
- **Severity**: `CRITICAL`
- **Condition**: Multiple distinct `Payment` records in `status = PAID` linked to the same single `Appointment`.
- **Root Cause**: Patient submitted multiple successful checkout orders for the same booking, or duplicate webhook delivery processing.
- **Business Impact**: Overcharging the patient; duplicate commission calculation.

---

## 3. Financial Reconciliation Ledger API

Super Administrators inspect reconciliation status using:
```http
GET /api/v1/admin/analytics/reconciliation/?period=last_30_days
```

### Health Status Signals
- `HEALTHY`: 0 discrepancies detected. All payments match appointments and satisfy accounting equations.
- `DISCREPANCIES_DETECTED`: 1 or more discrepancies identified. Each item provides:
  - `type`: Anomaly code.
  - `severity`: `CRITICAL` or `WARNING`.
  - `payment_id`: Transaction identifier.
  - `appointment_id`: Appointment identifier.
  - `clinic_name`: Healthcare facility affected.
  - `amount`: Discrepancy volume.
  - `description`: Detailed technical and business explanation.

---

## 4. Investigation Runbook

When a discrepancy is flagged:

1. **Locate Identifiers**: Copy `payment_id` or `appointment_id` from the reconciliation ledger.
2. **Review Payment Audit Logs**:
   Query `PaymentAuditLog` for the transaction:
   ```python
   PaymentAuditLog.objects.filter(payment_id=payment_id).order_by('created_at')
   ```
3. **Inspect Razorpay Webhook Logs**:
   Check `PaymentWebhookEvent` for unhandled or failed webhook payload deliveries:
   ```python
   PaymentWebhookEvent.objects.filter(gateway_order_id=order_id)
   ```
4. **Resolution Protocol**:
   - For `MISSING_COMMISSION_RECORD`: Trigger commission recalculation task using historical rate snapshot.
   - For `UNPAID_CONFIRMED_APPOINTMENT`: Contact clinic administrative staff to verify if consultation was conducted offline.
   - For `DUPLICATE_PAID_RECORDS`: Initiate Razorpay refund for the duplicate transaction, and mark payment as `REFUNDED`.

---

## 5. Audit Logging & Compliance

All reconciliation reviews and administrative resolutions are appended to the immutable `apps.audit_logs.models.AuditLog` model with actor IP, timestamp, and before/after state snapshots.
