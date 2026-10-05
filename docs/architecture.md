# EazyDoc — System Architecture & Technical Specification

## 1. High-Level System Architecture

EazyDoc is designed as a modular, service-oriented multi-tenant SaaS application. It isolates clinic operational boundaries while maintaining a global marketplace for doctors and patients.

```
                              ┌────────────────────────────────────────┐
                              │            Clients & Users             │
                              │  - Patients (Web / Mobile Browser)     │
                              │  - Doctors (Dashboard / Teleconsult)   │
                              │  - Clinic Owners & Staff (Admin SaaS)  │
                              │  - Super Admins (Platform Oversight)   │
                              └───────────────────┬────────────────────┘
                                                  │ HTTPS / WSS
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │     Nginx Reverse Proxy / Cloudflare   │
                              │   - SSL/TLS Termination, DDoS, WAF    │
                              │   - Static Asset Caching, Rate Limit   │
                              └───────┬────────────────────────┬───────┘
                                      │                        │
                     HTTP REST /api/v1│                        │ WebSockets /ws/
                                      ▼                        ▼
                   ┌──────────────────────────────┐ ┌───────────────────────────┐
                   │ Django 5+ Application Server │ │ Django Channels (Daphne)  │
                   │ (Gunicorn WSGI Workers)      │ │ (ASGI WebSocket Workers)  │
                   │ - Authentication & RBAC      │ │ - Real-Time Queue Updates │
                   │ - Domain Service Layer       │ │ - Live Slot Availability  │
                   │ - Multi-Tenant Mixins        │ │ - Doctor Calling Patient  │
                   │ - Payment Verification API   │ │                           │
                   └──────────────┬───────────────┘ └─────────────┬─────────────┘
                                  │                               │
            ┌─────────────────────┼───────────────────────┐       │
            │                     ▼                       ▼       ▼
            │       ┌───────────────────────────┐   ┌───────────────────────────┐
            │       │   PostgreSQL 16 Database  │   │  Redis 7 (In-Memory Data) │
            │       │ - Multi-Tenant Schemas/FK │   │ - Celery Task Broker      │
            │       │ - ACID Transactions       │   │ - Channel Layers (Pub/Sub)│
            │       │ - Row Locks (select_update│   │ - Slot Hold Tokens (TTL)  │
            │       │ - Exclusion/Unique Constr.│   │ - API Cache & Rate Limits │
            │       └───────────────────────────┘   └─────────────┬─────────────┘
            │                                                     │
            ▼                                                     ▼
┌───────────────────────────┐                       ┌───────────────────────────┐
│ Cloud Object Storage      │                       │ Celery Background Workers │
│ (AWS S3 / Cloudinary)     │                       │ - Email & SMS Dispatch    │
│ - Prescriptions (PDF)     │                       │ - Webhook Processing      │
│ - Doctor KYC & Clinic Docs│                       │ - Unavailability Fallout  │
│ - Pre-signed Secure URLs  │                       │ - Celery Beat Schedulers  │
└───────────────────────────┘                       └─────────────┬─────────────┘
                                                                  │
                                                                  ▼
                                                    ┌───────────────────────────┐
                                                    │ Third-Party Services      │
                                                    │ - Razorpay (Pay & Refund) │
                                                    │ - SendGrid / AWS SES (Mail│
                                                    │ - Twilio / Exotel (SMS)   │
                                                    └───────────────────────────┘
```

---

## 2. Frontend Architecture (React 19 + TypeScript + Vite)

### 2.1. Core Tech Stack
- **Framework:** React 19 with TypeScript in strict mode (`strict: true`, `noImplicitAny: true`).
- **Build Tool:** Vite with fast HMR and optimized production bundling (Rollup-based chunk splitting).
- **Styling & UI Kit:** Tailwind CSS with **shadcn/ui** (radix-ui primitives, accessible, fully themeable).
- **Routing:** React Router v6+ with code-splitting via `React.lazy()` and role-based route guards (`ProtectedRoute`, `ClinicTenantRoute`).
- **Server State & Caching:** **TanStack Query (React Query) v5** for declarative data fetching, automatic background revalidation, optimistic updates, and garbage collection.
- **Client State:** **Zustand** reserved strictly for client-only global state (e.g., active clinic tenant selector for multi-clinic doctors/owners, auth session tokens, notification tray state).
- **Forms & Validation:** `react-hook-form` with `zod` schema validation for full type safety across API boundaries.

