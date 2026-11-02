# EazyDoc — Multi-Tenant Doctor Booking & Clinic Management SaaS

A production-ready, multi-tenant healthcare SaaS platform connecting Patients, Verified Doctors, and Multi-Clinic Practices with strict tenant data isolation, real-time queue management, cross-clinic schedule conflict detection, concurrency-safe appointment booking, Razorpay payment processing, automated notifications, and robust staging/production deployment topologies.

---

## 1. Technology Stack

### Backend
- **Framework:** Python 3.13+, Django 5.1+, Django REST Framework 3.15+
- **Database:** PostgreSQL 16 (Relational integrity, B-tree & GiST indexes, `select_for_update` row locks)
- **Cache & Message Broker:** Redis 7 (Celery broker, ephemeral slot reservation holds, Django Channels layer)
- **Background Jobs:** Celery 5.5+ & Celery Beat (Scheduled reminders, refund sweeps, notification dispatches)
- **WebSockets / Real-Time:** Django Channels 4.2+ & Daphne ASGI server
- **Authentication:** SimpleJWT (Dual-token JWT, rotating refresh tokens, token blacklisting)
- **API Documentation:** `drf-spectacular` (OpenAPI 3.0 / Swagger UI / ReDoc)
- **Payment Gateway:** Razorpay SDK (Server-side order creation, HMAC-SHA256 webhook verification)
- **Monitoring & Safety:** Sentry SDK integration, live payment key rejection guards in non-prod

### Frontend
- **Framework:** React 19, TypeScript (Strict Mode)
- **Build Tool:** Vite 6
- **UI & Styling:** Tailwind CSS 3.4+, shadcn/ui design tokens
- **Routing:** React Router v7
- **Server State & Data Fetching:** TanStack Query (React Query) v5
- **HTTP Client:** Axios (Configured with auth interceptors, auto-refresh tokens, and relative base paths)
- **Icons:** Lucide React

### Infrastructure & DevOps
- **Containerization:** Docker & Docker Compose (Separate Development, Staging, and Production topologies)
- **Reverse Proxy:** Nginx (HTTP/80 redirect, HTTPS/443 SSL termination, WebSocket upgrade headers, SPA routing)
- **CI/CD:** GitHub Actions (Automated linting, type checks, unit/integration/E2E test runs, and staging deployment)
- **Object Storage:** AWS S3 / MinIO (Private buckets with 15-minute temporary pre-signed URLs)

---

## 2. Architecture & Monorepo Structure

```text
EazyDoc/
├── backend/
│   ├── config/                     # Project configuration (ASGI, WSGI, Celery, URLs)
│   │   └── settings/               # Modular settings (base, development, staging, production)
│   ├── apps/                       # Domain-driven Django applications
│   │   ├── accounts/               # Custom User model (roles, UUID, JWT authentication)
│   │   ├── clinics/                # Multi-tenant clinic management, staff & verification
│   │   ├── doctors/                # Doctor profiles, qualifications, and medical registration
│   │   ├── patients/               # Patient records, medical history, emergency contacts
│   │   ├── appointments/           # Booking engine, concurrency locks, cancellation policies
│   │   ├── schedules/              # Recurring shifts, buffer times, cross-clinic conflict engine
│   │   ├── consultations/          # Clinical notes, vitals, diagnosis records
│   │   ├── prescriptions/          # Digital prescriptions & pharmacy items
│   │   ├── payments/               # Razorpay orders, HMAC webhooks, platform commission ledger
│   │   ├── notifications/          # In-app, SMS, and email notification dispatches
│   │   ├── documents/              # Secure medical document uploads and pre-signed S3 URLs
│   │   ├── reviews/                # Patient reviews & clinic/doctor moderation
│   │   ├── analytics/              # Daily metric aggregations & reporting
│   │   └── audit_logs/             # Immutable audit trail logging
│   ├── tests/                      # Comprehensive test suites (311 tests, E2E verification)
│   ├── requirements/               # base.txt, development.txt, production.txt
│   ├── Dockerfile                  # Development Dockerfile
│   ├── Dockerfile.prod             # Hardened multi-stage production/staging Dockerfile
│   ├── entrypoint.sh               # Container startup script (db wait, migrations, static collection)
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── app/                    # Global context providers and state
│   │   ├── components/             # Reusable UI & shadcn/ui components
│   │   ├── features/               # Feature-sliced modules (auth, clinics, doctors, appointments, etc.)
│   │   ├── layouts/                # PublicLayout, AuthLayout, DashboardLayout
│   │   ├── pages/                  # Route views (landing, portals, booking flow, settings)
│   │   ├── routes/                 # React Router v7 configuration & protected route guards
│   │   ├── services/               # Axios API client with relative routing (api.ts)
│   │   ├── types/                  # TypeScript domain models and API contracts
│   │   └── index.css               # Tailwind CSS & design tokens
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── Dockerfile                  # Frontend container configuration
│   └── .env.staging.example        # Frontend staging environment template
├── docker/
│   ├── nginx/
│   │   ├── nginx.conf              # Production Nginx reverse proxy configuration
│   │   └── nginx.staging.conf      # Staging Nginx reverse proxy (HTTP & HTTPS SSL)
│   └── entrypoint.sh               # Base entrypoint script
├── scripts/                        # Operational and maintenance automation
│   ├── generate_staging_certs.py   # Cross-platform X.509 self-signed SSL cert generator
│   ├── staging_health_check.py     # Automated staging health probe (API, DB, Redis)
│   ├── backup_db.sh / .ps1         # Automated PostgreSQL backup with SHA-256 checksums
│   └── restore_db.sh / .ps1        # Point-in-time PostgreSQL database restoration
├── docs/                           # Architectural specs, runbooks, and audit reports
├── .github/workflows/ci.yml        # CI test matrix & automated staging deployment
├── docker-compose.yml              # Local development multi-container orchestration
├── docker-compose.staging.yml      # Isolated staging topology with Nginx SSL proxy
├── docker-compose.prod.yml         # Production multi-container topology
├── .env.example                    # Local development environment template
├── .env.staging.example            # Staging environment template with security defaults
├── Makefile                        # Common developer automation commands
└── README.md
```

