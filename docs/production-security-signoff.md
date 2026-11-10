# EazyDoc — Production Security Audit & Sign-Off

This document records the results of the comprehensive security review conducted across authentication, authorization, multi-tenant isolation, payment processing, infrastructure, and logging for the EazyDoc platform.

> [!CAUTION]
> **Regulatory Disclaimer:** This document does NOT constitute third-party security certification (such as SOC 2 Type II or ISO 27001). It represents an internal engineering and architecture security assessment based on actual automated tests and code reviews.

---

## 1. Security Verification Matrix

| Security Domain | Verification Status | Enforcement Layer | Test Coverage Reference |
| :--- | :---: | :--- | :--- |
| **Authentication & Password Security** | **VERIFIED** | Django Auth / Argon2 / PBKDF2 | `apps.accounts.tests` |
| **JWT Lifecycle & Rotation** | **VERIFIED** | SimpleJWT + Blacklist | `apps.accounts.tests` |
| **Brute-Force & Rate Limiting** | **VERIFIED** | DRF Throttles (`AnonRateThrottle`) | `apps.accounts.views` |
| **Role-Based Authorization (RBAC)**| **VERIFIED** | DRF Permission Classes | `apps.accounts.permissions` |
| **Multi-Tenant Data Isolation** | **VERIFIED** | Queryset Scoping + Object Permissions | `tests.test_multi_tenant_isolation` |
| **Pessimistic Concurrency Locking**| **VERIFIED** | PostgreSQL `select_for_update` | `tests.test_concurrency_and_scheduling` |
| **Payment Signature Verification** | **VERIFIED** | HMAC-SHA256 (`compare_digest`) | `tests.test_payment_integrity_edge_cases` |
| **Webhook Idempotency & Replay** | **VERIFIED** | Event Deduplication Table | `tests.test_payment_integrity_edge_cases` |
| **Infrastructure & Network Security**| **VERIFIED** | Docker Compose Internal Networks | `docker-compose.prod.yml` |
| **Sensitive Data Logging Scrubber** | **VERIFIED** | Custom Formatter + Filters | `tests.test_monitoring_and_logging` |
| **Dependency Supply-Chain Audit** | **VERIFIED** | npm audit / pip check | CI Workflow (`.github/workflows/ci.yml`) |

---

## 2. Authentication Security Audit

### 2.1 Password Hashing & Storage
- **Algorithm:** PBKDF2 with SHA-256 (600,000 iterations default) or Argon2.
- **Salt:** Cryptographic 128-bit random salt per user.
- **Storage:** Plaintext passwords never stored in database, logs, or cache.

### 2.2 JWT Token Lifecycle & Revocation
- **Access Token:** 15-minute expiration (`JWT_ACCESS_LIFETIME_MINUTES = 15`), stored in-memory by frontend client (never in `localStorage` or `sessionStorage`).
- **Refresh Token:** 7-day expiration (`JWT_REFRESH_LIFETIME_DAYS = 7`), transmitted via secure `HttpOnly` cookie.
- **Rotation & Blacklist:** Consuming a refresh token automatically issues a new access/refresh pair and moves the consumed token to the blacklist table (`token_blacklist_outstandingtoken`). Subsequent attempts to reuse the consumed token return HTTP 400/401.

### 2.3 Account Enumeration & Brute-Force Protections
- **Password Reset:** `POST /api/v1/auth/forgot-password/` returns an identical success response whether the submitted email address exists in the system or not.
- **Login Rate Limiting:** IP and user throttles restrict repeated failed attempts, mitigating credential stuffing attacks.

---

## 3. Authorization & RBAC Enforcement

The platform enforces five distinct security roles across the backend API:

```
[SUPER_ADMIN]   --> Full SaaS governance, clinic approval, doctor verification, audit logs
      |
[CLINIC_OWNER]  --> Scoped strictly to owned clinic(s), staff management, doctor invitations
      |
   [STAFF]      --> Scoped to assigned clinic, granular permissions (VIEW/MANAGE appointments)
      |
   [DOCTOR]     --> Manages personal availability, medical council registration, appointments
      |
  [PATIENT]     --> Books appointments, views personal medical records and payments
```

### 3.1 Backend vs Frontend Security
- Frontend route guards (e.g. `ProtectedRoute`) provide UI convenience only.
- Every API view independently verifies `request.user.is_authenticated`, `request.user.role`, and object-level clinic affiliations.

---

## 4. Multi-Tenant Data Isolation Audit

Automated security tests in `tests/test_multi_tenant_isolation.py` confirm:
1. **Clinic A vs Clinic B**: Clinic A owner attempting to read Clinic B's appointment list or financial records receives HTTP 403 Forbidden.
2. **Staff Isolation**: Staff members assigned to Clinic A cannot query appointments or patient rosters for Clinic B.
3. **Doctor Scope**: A doctor practicing at both Clinic A and Clinic B cannot view Clinic A patients while logged into a Clinic B context, preserving strict clinic confidentiality.
4. **Patient Privacy**: Patient records and appointment histories are strictly scoped to `patient=request.user`. Attempting to retrieve another patient's booking reference returns HTTP 404 or 403.
5. **Super Admin Isolation**: Clinic owners attempting to access Super Admin operations or approval views receive HTTP 403.

---

## 5. Infrastructure & Operational Security

1. **`DEBUG = False`**: Enforced in `config/settings/production.py`.
2. **HTTPS & Security Headers**:
   - `SECURE_SSL_REDIRECT = True`
   - `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `JWT_AUTH_COOKIE_SECURE = True`
   - `SECURE_HSTS_SECONDS = 31536000` (1 Year) with `includeSubDomains` and `preload`
   - `X-Frame-Options: DENY` (Clickjacking protection)
   - `X-Content-Type-Options: nosniff` (MIME sniffing prevention)
3. **Database & Cache Network Isolation**:
   - PostgreSQL (`db:5432`) and Redis (`redis:6379`) do NOT expose ports to the public host interface.
   - Accessible only by containers attached to the internal Docker bridge network (`internal_network`).
4. **Unprivileged Container Execution**:
   - Backend container runs as non-root user `appuser` (UID 1000).
5. **Sensitive Data Redaction**:
   - Passwords, authorization headers, JWT tokens, Razorpay secrets, CVVs, PANs, and medical notes are masked by `redact_sensitive_data` and Sentry `before_send` hooks before log output or telemetry transmission.

---

## 6. Residual Security Risks & Mitigations

| Identified Risk | Severity | Mitigation In Place | Production Recommendation |
| :--- | :---: | :--- | :--- |
| **DDoS / High-Volume Flood** | Medium | Nginx rate limiting (`limit_req_zone`) | Place Cloudflare or AWS CloudFront WAF in front of Nginx. |
| **Third-Party Secret Exposure**| Low | Secrets strictly injected via env vars | Use AWS Secrets Manager or HashiCorp Vault for production keys. |
| **Live Payment Activation** | High | Razorpay kept in test mode | Require explicit written authorization before entering live keys. |
| **Clinical PHI Data Protection**| Medium | Field-level redaction in logs | Enable PostgreSQL transparent data encryption (TDE) / encrypted EBS. |

---

## 7. Security Sign-Off Decision

**Security Engineer Sign-Off:** **`APPROVED FOR CONTROLLED PILOT`**  
The technical security controls, tenant boundaries, authentication defenses, and log sanitization mechanisms satisfy all requirements for pilot launch. Live payment keys and public DNS expansion remain gated behind administrative signoff.

