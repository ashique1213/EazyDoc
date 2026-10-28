# Notifications and Appointment Reminders Architecture (Day 14)

## 1. Overview & Architecture

EazyDoc incorporates a multi-tenant, channel-extensible notification and appointment reminder system.
It supports:
- **In-App Notifications**: Real-time notifications persisted in PostgreSQL and delivered to authenticated users via REST endpoints.
- **Email Notifications**: Responsive HTML and plaintext multipart transactional emails dispatched via Celery background workers.
- **Scheduled Reminders**: Configurable 24-hour and 2-hour appointment reminders scheduled via Celery Beat periodic tasks, respecting clinic-specific timezones.
- **Extensible Channel Design**: Channel adapters allow future channels (SMS, WhatsApp, WebPush) to be integrated cleanly without touching business event producers.

```
                    ┌─────────────────────────┐
                    │   Business Operations   │
                    │ (Appointments, Payments,│
                    │   Clinics, Invitations) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                     transaction.on_commit
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   NotificationService   │
                    └────────────┬────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
      ┌─────────────────────┐        ┌─────────────────────┐
      │ In-App Notification │        │  Delivery Dispatch  │
      │   (Postgres DB)     │        └──────────┬──────────┘
      └─────────────────────┘                   │
                                                ▼
                                     ┌─────────────────────┐
                                     │  Celery Email Task  │
                                     │ (Bounded Backoff &  │
                                     │    Idempotency)     │
                                     └──────────┬──────────┘
                                                │
                                                ▼
                                     ┌─────────────────────┐
                                     │ Email Provider/SMTP │
                                     └─────────────────────┘
```

---

## 2. Notification Event Catalogue

| Event Type | Trigger Point | Eligible Recipients | Channels | Content / Summary |
|------------|---------------|---------------------|----------|-------------------|
| `APPOINTMENT_CONFIRMED` | Successful booking/payment or clinic manual confirmation | Patient, Doctor | IN_APP, EMAIL | Booking reference, doctor name, clinic name, date & time |
| `APPOINTMENT_REMINDER` | Celery Beat 24h & 2h before consultation | Patient | IN_APP, EMAIL | Upcoming appointment time (in clinic timezone), preparation instructions |
| `APPOINTMENT_CANCELLED` | Patient or clinic cancels appointment | Affected Patient & Doctor | IN_APP, EMAIL | Booking reference, cancellation reason, contact info |
| `APPOINTMENT_RESCHEDULED` | Patient or clinic reschedules appointment | Affected Patient & Doctor | IN_APP, EMAIL | Old vs new slot, clinic name, updated booking reference |
| `DOCTOR_UNAVAILABILITY` | Doctor or clinic reports unavailability / closure | Affected Patients & Clinic Staff | IN_APP, EMAIL | Alert that appointment requires rescheduling or reassignment |
| `PAYMENT_VERIFIED` | Razorpay signature verification or webhook success | Patient | IN_APP, EMAIL | Amount paid, order ID, payment ID, confirmed booking |
| `PAYMENT_FAILED` | Confirmed Razorpay payment failure webhook | Patient | IN_APP, EMAIL | Failed attempt notice, retry link, payment reference |
| `CLINIC_INVITATION` | Clinic invites doctor to affiliate | Invited Doctor | IN_APP, EMAIL | Clinic name, invitation link, invitation actions |
| `CLINIC_INVITATION_RESPONSE` | Doctor accepts or rejects affiliation | Clinic Owner | IN_APP, EMAIL | Doctor name, accepted/rejected status |

---

## 3. Recipient and Privacy Rules

1. **Tenant & Role Isolation**:
   - **Patients**: Can access and query only their own in-app notifications and email updates (`recipient=request.user`).
   - **Doctors**: Access notifications strictly related to their appointments, affiliations, and schedules.
   - **Clinic Owners & Staff**: Access operational notifications only for clinics they have verified authorization to manage.
   - **Super Admin**: Receives platform-wide operational alerts only when explicitly configured.
