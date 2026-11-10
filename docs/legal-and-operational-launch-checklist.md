# EazyDoc — Legal, Compliance & Operational Launch Checklist

This document provides a comprehensive operational checklist for human stakeholders, legal counsel, and compliance officers prior to expanding the platform beyond the limited pilot phase.

> [!WARNING]
> **Legal Review Notice:**
> The items in this checklist require formal review and approval by qualified legal counsel licensed in the jurisdiction of operation (e.g., India DPDP Act 2023, Telemedicine Practice Guidelines, GDPR, or HIPAA). Do NOT open the platform to unrestricted public use without completing this review.

---

## 1. Legal Documentation & User Terms

- [ ] **Privacy Policy**:
  - [ ] Transparent declaration of what personal and sensitive health data is collected (name, email, phone, appointment history, consultation notes).
  - [ ] Clear disclosure that health data is segregated per clinic and never sold to third parties or used for ad targeting.
  - [ ] Cookie policy explaining `HttpOnly` security cookies and session management.
  - [ ] User rights: instructions on how users can request data export or account deactivation.
- [ ] **Patient Terms & Conditions**:
  - [ ] Agreement that EazyDoc is a technology facilitator connecting patients with registered clinics and doctors, not a direct healthcare provider.
  - [ ] Emergency medical disclaimer: explicit statement that EazyDoc must NOT be used for acute life-threatening medical emergencies.
  - [ ] Limitation of liability regarding clinical medical advice provided by affiliated doctors.
- [ ] **Clinic & Doctor Onboarding Agreement**:
  - [ ] Clinic representations: warranty that the clinic holds valid local clinical establishment licenses.
  - [ ] Doctor verification warranty: obligation for doctors to maintain valid medical council registration (e.g. State Medical Council / National Medical Commission in India).
  - [ ] Data processing addendum: defines the clinic as Data Fiduciary/Controller and EazyDoc as Data Processor.
- [ ] **Platform Commission & Settlement Terms**:
  - [ ] Explicit disclosure of platform commission rates (default 5.00% or clinic-negotiated rate).
  - [ ] Settlement cycle terms: terms governing when clinic payable balances are remitted to clinic bank accounts.
  - [ ] Deductions and dispute resolution terms for disputed appointments or refund reversals.
- [ ] **Cancellation & Refund Policy**:
  - [ ] Patient cancellation cutoff policy explicitly stated: cancellations allowed until 11:59:59 PM on the calendar day prior to the appointment in the clinic's local timezone.
  - [ ] Clear terms governing full refunds for doctor-initiated cancellations or clinic emergency closures.
  - [ ] Handling of no-shows: patient no-shows forfeit the consultation booking fee.

---

## 2. Regulatory & Healthcare Compliance

- [ ] **Digital Personal Data Protection (DPDP) Act 2023 (India)**:
  - [ ] Purpose limitation: data processed strictly for appointment booking and clinical care facilitation.
  - [ ] Notice and consent: explicit consent collected at patient registration and booking time.
  - [ ] Data retention schedule: medical records retained in compliance with local statutory retention requirements (e.g. 3 years minimum).
  - [ ] Grievance Redressal Officer appointed with contact details published on the website.
- [ ] **Medical Council Verification Compliance**:
  - [ ] Verification workflow verified: Super Admin must manually check medical registration certificates against official council registries before activating a doctor profile.
- [ ] **Prescription & Medical Records Privacy**:
  - [ ] Access control: prescriptions and clinical summaries accessible strictly to the treating doctor, affiliated clinic staff, and the patient.
  - [ ] Audit trail: all access to medical records logged immutably in `apps_audit_logs`.

---

## 3. Operational & Customer Support Readiness

- [ ] **Customer Support Contacts**:
  - [ ] Official support email (`support@eazydoc.com`) monitored with defined response SLA (< 4 hours for booking/payment issues).
  - [ ] Emergency escalation phone line established for clinic partners during active shift hours.
- [ ] **Dispute & Grievance Handling**:
  - [ ] Written procedure for handling patient billing discrepancies or duplicate payment disputes.
  - [ ] Escalation path between Razorpay support, platform finance, and clinic management.
- [ ] **Clinic Partner Onboarding Guide**:
  - [ ] Step-by-step PDF / web guide provided to pilot clinic administrators covering doctor invitations, schedule management, and appointment check-in.

---

## 4. Human Approval Sign-Off Block

| Role | Name | Signature / Approval Reference | Date |
| :--- | :--- | :--- | :--- |
| **Legal Counsel** | _______________________ | _______________________ | __________ |
| **Data Protection Officer (DPO)**| _______________________ | _______________________ | __________ |
| **Chief Medical / Clinical Lead**| _______________________ | _______________________ | __________ |
| **Product Launch Manager** | _______________________ | _______________________ | __________ |
