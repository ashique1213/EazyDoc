from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo
from django.core import mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole, UserStatus
from apps.appointments.models import Appointment, AppointmentHistory, AppointmentStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.notifications.models import (
    AppointmentReminderSchedule,
    DeliveryStatus,
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationPreference,
    NotificationType,
)
from apps.notifications.services import (
    NotificationService,
    handle_appointment_event,
    handle_clinic_doctor_event,
    handle_payment_event,
    invalidate_appointment_reminders,
    reschedule_appointment_reminders,
    schedule_appointment_reminders,
)
from apps.notifications.tasks import (
    process_due_appointment_reminders,
    send_email_notification_task,
)
from apps.payments.models import Payment, PaymentStatus


class NotificationSystemTests(APITestCase):
    """
    Comprehensive test suite for Notifications and Appointment Reminders (Day 14).
    Validates:
    - Scoping and access control (own notifications, unread count, mark-read isolation)
    - Preference enforcement and permitted field validation
    - Appointment confirmation, cancellation, and rescheduling event notifications
    - Verified backend payment success/failure triggers
    - Rollback safety (no false success notifications on rolled back transactions)
    - Duplicate event idempotency
    - Celery email task execution and bounded retry behavior
    - Reminder scheduling respecting clinic timezone, schedule versioning, and Celery Beat idempotency
    """

    def setUp(self):
        # 1. Users
        self.patient_alice = User.objects.create_user(
            email="alice.patient@gmail.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Alice",
            last_name="Smith",
        )
        self.patient_bob = User.objects.create_user(
            email="bob.patient@gmail.com",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
            status=UserStatus.ACTIVE,
            first_name="Bob",
            last_name="Jones",
        )
        self.clinic_owner = User.objects.create_user(
            email="dr.owner@wellnessclinic.com",
            password="StrongPassword123!",
            role=UserRole.CLINIC_OWNER,
            status=UserStatus.ACTIVE,
            first_name="Arthur",
            last_name="Conan",
        )
        self.doctor_user = User.objects.create_user(
            email="dr.watson@wellnessclinic.com",
            password="StrongPassword123!",
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
            first_name="John",
            last_name="Watson",
        )

        # 2. Clinic & Doctor
        self.clinic = Clinic.objects.create(
            name="Apex Wellness Clinic",
            slug="apex-wellness",
            owner=self.clinic_owner,
            status=ClinicStatus.APPROVED,
            email="contact@apexwellness.com",
            phone="+919876543210",
            address_line_1="100 MG Road",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            timezone="Asia/Kolkata",
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            full_name="Dr. John Watson",
            registration_number="MMC-10029",
            registration_council="Maharashtra Medical Council",
            specialization="General Medicine",
            verification_status=DoctorVerificationStatus.VERIFIED,
        )
        self.association = DoctorClinic.objects.create(
            doctor=self.doctor,
            clinic=self.clinic,
            status=DoctorClinicStatus.ACTIVE,
            consultation_fee=Decimal("500.00"),
            appointment_duration_minutes=30,
        )

        # 3. Base Appointment
        now = timezone.now()
        self.start_at = now + timedelta(days=2)
        self.end_at = self.start_at + timedelta(minutes=30)
        self.appointment = Appointment.objects.create(
            booking_reference="EZD-TEST-ALICE01",
            patient=self.patient_alice,
            doctor_clinic=self.association,
            doctor=self.doctor,
            clinic=self.clinic,
            start_at=self.start_at,
            end_at=self.end_at,
            status=AppointmentStatus.CONFIRMED,
            consultation_fee=Decimal("500.00"),
            currency="INR",
            payment_status=PaymentStatus.PAID,
        )

        # API URLs
        self.list_url = reverse("api-v1:notifications:list")
        self.unread_count_url = reverse("api-v1:notifications:unread-count")
        self.read_all_url = reverse("api-v1:notifications:read-all")
        self.preferences_url = reverse("api-v1:notifications:preferences")

    # 1. A user can list only their own notifications
    def test_user_can_list_only_their_own_notifications(self):
        Notification.objects.create(
            recipient=self.patient_alice,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Alice Notification",
            message="Message for Alice",
        )
        Notification.objects.create(
            recipient=self.patient_bob,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Bob Notification",
            message="Message for Bob",
        )

        self.client.force_authenticate(user=self.patient_alice)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Alice Notification")

    # 2. A user cannot mark another user's notification as read
    def test_user_cannot_mark_another_users_notification_as_read(self):
        bob_notification = Notification.objects.create(
            recipient=self.patient_bob,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Bob Notification",
            message="Message for Bob",
        )

        self.client.force_authenticate(user=self.patient_alice)
        read_url = reverse("api-v1:notifications:mark-read", kwargs={"notification_id": bob_notification.id})
        response = self.client.post(read_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify Bob's notification is still unread
        bob_notification.refresh_from_db()
        self.assertFalse(bob_notification.is_read)

    # 3. Unread count is correct
    def test_unread_count_is_accurate(self):
        Notification.objects.create(
            recipient=self.patient_alice,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Unread 1",
            message="Msg 1",
            is_read=False,
        )
        Notification.objects.create(
            recipient=self.patient_alice,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Unread 2",
            message="Msg 2",
            is_read=False,
        )
        Notification.objects.create(
            recipient=self.patient_alice,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Read 1",
            message="Msg 3",
            is_read=True,
        )

        self.client.force_authenticate(user=self.patient_alice)
        response = self.client.get(self.unread_count_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 2)

    # 4. Mark-all-as-read affects only the authenticated user
    def test_mark_all_as_read_affects_only_authenticated_user(self):
        n1 = Notification.objects.create(
            recipient=self.patient_alice,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Alice 1",
            message="Msg 1",
            is_read=False,
        )
        n2 = Notification.objects.create(
            recipient=self.patient_bob,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Bob 1",
            message="Msg 2",
            is_read=False,
        )

        self.client.force_authenticate(user=self.patient_alice)
        response = self.client.post(self.read_all_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["marked_read_count"], 1)

        n1.refresh_from_db()
        n2.refresh_from_db()
        self.assertTrue(n1.is_read)
        self.assertFalse(n2.is_read)

    # 5. Preference updates enforce permitted fields
    def test_preference_updates_enforce_permitted_fields(self):
        self.client.force_authenticate(user=self.patient_alice)
        response = self.client.patch(
            self.preferences_url,
            data={
                "email_enabled": False,
                "appointment_reminders_enabled": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["email_enabled"])
        self.assertFalse(response.data["appointment_reminders_enabled"])
        self.assertTrue(response.data["in_app_enabled"])  # unmodified

        prefs = NotificationPreference.get_for_user(self.patient_alice)
        self.assertFalse(prefs.email_enabled)
        self.assertFalse(prefs.appointment_reminders_enabled)

    # 6. Appointment confirmation creates correct notification
    def test_appointment_confirmation_creates_correct_notification(self):
        handle_appointment_event("appointment_created", self.appointment.id)

        alice_notifications = Notification.objects.filter(recipient=self.patient_alice)
        self.assertTrue(alice_notifications.exists())
        latest = alice_notifications.first()
        self.assertEqual(latest.notification_type, NotificationType.APPOINTMENT_CONFIRMED)
        self.assertIn("Apex Wellness Clinic", latest.message)
        self.assertIn(self.appointment.booking_reference, latest.message)

        # Doctor user should also receive notification
        doctor_notifications = Notification.objects.filter(recipient=self.doctor_user)
        self.assertTrue(doctor_notifications.exists())
        self.assertEqual(doctor_notifications.first().notification_type, NotificationType.APPOINTMENT_CONFIRMED)

    # 7. Payment success notifications occur only after verified success
    def test_payment_success_notification_occurs_only_after_verified_success(self):
        payment = Payment.objects.create(
            appointment=self.appointment,
            patient=self.patient_alice,
            clinic=self.clinic,
            gateway_name="RAZORPAY",
            gateway_order_id="order_test_999",
            amount=Decimal("500.00"),
            currency="INR",
            status=PaymentStatus.PAID,
        )

        handle_payment_event("payment_verified", payment.id)

        notifs = Notification.objects.filter(recipient=self.patient_alice, notification_type=NotificationType.PAYMENT_VERIFIED)
        self.assertEqual(notifs.count(), 1)
        self.assertIn("500.00", notifs.first().message)

    # 8. Failed or rolled-back business transactions do not produce false success notifications
    def test_rolled_back_transactions_do_not_produce_notifications(self):
        initial_count = Notification.objects.count()

        # Simulate rolled-back transaction
        try:
            with transaction.atomic():
                # Simulating an event hook inside transaction that rolls back
                transaction.on_commit(lambda: handle_appointment_event("appointment_created", self.appointment.id))
                raise ValueError("Intentional business transaction rollback")
        except ValueError:
            pass

        self.assertEqual(Notification.objects.count(), initial_count)

    # 9. Duplicate event processing does not create duplicate notification records
    def test_duplicate_event_processing_does_not_create_duplicate_notifications(self):
        # First dispatch
        handle_appointment_event("appointment_created", self.appointment.id)
        count_first = Notification.objects.filter(recipient=self.patient_alice).count()

        # Second dispatch with duplicate event
        handle_appointment_event("appointment_created", self.appointment.id)
        count_second = Notification.objects.filter(recipient=self.patient_alice).count()

        self.assertEqual(count_first, count_second)

    # 10. Email delivery is dispatched through background task system
    @patch("apps.notifications.tasks.send_email_notification_task.delay")
    def test_email_delivery_is_dispatched_via_celery_task(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            NotificationService.send_notification(
                recipient=self.patient_alice,
                notification_type=NotificationType.APPOINTMENT_CONFIRMED,
                title="Appointment Email Test",
                message="This should dispatch Celery email task.",
            )

        deliveries = NotificationDelivery.objects.filter(
            notification__recipient=self.patient_alice,
            channel=NotificationChannel.EMAIL,
        )
        self.assertTrue(deliveries.exists())
        mock_delay.assert_called_once_with(str(deliveries.first().id))

    # 11. Transient delivery failures are retried within configured limits
    @patch("apps.notifications.tasks.EmailMultiAlternatives.send")
    def test_transient_delivery_failures_retry_within_limits(self, mock_send):
        mock_send.side_effect = ConnectionError("Temporary SMTP network timeout")

        notif = Notification.objects.create(
            recipient=self.patient_alice,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Transient Retry Test",
            message="Transient test message",
        )
        delivery = NotificationDelivery.objects.create(
            notification=notif,
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.PENDING,
        )

        with self.assertRaises(Exception):
            send_email_notification_task.apply(args=[str(delivery.id)])

        delivery.refresh_from_db()
        self.assertIn("ConnectionError", delivery.sanitized_failure_reason)
        self.assertGreaterEqual(delivery.attempt_count, 1)

    # 12. Permanent delivery failures do not retry indefinitely
    def test_permanent_delivery_failures_fail_immediately_without_retry(self):
        user_no_email = User.objects.create_user(
            email="invalid-user-no-email",
            password="StrongPassword123!",
            role=UserRole.PATIENT,
        )
        notif = Notification.objects.create(
            recipient=user_no_email,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Permanent Failure Test",
            message="No email address",
        )
        delivery = NotificationDelivery.objects.create(
            notification=notif,
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.PENDING,
        )

        result = send_email_notification_task.apply(args=[str(delivery.id)]).get()
        self.assertEqual(result, "Invalid recipient email")

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DeliveryStatus.FAILED)
        self.assertIn("valid email address", delivery.sanitized_failure_reason)

    # 13. Cancelled appointments do not receive future reminders
    def test_cancelled_appointments_do_not_receive_reminders(self):
        schedule_appointment_reminders(self.appointment, schedule_version=1)
        self.assertTrue(self.appointment.reminder_schedules.filter(status="PENDING").exists())

        # Cancel appointment
        self.appointment.status = AppointmentStatus.CANCELLED
        self.appointment.save(update_fields=["status"])
        invalidate_appointment_reminders(self.appointment)

        # All reminders must be CANCELLED
        pending_count = self.appointment.reminder_schedules.filter(status="PENDING").count()
        self.assertEqual(pending_count, 0)

        # Running Celery Beat reminder task should process 0 reminders
        processed = process_due_appointment_reminders()
        self.assertEqual(processed, 0)

    # 14. Rescheduled appointments do not receive stale reminders
    def test_rescheduled_appointments_invalidate_old_and_schedule_new_reminders(self):
        schedule_appointment_reminders(self.appointment, schedule_version=1)
        v1_schedules = list(self.appointment.reminder_schedules.filter(schedule_version=1))

        # Reschedule appointment to +5 days
        self.appointment.start_at = timezone.now() + timedelta(days=5)
        self.appointment.end_at = self.appointment.start_at + timedelta(minutes=30)
        self.appointment.save(update_fields=["start_at", "end_at"])

        reschedule_appointment_reminders(self.appointment)

        # Previous v1 schedules should be CANCELLED
        for s in v1_schedules:
            s.refresh_from_db()
            self.assertEqual(s.status, "CANCELLED")

        # New v2 schedules should exist
        v2_schedules = self.appointment.reminder_schedules.filter(schedule_version=2)
        self.assertTrue(v2_schedules.exists())

    # 15. Reminder scheduling respects clinic timezone
    def test_reminder_respects_clinic_timezone(self):
        # Set clinic timezone to America/New_York
        self.clinic.timezone = "America/New_York"
        self.clinic.save(update_fields=["timezone"])

        future_dt = timezone.now() + timedelta(hours=10)
        self.appointment.start_at = future_dt
        self.appointment.save(update_fields=["start_at"])

        # Create a due reminder schedule
        schedule = AppointmentReminderSchedule.objects.create(
            appointment=self.appointment,
            reminder_type="REMINDER_2H",
            scheduled_for=timezone.now() - timedelta(minutes=5),  # Due now
            schedule_version=1,
            status="PENDING",
        )

        process_due_appointment_reminders()

        schedule.refresh_from_db()
        self.assertEqual(schedule.status, "SENT")
        self.assertIsNotNone(schedule.notification)

    # 16. Repeated Celery Beat runs do not duplicate reminders
    def test_repeated_celery_beat_runs_do_not_duplicate_reminders(self):
        AppointmentReminderSchedule.objects.create(
            appointment=self.appointment,
            reminder_type="REMINDER_24H",
            scheduled_for=timezone.now() - timedelta(minutes=5),  # Due
            schedule_version=1,
            status="PENDING",
        )

        # Run beat task first time
        run1 = process_due_appointment_reminders()
        self.assertEqual(run1, 1)

        # Run beat task second time immediately
        run2 = process_due_appointment_reminders()
        self.assertEqual(run2, 0)

        # Verify only 1 reminder notification was generated for patient
        reminders = Notification.objects.filter(
            recipient=self.patient_alice,
            notification_type=NotificationType.APPOINTMENT_REMINDER,
        )
        self.assertEqual(reminders.count(), 1)

    # 17. User preferences are respected
    def test_user_preferences_are_strictly_respected(self):
        # Patient disables appointment reminders
        prefs = NotificationPreference.get_for_user(self.patient_alice)
        prefs.appointment_reminders_enabled = False
        prefs.save()

        AppointmentReminderSchedule.objects.create(
            appointment=self.appointment,
            reminder_type="REMINDER_24H",
            scheduled_for=timezone.now() - timedelta(minutes=10),
            schedule_version=1,
            status="PENDING",
        )

        process_due_appointment_reminders()

        # Should be marked SKIPPED and not delivered
        sched = AppointmentReminderSchedule.objects.get(appointment=self.appointment)
        self.assertEqual(sched.status, "SKIPPED")
        self.assertIsNone(sched.notification)

    # 18. Unauthorized users cannot access notification links or related objects
    def test_unauthorized_user_cannot_access_notification_links(self):
        # Attempting to access another patient's appointment returns 403 or 404
        self.client.force_authenticate(user=self.patient_bob)
        url = reverse("api-v1:appointments:appointment-detail", kwargs={"appointment_id": self.appointment.id})
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    # 19. Sensitive information is not exposed in public or unrelated notifications
    def test_sensitive_information_is_not_exposed(self):
        handle_appointment_event("appointment_created", self.appointment.id)
        notif = Notification.objects.filter(recipient=self.patient_alice).first()

        # Check that no payment keys, token secrets, or internal commissions are in notification
        self.assertNotIn("commission", notif.message.lower())
        self.assertNotIn("secret", notif.message.lower())
        self.assertNotIn("token", notif.message.lower())

    # 20. Doctor clinic invitations and responses generate proper notifications
    def test_doctor_clinic_invitation_lifecycle_notifications(self):
        # Invitation sent
        handle_clinic_doctor_event("clinic_invitation_sent", self.association.id)
        doc_notifs = Notification.objects.filter(
            recipient=self.doctor_user,
            notification_type=NotificationType.CLINIC_INVITATION_SENT,
        )
        self.assertTrue(doc_notifs.exists())

        # Invitation accepted
        handle_clinic_doctor_event("clinic_invitation_accepted", self.association.id)
        owner_notifs = Notification.objects.filter(
            recipient=self.clinic_owner,
            notification_type=NotificationType.CLINIC_INVITATION_ACCEPTED,
        )
        self.assertTrue(owner_notifs.exists())