2. **Medical & Sensitive Data Privacy**:
   - Notification titles and email subject lines never contain confidential diagnostic, medical, or clinical notes.
   - Financial platform commission percentages and platform profit shares are strictly omitted from patient notifications.
   - Tokens, webhook secrets, and private verification documents are strictly excluded.
3. **Authorization on Associated Resources**:
   - Notification payloads provide relative `action_url` links (e.g. `/appointments/{id}`).
   - The backend API verifies the user's role and permission whenever the user navigates to the target resource.

---

## 4. Database Schema

The notification subsystem consists of four core models in `apps/notifications/models.py`:

### `Notification`
- `id`: UUID (Primary Key).
- `recipient`: ForeignKey (`users.User`, `on_delete=CASCADE`).
- `notification_type`: Choice (`NotificationType`).
- `title`: CharField(max_length=255).
- `message`: TextField.
- `related_object_type`: CharField(max_length=100, blank=True).
- `related_object_id`: CharField(max_length=100, blank=True).
- `action_url`: CharField(max_length=500, blank=True).
- `is_read`: BooleanField(default=False, db_index=True).
- `read_at`: DateTimeField(null=True, blank=True).
- `idempotency_key`: CharField(max_length=255, unique=True, null=True, db_index=True).
- `created_at`: DateTimeField(auto_now_add=True, db_index=True).

### `NotificationDelivery`
- `id`: UUID (Primary Key).
- `notification`: ForeignKey(`Notification`, related_name="deliveries").
- `channel`: Choice (`IN_APP`, `EMAIL`, `SMS`, `WHATSAPP`).
- `status`: Choice (`PENDING`, `PROCESSING`, `SENT`, `FAILED`, `CANCELLED`, `SKIPPED`).
- `attempt_count`: PositiveIntegerField(default=0).
- `last_attempt_at`: DateTimeField(null=True, blank=True).
- `sent_at`: DateTimeField(null=True, blank=True).
- `failure_reason`: TextField(blank=True).
- `provider_message_id`: CharField(max_length=255, blank=True).
- `idempotency_key`: CharField(max_length=255, unique=True, null=True).

### `NotificationPreference`
- `user`: OneToOneField(`users.User`, related_name="notification_preferences").
- `email_enabled`: BooleanField(default=True).
- `in_app_enabled`: BooleanField(default=True).
- `appointment_reminders_enabled`: BooleanField(default=True).
- `appointment_updates_enabled`: BooleanField(default=True).
- `payment_updates_enabled`: BooleanField(default=True).
- `clinic_updates_enabled`: BooleanField(default=True).
- `created_at` & `updated_at`.

### `AppointmentReminderSchedule`
- `id`: UUID (Primary Key).
- `appointment`: ForeignKey(`appointments.Appointment`, related_name="reminder_schedules").
- `reminder_type`: Choice (`REMINDER_24H`, `REMINDER_2H`).
- `scheduled_for`: DateTimeField(db_index=True).
- `schedule_version`: PositiveIntegerField(default=1).
- `status`: Choice (`PENDING`, `SENT`, `CANCELLED`, `SKIPPED`).
- `sent_at`: DateTimeField(null=True, blank=True).
- `delivery`: ForeignKey(`NotificationDelivery`, null=True, blank=True).
- **Constraint**: `UniqueConstraint(fields=['appointment', 'reminder_type', 'schedule_version'], name='unique_appointment_reminder_version')`.

---

## 5. Scheduled Appointment Reminders Engine

### Clinic Timezone Handling
Reminders are computed in the timezone of the appointment's clinic:
- If clinic timezone is `"Asia/Kolkata"`, the appointment slot datetime is resolved in Asia/Kolkata.
- 24-hour and 2-hour target offsets are translated into timezone-aware UTC timestamps stored in `AppointmentReminderSchedule.scheduled_for`.

### Celery Beat Periodic Polling
Celery Beat runs `apps.notifications.tasks.process_due_appointment_reminders` periodically (default: every 5 minutes):
1. Queries `AppointmentReminderSchedule` where:
   - `status = PENDING`
   - `scheduled_for <= current_time`
   - `scheduled_for >= current_time - 3 hours` (grace period).