### 2.2. Frontend Directory Structure & Organization
```
frontend/
├── src/
│   ├── assets/              # Static icons, logos, brand illustrations
│   ├── components/          # Reusable UI component library
│   │   ├── ui/              # shadcn/ui primitives (Button, Dialog, Card, Form...)
│   │   ├── common/          # SearchBar, DataTable, TimePicker, StatusBadge
│   │   └── layout/          # Navbar, Sidebar, Breadcrumb, TenantSwitcher
│   ├── features/            # Feature-sliced domain modules
│   │   ├── auth/            # Login, Register, ForgotPassword, DoctorKYC
│   │   ├── clinic/          # ClinicDashboard, Settings, StaffManagement
│   │   ├── doctor/          # DoctorProfile, DoctorClinicAssociation, Roster
│   │   ├── schedule/        # WeeklyScheduleEditor, SlotConfigurator, LeaveManager
│   │   ├── appointments/    # BookingFlow, SlotPicker, AppointmentHistory
│   │   ├── queue/           # LiveQueueBoard, PatientCheckInModal
│   │   ├── consultation/    # PrescriptionEditor, ClinicalNotes, VitalsForm
│   │   ├── payments/        # RazorpayCheckout, SettlementSummary, Invoices
│   │   └── admin/           # SuperAdminAudit, ClinicVerification, CommissionConfig
│   ├── hooks/               # Custom hooks (useAuth, useTenant, useWebSocket)
│   ├── lib/                 # Axios/Fetch client, TanStack Query setup, date utils
│   ├── routes/              # Route definitions and Guard wrappers
│   ├── stores/              # Zustand stores (useAuthStore, useTenantStore)
│   ├── types/               # TypeScript interface definitions mirroring backend models
│   └── App.tsx              # Root component with providers
```

### 2.3. Frontend State Isolation Principles
1. **Zero Domain Logic in Components:** Components only render UI and emit events to TanStack mutation hooks or service functions.
2. **Server Truth vs Local UI:** Server data lives in TanStack Query. Local UI state (modal open/closed, current step in wizard) lives in local component state (`useState`) or URL query params for linkability.
3. **Tenant Context Persistence:** When a Clinic Owner or Receptionist logs in, their current active clinic ID is stored in the `TenantContext`. All outgoing TanStack Query requests automatically attach the header `X-Clinic-ID: <uuid>` or query parameter to maintain tenant scoping.

---

## 3. Backend Architecture (Django 5+ & Django REST Framework)

### 3.1. Architectural Philosophy: The Service Layer Pattern
To avoid "fat models" and "fat views", EazyDoc strictly separates responsibilities into four layers:
1. **Model Layer (`models.py`):** Pure entity schemas, database constraints (`CheckConstraint`, `UniqueConstraint`), foreign keys, and low-level data invariants.
2. **Selector Layer (`selectors.py`):** Encapsulates complex ORM queries, multi-table joins, aggregations, and tenant filtering. Views and services never write raw ORM queries with ad-hoc business filters.
3. **Service Layer (`services.py`):** Pure business logic, cross-model transactions, external API calls, state transitions, locking (`select_for_update`), and event triggering. This keeps logic reusable across REST views, Celery tasks, and management commands.
4. **API / Serializer Layer (`views.py`, `serializers.py`):** Serializers validate incoming HTTP payloads and format outbound JSON. ViewSets authenticate, check permissions, invoke the appropriate service or selector, and return standard HTTP responses.

### 3.2. Multi-Tenant Backend Scoping
- **Tenant Identification:** Each clinic is a tenant with a primary UUID key.
- **Tenant Context Middleware:** Extracts the clinic context from the authenticated user:
  - If user is `CLINIC_OWNER` or `STAFF`, their assigned clinic is attached to `request.tenant_clinic`.
  - If a user owns multiple clinics, the `X-Clinic-ID` header determines the active context after validating ownership.
- **TenantQuerySetMixin:** Custom DRF QuerySet mixin automatically enforces `.filter(clinic=request.tenant_clinic)` on all clinic-scoped resources, preventing any accidental cross-tenant data leakage.

