from datetime import timedelta
from decimal import Decimal
import pytz
from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole
from apps.accounts.permissions import IsSuperAdmin
from apps.appointments.models import Appointment, AppointmentStatus
from apps.clinics.models import Clinic, ClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.payments.models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentStatus,
    PlatformSetting,
)


class AdminDashboardSummaryView(APIView):
    """
    Super Admin endpoint returning trusted platform-wide operational and financial metrics.
    All figures are derived directly from transactional database records via aggregations.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Dashboard Summary Metrics",
        description="Returns trusted aggregated metrics for clinics, doctors, users, appointments, and finances.",
        responses={200: dict},
    )
    def get(self, request):
        tz_str = getattr(settings, "TIME_ZONE", "Asia/Kolkata")
        try:
            local_tz = pytz.timezone(tz_str)
        except Exception:
            local_tz = pytz.UTC

        now_utc = timezone.now()
        now_local = now_utc.astimezone(local_tz)
        today_local = now_local.date()

        clinic_id = request.query_params.get("clinic_id")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        # 1. Clinic Metrics
        clinic_qs = Clinic.objects.all()
        if clinic_id:
            clinic_qs = clinic_qs.filter(id=clinic_id)
        if date_from:
            df = parse_date(date_from)
            if df:
                clinic_qs = clinic_qs.filter(created_at__date__gte=df)
        if date_to:
            dt = parse_date(date_to)
            if dt:
                clinic_qs = clinic_qs.filter(created_at__date__lte=dt)

        clinic_stats = clinic_qs.aggregate(
            total=Count("id"),
            approved=Count("id", filter=Q(status=ClinicStatus.APPROVED)),
            pending=Count("id", filter=Q(status=ClinicStatus.PENDING)),
            rejected=Count("id", filter=Q(status=ClinicStatus.REJECTED)),
            suspended=Count("id", filter=Q(status=ClinicStatus.SUSPENDED)),
        )

        # 2. Doctor Metrics
        doctor_qs = Doctor.objects.all()
        if date_from:
            df = parse_date(date_from)
            if df:
                doctor_qs = doctor_qs.filter(created_at__date__gte=df)
        if date_to:
            dt = parse_date(date_to)
            if dt:
                doctor_qs = doctor_qs.filter(created_at__date__lte=dt)

        doctor_stats = doctor_qs.aggregate(
            total=Count("id"),
            verified=Count("id", filter=Q(verification_status=DoctorVerificationStatus.VERIFIED)),
            pending=Count("id", filter=Q(verification_status=DoctorVerificationStatus.PENDING)),
            suspended=Count("id", filter=Q(verification_status=DoctorVerificationStatus.SUSPENDED)),
            rejected=Count("id", filter=Q(verification_status=DoctorVerificationStatus.REJECTED)),
        )

        # 3. Patient and User Counts
        total_patients = User.objects.filter(role=UserRole.PATIENT).count()
        total_users = User.objects.count()

        # 4. Appointment Metrics
        appt_qs = Appointment.objects.all()
        if clinic_id:
            appt_qs = appt_qs.filter(clinic_id=clinic_id)
        if date_from:
            df = parse_date(date_from)
            if df:
                appt_qs = appt_qs.filter(start_at__date__gte=df)
        if date_to:
            dt = parse_date(date_to)
            if dt:
                appt_qs = appt_qs.filter(start_at__date__lte=dt)

        appt_stats = appt_qs.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
            confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
            reschedule_required=Count("id", filter=Q(reschedule_required=True)),
        )

        # Appointments today (in local timezone)
        appointments_today = Appointment.objects.filter(start_at__date=today_local)
        if clinic_id:
            appointments_today = appointments_today.filter(clinic_id=clinic_id)
        appointments_today_count = appointments_today.count()

        # Upcoming appointments
        upcoming_appointments_count = Appointment.objects.filter(
            start_at__gte=now_utc,
            status=AppointmentStatus.CONFIRMED,
        )
        if clinic_id:
            upcoming_appointments_count = upcoming_appointments_count.filter(clinic_id=clinic_id)
        upcoming_count = upcoming_appointments_count.count()

        # 5. Financial Metrics
        payment_qs = Payment.objects.all()
        if clinic_id:
            payment_qs = payment_qs.filter(clinic_id=clinic_id)
        if date_from:
            df = parse_date(date_from)
            if df:
                payment_qs = payment_qs.filter(created_at__date__gte=df)
        if date_to:
            dt = parse_date(date_to)
            if dt:
                payment_qs = payment_qs.filter(created_at__date__lte=dt)

        payment_stats = payment_qs.aggregate(
            total_payments=Count("id"),
            successful_payments=Count("id", filter=Q(status=PaymentStatus.PAID)),
            failed_payments=Count("id", filter=Q(status=PaymentStatus.FAILED)),
            gross_volume=Sum("amount", filter=Q(status=PaymentStatus.PAID)),
            failed_volume=Sum("amount", filter=Q(status=PaymentStatus.FAILED)),
        )

        commission_qs = CommissionRecord.objects.all()
        if clinic_id:
            commission_qs = commission_qs.filter(clinic_id=clinic_id)
        if date_from:
            df = parse_date(date_from)
            if df:
                commission_qs = commission_qs.filter(created_at__date__gte=df)
        if date_to:
            dt = parse_date(date_to)
            if dt:
                commission_qs = commission_qs.filter(created_at__date__lte=dt)

        comm_stats = commission_qs.aggregate(
            recorded_commission=Sum("commission_amount"),
            calculated_clinic_share=Sum("clinic_share"),
        )

        gross_vol = Decimal(str(payment_stats["gross_volume"] or "0.00"))
        comm_rec = Decimal(str(comm_stats["recorded_commission"] or "0.00"))
        clinic_share = Decimal(str(comm_stats["calculated_clinic_share"] or "0.00"))
        default_comm_rate = PlatformSetting.get_default_commission_rate()

        return Response(
            {
                "success": True,
                "data": {
                    "clinics": {
                        "total": clinic_stats["total"] or 0,
                        "approved": clinic_stats["approved"] or 0,
                        "pending": clinic_stats["pending"] or 0,
                        "rejected": clinic_stats["rejected"] or 0,
                        "suspended": clinic_stats["suspended"] or 0,
                    },
                    "doctors": {
                        "total": doctor_stats["total"] or 0,
                        "verified": doctor_stats["verified"] or 0,
                        "pending": doctor_stats["pending"] or 0,
                        "suspended": doctor_stats["suspended"] or 0,
                        "rejected": doctor_stats["rejected"] or 0,
                    },
                    "users": {
                        "total_patients": total_patients,
                        "total_users": total_users,
                    },
                    "appointments": {
                        "total": appt_stats["total"] or 0,
                        "today": appointments_today_count,
                        "upcoming": upcoming_count,
                        "completed": appt_stats["completed"] or 0,
                        "cancelled": appt_stats["cancelled"] or 0,
                        "confirmed": appt_stats["confirmed"] or 0,
                        "reschedule_required": appt_stats["reschedule_required"] or 0,
                    },
                    "finance": {
                        "successful_payments": payment_stats["successful_payments"] or 0,
                        "failed_payments": payment_stats["failed_payments"] or 0,
                        "gross_volume": f"{gross_vol:.2f}",
                        "recorded_commission": f"{comm_rec:.2f}",
                        "calculated_clinic_share": f"{clinic_share:.2f}",
                        "default_commission_rate": f"{Decimal(str(default_comm_rate)):.2f}",
                        "actual_payouts": "0.00",
                        "payout_disclaimer": "No automatic bank payouts disbursed; gateway settlement module inactive.",
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class AdminAppointmentsTrendView(APIView):
    """
    Super Admin endpoint returning daily appointment volume trends.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Appointments Volume Trend",
        description="Daily aggregated counts of appointments over recent days.",
        responses={200: list},
    )
    def get(self, request):
        days = int(request.query_params.get("days", 14))
        days = min(max(days, 3), 90)

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        clinic_id = request.query_params.get("clinic_id")

        qs = Appointment.objects.filter(start_at__date__gte=start_date, start_at__date__lte=end_date)
        if clinic_id:
            qs = qs.filter(clinic_id=clinic_id)

        # Aggregate counts grouped by start_at__date
        aggregates = (
            qs.values("start_at__date")
            .annotate(
                total=Count("id"),
                confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
                completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
                cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
            )
            .order_by("start_at__date")
        )

        agg_map = {row["start_at__date"]: row for row in aggregates}

        trend = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            row = agg_map.get(d)
            trend.append(
                {
                    "date": d.isoformat(),
                    "total": row["total"] if row else 0,
                    "confirmed": row["confirmed"] if row else 0,
                    "completed": row["completed"] if row else 0,
                    "cancelled": row["cancelled"] if row else 0,
                }
            )

        return Response({"success": True, "data": trend}, status=status.HTTP_200_OK)