2. For each due reminder:
   - Re-checks appointment status (`CONFIRMED`).
   - Verifies the appointment schedule version matches the schedule record.
   - If rescheduled or cancelled, automatically marks reminder `CANCELLED` or `SKIPPED`.
   - Checks recipient's reminder preferences (`appointment_reminders_enabled` and `email_enabled`).
   - Renders localized date and time in the clinic's timezone.
   - Dispatches in-app and email notifications.
   - Atomically updates status to `SENT`.

### Version Invalidation on Reschedule & Cancel
- **Rescheduling**: `schedule_version` on the appointment is incremented. Prior pending reminders for the previous schedule version are invalidated (`status=CANCELLED`). New reminder records are created for the new slot with the new version.
- **Cancellation**: All pending reminders for the appointment are immediately transitioned to `CANCELLED`.
- **Completion / No-Show**: Any remaining pending reminders are transitioned to `CANCELLED`.

---

## 6. Celery Worker, Beat & Email Configuration

### Environment Variables (`.env`)
```bash
# Email Backend Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-smtp-secret-key
DEFAULT_FROM_EMAIL="EazyDoc Support <notifications@eazydoc.example.com>"

# Celery & Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
REDIS_URL=redis://redis:6379/0
```

### Running Locally
```bash
# 1. Start Celery Worker
celery -A config worker -l INFO

# 2. Start Celery Beat Scheduler
celery -A config beat -l INFO

# 3. Test Email Delivery locally in Console mode
# In .env: EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Docker Compose
Both `eazydoc_celery` and `eazydoc_celery_beat` are defined as services in `docker-compose.yml`, mounting the backend application and depending on Redis and PostgreSQL.

---

## 7. Reliability, Retries & Idempotency

- **Atomic Dispatches**: Notification dispatches use `transaction.on_commit(...)` to ensure tasks are queued only after the database commit succeeds.
- **Deduplication**: In-app notifications and delivery records enforce unique idempotency keys (`appt_confirmed_patient_{appt_id}`, `pay_verified_{order_id}`, etc.). Duplicate attempts are logged and safely ignored.
- **Bounded Exponential Backoff**: Transient errors (e.g. SMTP connection timeouts) are retried up to 3 times with exponential backoff (`countdown = 2 ** attempt * 30`).
- **Permanent Failure Handling**: Invalid recipient email addresses or configuration errors immediately transition the delivery record to `FAILED` with sanitized failure reasons, without infinite retry loops.

---

## 8. REST API Endpoints

All notification endpoints follow the `/api/v1/notifications/` prefix and require JWT authentication:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/notifications/` | List recipient's paginated notifications (query params: `is_read`, `page`, `page_size`) |
| `GET` | `/api/v1/notifications/unread-count/` | Return total unread notifications count `{ count: N }` |
| `POST` | `/api/v1/notifications/{id}/read/` | Mark a specific notification as read |
| `POST` | `/api/v1/notifications/read-all/` | Mark all unread notifications for the user as read |
| `GET` | `/api/v1/notifications/preferences/` | Get current notification preferences |
| `PATCH` | `/api/v1/notifications/preferences/` | Update notification preferences |

---

## 9. Frontend Notification Components

- **`NotificationBell`** (`frontend/src/features/notifications/components/NotificationBell.tsx`):
  - Placed in both Dashboard and Public layout headers.
  - Live unread badge count with auto-refresh on read actions.
  - Quick dropdown listing recent notifications with relative timestamps ("2m ago", "1h ago").
  - "Mark all as read" button.
- **`NotificationsPage`** (`frontend/src/pages/NotificationsPage.tsx`):
  - Dedicated notification center at `/notifications`.
  - Filter tabs: **All**, **Unread**, and **Notification Settings**.
  - Interactive item cards with unread indicator dots, action link buttons, and mark-as-read buttons.
- **`NotificationPreferencesSection`** (`frontend/src/features/notifications/components/NotificationPreferencesSection.tsx`):
  - Fine-grained channel toggles (Email & In-App) and category toggles (Appointment Reminders, Status Updates, Payment Receipts, Clinic Affiliations).
  - Prominent banner distinguishing essential security/transactional notices from optional alerts.
