# EazyDoc — Payment & Commission Production Checklist

This document details the payment gateway architecture, platform commission calculation rules, accounting distinctions, and human authorization safeguards for Razorpay production activation.

---

## 1. Razorpay Integration Architecture

EazyDoc integrates Razorpay Standard Checkout with server-side order generation and cryptographically signed webhook callbacks.

```
[Patient Browser]                [EazyDoc Backend API]              [Razorpay Gateway]
       |                                   |                                |
       | 1. Initiate Booking Payment ----> |                                |
       |                                   | 2. Create Order (Rupees) ----> |
       |                                   |    amount = fee * 100 paise    |
       |                                   | <--- Return order_id ----------|
       | <--- Return order_id & key_id --- |                                |
       |                                                                    |
       | 3. Complete Checkout (Card / UPI / NetBanking) ------------------> |
       | <--- Return razorpay_payment_id & razorpay_signature ------------- |
       |                                                                    |
       | 4. Confirm Payment (order_id, payment_id, signature) ------------> |
       |                                   | 5. Verify HMAC-SHA256          |
       |                                   | 6. Atomic DB Transaction:      |
       |                                   |    - Mark Payment PAID         |
       |                                   |    - Create CommissionRecord   |
       |                                   |    - Confirm Appointment       |
       | <--- Return 200 OK Confirmed ---- |                                |
       |                                                                    |
       |                                   | <--- Webhook: payment.captured |
       |                                   | 7. Deduplicate & Verify HMAC   |
       |                                   |    (Idempotent fallback)       |
```

---

## 2. Payment Security & Integrity Controls

| Security Control | Implementation | Verification Test |
| :--- | :--- | :--- |
| **Server-Side Order Amount** | Amount derived exclusively from trusted backend `Appointment.consultation_fee` | `test_payment_order_matches_fee` |
| **Client Signature Verification** | `hmac.new(key_secret, order_id + "\|" + payment_id, sha256)` | `test_tampered_signature_rejected` |
| **Webhook Signature Check** | Raw request bytes verified against `RAZORPAY_WEBHOOK_SECRET` | `test_webhook_signature_verification` |
| **Webhook Idempotency** | Event deduplication via `PaymentWebhookEvent.event_id` | `test_duplicate_webhook_ignored` |
| **Out-of-Order Safety** | Late `payment.failed` webhooks ignored if payment is already `PAID` | `test_out_of_order_webhook_ignored` |
| **Late Payment on Expired Slot** | Marked `PAID` with `reschedule_required=True`; avoids double-booking | `test_late_payment_on_expired_slot` |

---

## 3. Platform Commission & Accounting Invariants

### 3.1 Precedence Rules for Commission Rate
1. **Clinic Override**: If `Clinic.commission_rate` is set (e.g. `7.50%`), it takes precedence.
2. **Platform Default**: If no clinic override exists, the platform default rate (`5.00%`) is applied.

### 3.2 Accounting Invariant
$$\text{Gross Amount} = \text{Commission Amount} + \text{Clinic Share}$$

All monetary arithmetic is performed using Python's `Decimal` type with `ROUND_HALF_UP` to prevent floating-point rounding errors.

### 3.3 Concrete Calculation Example

- **Appointment Consultation Fee**: ₹500.00
- **Applicable Commission Rate**: 5.00%
- **Platform Commission (Retained)**: ₹25.00
- **Calculated Clinic Share**: ₹475.00
- **Patient Receipt Display**: Shows ₹500.00 total consultation fee. **Platform commission is an internal deduction and is NEVER displayed as an extra charge to the patient.**

---

## 4. Financial Status Definitions & Payout Boundaries

> [!IMPORTANT]
> **Strict Accounting Distinction**:
> The calculated `clinic_share` in `CommissionRecord` is an internal ledger allocation. It is **NOT** proof that the clinic has received a bank payout.

| Financial Term | Technical Definition | System State / Entity |
| :--- | :--- | :--- |
| **Payment Collected** | Gross patient funds successfully captured by Razorpay | `Payment.status = PAID` |
| **Platform Commission**| SaaS revenue retained by the platform for transaction facilitation | `CommissionRecord.commission_amount` |
| **Clinic Payable Balance**| Cumulative net earnings owed to a clinic from completed consultations | Sum of `CommissionRecord.clinic_share` where `status = PENDING_SETTLEMENT` |
| **Actual Payout** | Physical bank transfer of funds from platform bank account to clinic account | **Manual / External Banking Process** (Automated payouts are NOT claimed or enabled) |
| **Refund** | Patient payment reversed prior to service delivery | `Payment.status = REFUNDED` |
| **Refund Adjustment** | Reversal of platform commission and clinic payable balance on refund | `CommissionRecord.status = CANCELLED` |

---

## 5. Live Payment Activation Sign-Off Protocol

To prevent accidental financial transactions during staging, pilot testing, and internal verification:

1. **Current State:**
   - `RAZORPAY_KEY_ID`: `rzp_test_*`
   - Test mode is strictly enforced across all development and staging environments.
2. **Human Authorization Requirement:**
   - Switching to live keys (`rzp_live_*`) is **LOCKED** until written authorization is signed by the Product Launch Manager and Finance Director.
3. **Pre-Live Activation Checklist:**
   - [ ] All 322 automated tests passing.
   - [ ] Bank account linked and verified in Razorpay Production Dashboard.
   - [ ] Webhook URL registered in Razorpay Dashboard (`https://api.eazydoc.com/api/v1/payments/webhook/`).
   - [ ] Webhook events selected: `payment.captured`, `payment.failed`, `order.paid`.
   - [ ] Production webhook secret generated and securely populated in `.env.production`.
   - [ ] Two live test transactions (₹1.00) completed and successfully refunded to verify live credentials.
   - [ ] Written sign-off executed.

### Authorization Form:
- **Product Launch Manager Approval:** ___________________________ (Date: __________)
- **Finance Director Approval:** ___________________________ (Date: __________)