### 3.3. Project App Modularization
```
backend/
├── manage.py
├── config/                  # Django project root
│   ├── settings/
│   │   ├── base.py          # Shared settings
│   │   ├── local.py         # Local development configuration
│   │   └── production.py    # Production AWS/Docker configuration
│   ├── asgi.py              # Channels ASGI application router
│   ├── wsgi.py              # Gunicorn WSGI entrypoint
│   ├── urls.py              # Root URL router
│   └── celery.py            # Celery app initialization
├── apps/                    # Domain applications
│   ├── common/              # Base models, mixins, pagination, exceptions
│   ├── users/               # Custom User (AbstractBaseUser), auth, JWT, OTP
│   ├── clinics/             # Clinic, ClinicStaff, ClinicOperatingHours
│   ├── doctors/             # Doctor, Specialization, DoctorKYC
│   ├── doctor_clinics/      # DoctorClinic M2M, Fees, Invitations
│   ├── schedules/           # Schedule, DoctorUnavailability, BlockedSlot
│   ├── appointments/        # Appointment, Slot Reservation Engine, State Machine
│   ├── payments/            # Payment, PlatformCommission, Razorpay integration
│   ├── consultations/       # Consultation, Prescription, PrescriptionItem
│   ├── notifications/       # SMS, Email, In-app alerts, Celery workers
│   └── audit/               # AuditLog, Compliance tracking
```

---

## 4. Database Architecture (PostgreSQL 16)

### 4.1. Storage Engine & Integrity
- **Engine:** PostgreSQL 16 with B-Tree and GIST indexes for temporal overlap queries.
- **ACID Invariants:** Strict relational foreign keys with `ON_DELETE=PROTECT` on mission-critical financial and clinical records (Appointments, Payments, Prescriptions) to prevent accidental data loss.
- **UUID Primary Keys:** All primary keys utilize UUIDv4 to eliminate sequential enumeration attacks across clinics.
- **Timezone Awareness:** All timestamps stored in UTC (`TIMESTAMP WITH TIME ZONE`). Conversion to clinic-specific timezone (default: `Asia/Kolkata`) happens at the presentation/service layer.

### 4.2. Concurrency & Locking Strategy
- **Pessimistic Row Locking (`SELECT FOR UPDATE`):**
  When confirming a slot or executing a payment verification, the slot reservation record is locked within an atomic transaction (`transaction.atomic()`).
- **Postgres Exclusion Constraints (`btree_gist`):**
  Postgres exclusion constraints ensure that no two schedule shifts for the same doctor across any clinic can have overlapping time intervals on the same day of the week.

---

## 5. Caching, Session & Message Broker (Redis 7)

Redis serves four dedicated architectural functions:
1. **Celery Message Broker & Result Backend:** High-throughput queue for asynchronous and periodic background jobs (`redis://.../0`).
2. **Ephemeral Slot Reservation Holds:** Temporary 10-minute hold tokens (`slot_hold:<doctor_clinic_id>:<date>:<time>`) with automatic Redis key expiration (`EXPIRE 600`) (`redis://.../1`).
3. **Application & API Caching:** Cache for doctor profiles, clinic public details, and specialization taxonomies with cache invalidation signals on model updates (`redis://.../2`).
4. **Django Channels Layer:** Redis Pub/Sub backend for broadcasting real-time WebSocket events across horizontally scaled Daphne workers (`redis://.../3`).

---

## 6. Asynchronous Processing (Celery & Celery Beat)

### 6.1. Dedicated Queues
- `default`: General lightweight asynchronous tasks.
- `notifications`: Email, SMS, and WhatsApp message dispatches (retried with exponential backoff on vendor throttling).
- `payments`: Webhook processing, Razorpay refund dispatches, platform settlement calculations.
- `unavailability_fallout`: Heavy batch jobs analyzing and cancelling appointments when a doctor declares sudden sick leave.

### 6.2. Celery Beat Periodic Tasks
- **Expired Slot Sweep (Every 1 minute):** Cleans up stale `PENDING` appointments whose 10-minute payment window elapsed without a verified transaction.
- **Appointment Reminder Dispatch (Every 15 minutes):** Sends reminders 24 hours and 2 hours before scheduled consultation times.
- **Daily Clinic Settlement Reconciler (Daily at 02:00 UTC):** Aggregates completed appointments for the day, computes net clinic payouts after deducting platform commissions, and generates settlement batches.
- **No-Show Detection (Every 30 minutes):** Automatically transitions past unchecked-in appointments to `NO_SHOW`.

---

## 7. Real-Time Communication (Django Channels & WebSockets)