class AdminFinancialSummaryView(APIView):
    """
    Super Admin endpoint returning financial aggregations and daily revenue/commission trends.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Admin Financial Summary and Trends",
        description="Aggregated revenue, recorded commission, and daily financial volume trends.",
        responses={200: dict},
    )
    def get(self, request):
        days = int(request.query_params.get("days", 14))
        days = min(max(days, 3), 90)

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        clinic_id = request.query_params.get("clinic_id")

        p_qs = Payment.objects.all()
        if clinic_id:
            p_qs = p_qs.filter(clinic_id=clinic_id)

        # Aggregate total revenue & failures
        overall = p_qs.aggregate(
            gross_volume=Sum("amount", filter=Q(status=PaymentStatus.PAID)),
            failed_volume=Sum("amount", filter=Q(status=PaymentStatus.FAILED)),
            paid_count=Count("id", filter=Q(status=PaymentStatus.PAID)),
            failed_count=Count("id", filter=Q(status=PaymentStatus.FAILED)),
        )

        c_qs = CommissionRecord.objects.all()
        if clinic_id:
            c_qs = c_qs.filter(clinic_id=clinic_id)

        comm_overall = c_qs.aggregate(
            recorded_commission=Sum("commission_amount"),
            calculated_clinic_share=Sum("clinic_share"),
        )

        # Daily trends
        daily_payments = (
            p_qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
            .values("created_at__date")
            .annotate(
                gross=Sum("amount", filter=Q(status=PaymentStatus.PAID)),
                successful=Count("id", filter=Q(status=PaymentStatus.PAID)),
                failed=Count("id", filter=Q(status=PaymentStatus.FAILED)),
            )
            .order_by("created_at__date")
        )

        daily_commissions = (
            c_qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
            .values("created_at__date")
            .annotate(
                commission=Sum("commission_amount"),
                clinic_share=Sum("clinic_share"),
            )
            .order_by("created_at__date")
        )

        pay_map = {row["created_at__date"]: row for row in daily_payments}
        comm_map = {row["created_at__date"]: row for row in daily_commissions}

        daily_trend = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            p_row = pay_map.get(d)
            c_row = comm_map.get(d)

            daily_trend.append(
                {
                    "date": d.isoformat(),
                    "gross_volume": str(p_row["gross"] or Decimal("0.00")) if p_row else "0.00",
                    "commission_recorded": str(c_row["commission"] or Decimal("0.00")) if c_row else "0.00",
                    "clinic_share": str(c_row["clinic_share"] or Decimal("0.00")) if c_row else "0.00",
                    "successful_count": p_row["successful"] if p_row else 0,
                    "failed_count": p_row["failed"] if p_row else 0,
                }
            )

        gross_vol = Decimal(str(overall["gross_volume"] or "0.00"))
        failed_vol = Decimal(str(overall["failed_volume"] or "0.00"))
        comm_rec = Decimal(str(comm_overall["recorded_commission"] or "0.00"))
        clinic_share = Decimal(str(comm_overall["calculated_clinic_share"] or "0.00"))

        return Response(
            {
                "success": True,
                "data": {
                    "totals": {
                        "gross_successful_payments": f"{gross_vol:.2f}",
                        "recorded_commission": f"{comm_rec:.2f}",
                        "calculated_clinic_share": f"{clinic_share:.2f}",
                        "failed_payments_volume": f"{failed_vol:.2f}",
                        "successful_payments_count": overall["paid_count"] or 0,
                        "failed_payments_count": overall["failed_count"] or 0,
                        "actual_refunds": "0.00",
                        "actual_payouts": "0.00",
                    },
                    "daily_trend": daily_trend,
                },
            },
            status=status.HTTP_200_OK,
        )