---

## 3. Development Prerequisites

Ensure the following tools are installed locally:
- **Python:** 3.13+
- **Node.js:** 22+ & npm 11+
- **Docker & Docker Compose:** Docker 24+
- **Git**

---

## 4. Environment Configuration

### Local Development
Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```

### Staging Environment
Copy `.env.staging.example` to `.env.staging`:
```bash
cp .env.staging.example .env.staging
cp frontend/.env.staging.example frontend/.env.staging
```

> [!IMPORTANT]
> The staging configuration enforces `DEBUG=False`, strict `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and a runtime guard that blocks any live Razorpay key (`rzp_live_*`).

Refer to [`docs/environment-variables.md`](file:///d:/Projects/EazyDoc/docs/environment-variables.md) for full variable definitions.

---

## 5. Running the Application

### Option A: Local Development with Docker Compose (Recommended)

Starts PostgreSQL, Redis, Django Daphne API, Celery Worker, Celery Beat, and React Frontend:

```bash
# Build and start services in detached mode
docker compose up -d --build

# Follow logs across all containers
docker compose logs -f

# Apply migrations
docker compose exec backend python manage.py migrate

# Stop services
docker compose down
```

**Local Endpoints:**
- **Frontend SPA:** `http://localhost:5173`
- **Backend REST API:** `http://localhost:8000/api/v1/`
- **Swagger Documentation:** `http://localhost:8000/api/docs/`
- **ReDoc Documentation:** `http://localhost:8000/api/redoc/`
- **Health Check:** `http://localhost:8000/api/v1/health/`

---

### Option B: Staging Deployment Topology (Day 16)

The staging environment mirrors production: containers communicate over internal networks (`eazydoc-staging-internal`), database and Redis ports are not exposed externally, and Nginx serves as the SSL reverse proxy on ports 80 and 443.

```bash
# 1. Generate staging SSL certificates
python scripts/generate_staging_certs.py

# 2. Build and launch staging services
docker compose -f docker-compose.staging.yml up -d --build

# 3. Verify health status across API, Database, and Redis
python scripts/staging_health_check.py https://localhost

# 4. View logs
docker compose -f docker-compose.staging.yml logs -f backend
```

**Staging Endpoints:**
- **HTTPS Frontend & API:** `https://localhost` or `https://staging.eazydoc.internal`
- **HTTP (Redirected):** `http://localhost`
- **API Base:** `https://localhost/api/v1/`
- **Swagger UI:** `https://localhost/api/docs/`
- **Health Check:** `https://localhost/api/v1/health/`

Refer to [`docs/staging-deployment-guide.md`](file:///d:/Projects/EazyDoc/docs/staging-deployment-guide.md) and [`docs/deployment-runbook.md`](file:///d:/Projects/EazyDoc/docs/deployment-runbook.md).

---

### Option C: Running Locally Without Docker

#### Backend Setup
```bash
cd backend

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements/development.txt

# Run migrations and start development server
python manage.py migrate
python manage.py runserver 8000
```

#### Frontend Setup
```bash
cd frontend

# Install packages and start Vite dev server
npm install
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## 6. Testing & Quality Assurance

The repository maintains an automated test suite with **311 passing tests** covering multi-tenant isolation, role-based access control, appointment booking concurrency, payment webhooks, and end-to-end staging flows.

### Running Backend Tests
```bash
cd backend

# Run the complete test suite (all 311 tests)
python manage.py test

# Run specific domain test suites
python manage.py test tests.test_auth
python manage.py test tests.test_tenant_isolation
python manage.py test tests.test_concurrency
python manage.py test tests.test_payments
python manage.py test tests.test_staging_e2e_verification
```

### System Configuration Checks
```bash
cd backend

# Validate development settings
python manage.py check

# Validate staging settings (checks deployment flags & CSRF)
python manage.py check --settings=config.settings.staging
```

### Frontend Code Quality
```bash
cd frontend

# Run ESLint validation
npm run lint

# Execute production TypeScript build
npm run build
```

---

## 7. Core Architectural Capabilities

### Multi-Tenant Isolation
- Strict database-level and query-level isolation ensuring clinics cannot view other clinics' patients, appointments, medical records, or financial metrics.
- Enforced role hierarchies: **Super Admin**, **Clinic Owner**, **Staff**, **Doctor**, and **Patient**.

### Scheduling & Concurrency Engine
- Doctor schedules partitioned per clinic with configurable consultation buffers.
- Cross-clinic conflict detection preventing a doctor from being scheduled in overlapping slots across different clinics.
- Concurrency-safe booking utilizing PostgreSQL `select_for_update` row locks and Redis 15-minute temporary holds to eliminate double bookings.

### Razorpay Payments & Platform Commissions
- Server-side Razorpay order generation and verification with HMAC-SHA256 signatures.
- Platform commission calculation using decimal `ROUND_HALF_UP` arithmetic ($gross = commission + clinic\_share$).
- Idempotent webhook handling preventing duplicate credit or refund executions.

### Asynchronous Operations
- Background job processing powered by Celery & Redis.
- Celery Beat scheduler executing periodic appointment reminders, reservation expiration sweeps, and daily metric aggregations.

### Database Backups & Recovery
- Automated backup scripts with SHA-256 verification and retention policies.
- Tested point-in-time recovery with target RTO $\le$ 30 minutes and RPO $\le$ 15 minutes.
- See [`docs/database-deployment.md`](file:///d:/Projects/EazyDoc/docs/database-deployment.md) and [`docs/rollback-procedure.md`](file:///d:/Projects/EazyDoc/docs/rollback-procedure.md).

---

## 8. Documentation Index

Detailed specifications, runbooks, and audit reports are located in the [`docs/`](file:///d:/Projects/EazyDoc/docs/) directory:

| Document | Purpose |
| :--- | :--- |
| [`docs/deployment-assessment.md`](file:///d:/Projects/EazyDoc/docs/deployment-assessment.md) | Initial staging infrastructure assessment and security review |
| [`docs/staging-deployment-guide.md`](file:///d:/Projects/EazyDoc/docs/staging-deployment-guide.md) | Step-by-step staging setup, SSL generation, and container launch |
| [`docs/environment-variables.md`](file:///d:/Projects/EazyDoc/docs/environment-variables.md) | Complete environment variable specification across all environments |
| [`docs/database-deployment.md`](file:///d:/Projects/EazyDoc/docs/database-deployment.md) | Database configuration, indexing, migration checks, and backup procedures |
| [`docs/deployment-runbook.md`](file:///d:/Projects/EazyDoc/docs/deployment-runbook.md) | Operational runbook, health checks, troubleshooting, and incident response |
| [`docs/staging-test-report.md`](file:///d:/Projects/EazyDoc/docs/staging-test-report.md) | Test execution results (311 tests), coverage, and E2E verification |
| [`docs/rollback-procedure.md`](file:///d:/Projects/EazyDoc/docs/rollback-procedure.md) | Rollback triggers, database restoration steps, and RTO/RPO targets |
| [`docs/production-readiness-report.md`](file:///d:/Projects/EazyDoc/docs/production-readiness-report.md) | Comprehensive Day 15 production readiness and security audit report |
| [`docs/payments-and-commission.md`](file:///d:/Projects/EazyDoc/docs/payments-and-commission.md) | Razorpay payment flow, webhook handling, and commission ledger |
| [`docs/architecture.md`](file:///d:/Projects/EazyDoc/docs/architecture.md) | High-level system architecture and component interactions |
| [`docs/database-design.md`](file:///d:/Projects/EazyDoc/docs/database-design.md) | Entity relationship diagrams, schema definitions, and constraints |

---

## 9. Useful Developer Commands (Makefile)

```bash
make help            # Display list of available developer targets
make up              # Start all containers in detached mode
make down            # Stop all containers
make build           # Rebuild Docker container images
make logs            # Tail logs of all running containers
make migrate         # Execute Django database migrations
make makemigrations  # Inspect models and generate new migrations
make test-backend    # Run all backend automated tests
make test-frontend   # Build frontend and verify TypeScript compilation
make lint            # Run frontend linter
make check           # Run Django system checks
```