### 7.1. Routing & Channels Architecture
- **Protocol Router:** ASGI router delegates HTTP to Django and `ws://` traffic to Django Channels.
- **Authentication:** Custom JWT WebSocket Auth middleware reads token from the WebSocket connection query string or headers, validating user session before accepting the handshake.

### 7.2. WebSocket Event Streams
- `ws/clinics/<clinic_id>/queue/`: Real-time queue monitor for receptionists and doctors. When a patient is checked in or called, the display updates immediately without page refreshes.
- `ws/appointments/<appointment_id>/`: Real-time booking completion stream notifying the patient frontend as soon as a Razorpay webhook confirms payment.

---

## 8. Payment Gateway Integration (Razorpay)

### 8.1. End-to-End Secure Flow
1. **Order Creation:** Client requests an appointment. Service creates a database appointment in `PENDING` status, reserves the slot, and invokes Razorpay API to generate a `razorpay_order_id` for the exact `gross_amount`.
2. **Client Checkout:** Razorpay Standard Checkout modal opens on the patient's browser with the generated `order_id`.
3. **Verification Handshake:** Client submits `razorpay_payment_id`, `razorpay_order_id`, and `razorpay_signature` to the backend verification endpoint `/api/v1/payments/verify/`.
4. **Cryptographic Validation:** Backend computes HMAC-SHA256 of `order_id + "|" + payment_id` using the secret `RAZORPAY_KEY_SECRET`. If signature matches, appointment transitions to `CONFIRMED`.
5. **Asynchronous Webhook Redundancy:** A dedicated webhook endpoint `/api/v1/payments/webhook/` handles `payment.captured` and `payment.failed` events to guarantee state consistency even if the user closes their browser prematurely.

---

## 9. File & Document Storage (AWS S3 / Cloudinary)

### 9.1. Storage Classification
- **Public Assets:** Clinic exterior photos, doctor profile avatars (processed via Cloudinary or public S3 bucket with CDN).
- **Private & Sensitive Medical Documents:** Patient prescriptions, lab diagnostic uploads, and doctor medical council registration certificates stored in private AWS S3 buckets.
- **Access Control:** No private files are publicly accessible. The backend generates temporary time-limited pre-signed URLs (valid for 15 minutes) only after authenticating that the requesting patient or doctor has authorization to view the record.

---

## 10. Deployment & Infrastructure Architecture

```
                       ┌──────────────────────────────────────────────┐
                       │          GitHub Actions CI/CD Pipeline       │
                       │  - Code Quality: Flake8, Black, ESLint       │
                       │  - Automated Testing: Pytest, Vitest         │
                       │  - Docker Image Build & Push to AWS ECR      │
                       └──────────────────────┬───────────────────────┘
                                              │ Deploy Trigger
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AWS Cloud Infrastructure                                  │
│                                                                                             │
│  ┌───────────────────────┐         ┌─────────────────────────────────────────────────────┐  │
│  │ AWS Route 53 (DNS)    │         │ AWS Elastic Load Balancer (ALB)                     │  │
│  │ AWS Certificate (SSL) ├────────►│ - SSL Termination (HTTPS/WSS)                       │  │
│  └───────────────────────┘         │ - Path routing (/api -> WSGI, /ws -> ASGI)          │  │
│                                    └──────────┬───────────────────────┬──────────────────┘  │
│                                               │                       │                     │
│                                    ┌──────────▼────────┐   ┌──────────▼────────┐            │
│                                    │ ECS Tasks: Django │   │ ECS Tasks: Daphne │            │
│                                    │ (Gunicorn / API)  │   │ (WebSockets)      │            │
│                                    └──────────┬────────┘   └──────────┬────────┘            │
│                                               │                       │                     │
│  ┌────────────────────────────────────────┐   │                       │                     │
│  │ ECS Tasks: Celery Workers & Beat       ├───┼───────────────────────┤                     │
│  └────────────────────────────────────────┘   │                       │                     │
│                                               ▼                       ▼                     │
│                         ┌─────────────────────────────┐ ┌─────────────────────────────┐     │
│                         │ AWS RDS PostgreSQL 16       │ │ AWS ElastiCache Redis 7     │     │
│                         │ (Multi-AZ, Automated PITR)  │ │ (In-Memory Cluster)         │     │
│                         └─────────────────────────────┘ └─────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```
