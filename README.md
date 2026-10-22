# EazyDoc — Multi-Clinic Doctor & Practice Management SaaS

A production-ready SaaS platform connecting Patients, Verified Doctors, and Multi-Clinic Practices with real-time queue management, schedule conflict detection, strict cancellation policies, and integrated healthcare workflows.

---

## 1. Technology Stack

### Backend
- **Framework:** Python 3.13+, Django 5.1+, Django REST Framework 3.15+
- **Database:** PostgreSQL 16 (Relational integrity, exclusion constraints, `select_for_update`)
- **Cache & Message Broker:** Redis 7 (Celery broker, ephemeral slot reservation hold, Channels Pub/Sub)
- **Background Tasks:** Celery 5.5+ & Celery Beat (Periodic tasks, refund processing, notification dispatch)
- **WebSockets / Real-Time:** Django Channels 4.2+ & Daphne ASGI
- **Authentication:** SimpleJWT (Dual-token JWT, rotating refresh token, Redis blacklisting)
- **API Documentation:** `drf-spectacular` (OpenAPI 3.0 / Swagger UI / Redoc)
- **Configuration:** `django-environ`

### Frontend
- **Framework:** React 19, TypeScript (Strict Mode)
- **Build Tool:** Vite 6
- **UI & Styling:** Tailwind CSS 3.4+, shadcn/ui design tokens
- **Routing:** React Router v7
- **Server State & Data Fetching:** TanStack Query (React Query) v5
- **HTTP Client:** Axios (Custom client with interceptors)
- **Icons:** Lucide React

### Infrastructure & DevOps
- **Containerization:** Docker & Docker Compose
- **Web Server:** Nginx Reverse Proxy
- **Payment Gateway:** Razorpay (HMAC-SHA256 server-verified)
- **Object Storage:** AWS S3 (Private buckets with 15-minute temporary pre-signed URLs)

---

## 2. Architecture & Monorepo Structure

```text
EazyDoc/
├── backend/
│   ├── config/                     # Project config (ASGI, WSGI, Celery, URLs)
│   │   └── settings/               # Modular settings (base, development, production)
│   ├── apps/                       # Domain apps
│   │   ├── accounts/               # Custom User model (roles, UUID, identity)
│   │   ├── clinics/                # Clinic management & staff
│   │   ├── doctors/                # Doctor profiles & credentials
│   │   ├── patients/               # Patient records & emergency contacts
│   │   ├── appointments/           # Booking engine & anti-double-booking locks
│   │   ├── schedules/              # Recurring shifts & cross-clinic conflict engine
│   │   ├── consultations/          # Clinical notes & vitals
│   │   ├── prescriptions/          # Digital prescriptions & items
│   │   ├── payments/               # Razorpay & commission ledger
│   │   ├── notifications/          # Celery notification dispatches
│   │   ├── documents/              # Secure medical document uploads
│   │   ├── reviews/                # Patient reviews & moderation
│   │   ├── analytics/              # Daily metric aggregations
│   │   └── audit_logs/             # Immutable audit trails
│   ├── requirements/               # base.txt, development.txt, production.txt
│   ├── Dockerfile
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── app/                    # App-level providers
│   │   ├── components/             # Reusable UI & shadcn/ui components
│   │   ├── features/               # Feature-sliced modules
│   │   ├── layouts/                # PublicLayout, AuthLayout, DashboardLayout
│   │   ├── pages/                  # HomePage, LoginPage, RegisterPage, Portal shells
│   │   ├── routes/                 # React Router v7 routes
│   │   ├── services/               # Axios API client (api.ts)
│   │   ├── types/                  # TypeScript domain models
│   │   └── index.css               # Tailwind & design tokens
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docs/                           # Architecture, specifications & workflows
├── docker/                         # Entrypoint scripts & container configs
├── docker-compose.yml              # Multi-container local orchestration
├── .env.example                    # Environment variable template
├── Makefile                        # Common developer commands
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

## 4. Environment Variables

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

Key environment configurations:
- `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `CORS_ALLOWED_ORIGINS`
- `JWT_ACCESS_LIFETIME_MINUTES`, `JWT_REFRESH_LIFETIME_DAYS`
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`

---

## 5. Running with Docker Compose (Recommended)

To start the complete development stack (PostgreSQL, Redis, Django API, Celery Worker, Celery Beat, and React Frontend):

```bash
# Build and run containers in detached mode
docker compose up -d --build

# View real-time container logs
docker compose logs -f

# Run database migrations inside container
docker compose exec backend python manage.py migrate

# Stop all services
docker compose down
```

Services exposed:
- **Frontend App:** `http://localhost:5173`
- **Backend REST API:** `http://localhost:8000/api/v1/`
- **OpenAPI Swagger Docs:** `http://localhost:8000/api/docs/`
- **OpenAPI Redoc:** `http://localhost:8000/api/redoc/`
- **PostgreSQL 16:** `localhost:5432`
- **Redis 7:** `localhost:6379`

---

## 6. Running Locally (Without Docker)

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements/development.txt

# Run migrations
python manage.py migrate

# Start ASGI / WSGI development server
python manage.py runserver 8000
```

### Frontend Setup

```bash
cd frontend

# Install npm packages
npm install

# Start Vite development server
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## 7. Testing & Code Quality

### Backend Tests
Execute unit and smoke tests (runs isolated with fast SQLite test database):
```bash
cd backend
python manage.py test
```

Run Django system configuration check:
```bash
cd backend
python manage.py check
```

### Frontend Checks
Lint and build the React 19 application:
```bash
cd frontend
npm run lint
npm run build
```

---

## 8. API Documentation & Health Check

- **Health Check Endpoint:** `GET /api/v1/health/`
  ```json
  {
    "status": "ok",
    "database": "ok",
    "redis": "ok"
  }
  ```
- **OpenAPI Schema:** `GET /api/schema/`
- **Interactive Swagger UI:** `http://localhost:8000/api/docs/`
- **Interactive ReDoc:** `http://localhost:8000/api/redoc/`

---

## 9. Payments & Platform Commission (Day 11)

- **Razorpay Integration**: Server-authorized order creation, client-side Razorpay Checkout, backend HMAC-SHA256 signature verification, and idempotent webhook handling.
- **Platform Commission**: Default 5.00% platform commission with configurable clinic overrides (`Clinic.commission_rate`), strict `ROUND_HALF_UP` decimal calculations, and invariant enforcement ($gross = commission + clinic\_share$).
- **Pending Reservations**: Configurable reservation expiry (`PAYMENT_RESERVATION_TIMEOUT_MINUTES=15`) with concurrency conflict protection against late overlapping bookings.
- **Detailed Specification**: See [docs/payments-and-commission.md](file:///d:/Projects/EazyDoc/docs/payments-and-commission.md).
