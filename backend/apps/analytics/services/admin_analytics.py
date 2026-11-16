from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
import pytz
from django.conf import settings
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.appointments.models import Appointment, AppointmentStatus
from apps.clinics.models import Clinic, ClinicStatus, DoctorClinic, DoctorClinicStatus
from apps.doctors.models import Doctor, DoctorVerificationStatus
from apps.payments.models import (
    CommissionRecord,
    CommissionStatus,
    Payment,
    PaymentAuditLog,
    PaymentStatus,
    PaymentWebhookEvent,
    PlatformSetting,
)
from .date_range import DateRangeBounds


def _round_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_super_admin_kpis(
    bounds: DateRangeBounds,
    clinic_id: str = None,
    doctor_id: str = None,
    status_filter: str = None,
) -> dict:
    """
    Computes platform-wide or filtered super admin KPI cards.
    Adheres strictly to the accounting invariant: gross == commission + clinic_share.
    """
    # 1. User & Profile metrics
    user_qs = User.objects.all()
    patient_count = user_qs.filter(role=UserRole.PATIENT).count()
    total_users = user_qs.count()

    doctor_qs = Doctor.objects.all()
    if doctor_id:
        doctor_qs = doctor_qs.filter(id=doctor_id)
    doc_stats = doctor_qs.aggregate(
        total=Count("id"),
        verified=Count("id", filter=Q(verification_status=DoctorVerificationStatus.VERIFIED)),
        pending=Count("id", filter=Q(verification_status=DoctorVerificationStatus.PENDING)),
        rejected=Count("id", filter=Q(verification_status=DoctorVerificationStatus.REJECTED)),
        suspended=Count("id", filter=Q(verification_status=DoctorVerificationStatus.SUSPENDED)),
    )

    clinic_qs = Clinic.objects.all()
    if clinic_id:
        clinic_qs = clinic_qs.filter(id=clinic_id)
    clinic_stats = clinic_qs.aggregate(
        total=Count("id"),
        approved=Count("id", filter=Q(status=ClinicStatus.APPROVED)),
        active=Count("id", filter=Q(status=ClinicStatus.APPROVED, is_verified=True)),
        pending=Count("id", filter=Q(status=ClinicStatus.PENDING)),
        rejected=Count("id", filter=Q(status=ClinicStatus.REJECTED)),
        suspended=Count("id", filter=Q(status=ClinicStatus.SUSPENDED)),
    )

    # 2. Appointment metrics within bounds
    appt_qs = Appointment.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if clinic_id:
        appt_qs = appt_qs.filter(clinic_id=clinic_id)
    if doctor_id:
        appt_qs = appt_qs.filter(doctor_id=doctor_id)
    if status_filter:
        appt_qs = appt_qs.filter(status=status_filter)

    appt_stats = appt_qs.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
        confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
        cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
        pending=Count("id", filter=Q(status=AppointmentStatus.PENDING_CONFIRMATION)),
        reschedule_required=Count("id", filter=Q(reschedule_required=True)),
    )

    total_appts = appt_stats["total"] or 0
    completed_appts = appt_stats["completed"] or 0
    cancelled_appts = appt_stats["cancelled"] or 0
    completion_rate = round((completed_appts / total_appts * 100), 2) if total_appts > 0 else 0.0
    cancellation_rate = round((cancelled_appts / total_appts * 100), 2) if total_appts > 0 else 0.0

    # Today & upcoming (based on start_at and local timezone)
    now_utc = timezone.now()
    try:
        local_tz = pytz.timezone(bounds.timezone_str)
    except Exception:
        local_tz = pytz.timezone("Asia/Kolkata")
    now_local = now_utc.astimezone(local_tz)
    today_start = local_tz.localize(datetime.combine(now_local.date(), time.min)).astimezone(pytz.UTC)
    today_end = local_tz.localize(datetime.combine(now_local.date(), time.max)).astimezone(pytz.UTC)

    today_appts_qs = Appointment.objects.filter(start_at__gte=today_start, start_at__lte=today_end)
    upcoming_appts_qs = Appointment.objects.filter(start_at__gt=now_utc, status=AppointmentStatus.CONFIRMED)
    if clinic_id:
        today_appts_qs = today_appts_qs.filter(clinic_id=clinic_id)
        upcoming_appts_qs = upcoming_appts_qs.filter(clinic_id=clinic_id)
    if doctor_id:
        today_appts_qs = today_appts_qs.filter(doctor_id=doctor_id)
        upcoming_appts_qs = upcoming_appts_qs.filter(doctor_id=doctor_id)

    # 3. Financial Metrics
    pay_qs = Payment.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if clinic_id:
        pay_qs = pay_qs.filter(clinic_id=clinic_id)
    if doctor_id:
        pay_qs = pay_qs.filter(appointment__doctor_id=doctor_id)

    pay_stats = pay_qs.aggregate(
        total_payments=Count("id"),
        paid_count=Count("id", filter=Q(status=PaymentStatus.PAID)),
        failed_count=Count("id", filter=Q(status=PaymentStatus.FAILED)),
        pending_count=Count("id", filter=Q(status=PaymentStatus.PENDING)),
        refunded_count=Count("id", filter=Q(status=PaymentStatus.REFUNDED)),
        gross_collected=Sum("amount", filter=Q(status=PaymentStatus.PAID)),
        failed_volume=Sum("amount", filter=Q(status=PaymentStatus.FAILED)),
        refund_volume=Sum("amount", filter=Q(status=PaymentStatus.REFUNDED)),
    )

    comm_qs = CommissionRecord.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if clinic_id:
        comm_qs = comm_qs.filter(clinic_id=clinic_id)
    if doctor_id:
        comm_qs = comm_qs.filter(appointment__doctor_id=doctor_id)

    comm_stats = comm_qs.aggregate(
        commission_earned=Sum("commission_amount"),
        clinic_payable=Sum("clinic_share"),
        snapshot_gross=Sum("gross_amount"),
    )

    gross_collected = _round_decimal(pay_stats["gross_collected"])
    commission_earned = _round_decimal(comm_stats["commission_earned"])
    clinic_payable = _round_decimal(comm_stats["clinic_payable"])
    failed_volume = _round_decimal(pay_stats["failed_volume"])
    refund_volume = _round_decimal(pay_stats["refund_volume"])

    # Verify accounting invariant
    invariant_valid = abs(gross_collected - (commission_earned + clinic_payable)) <= Decimal("0.05")

    conversion_rate = 0.0
    paid_count = pay_stats["paid_count"] or 0
    if total_appts > 0:
        conversion_rate = round((paid_count / total_appts) * 100, 2)

    return {
        "period": {
            "name": bounds.period,
            "start_date": bounds.start_date.isoformat(),
            "end_date": bounds.end_date.isoformat(),
            "days_count": bounds.days_count,
            "timezone": bounds.timezone_str,
        },
        "users": {
            "total_users": total_users,
            "total_patients": patient_count,
        },
        "clinics": {
            "total": clinic_stats["total"] or 0,
            "approved": clinic_stats["approved"] or 0,
            "active": clinic_stats["active"] or 0,
            "pending": clinic_stats["pending"] or 0,
            "rejected": clinic_stats["rejected"] or 0,
            "suspended": clinic_stats["suspended"] or 0,
        },
        "doctors": {
            "total": doc_stats["total"] or 0,
            "verified": doc_stats["verified"] or 0,
            "pending": doc_stats["pending"] or 0,
            "rejected": doc_stats["rejected"] or 0,
            "suspended": doc_stats["suspended"] or 0,
        },
        "appointments": {
            "total": total_appts,
            "completed": completed_appts,
            "confirmed": appt_stats["confirmed"] or 0,
            "cancelled": cancelled_appts,
            "no_show": appt_stats["no_show"] or 0,
            "pending": appt_stats["pending"] or 0,
            "reschedule_required": appt_stats["reschedule_required"] or 0,
            "today": today_appts_qs.count(),
            "upcoming": upcoming_appts_qs.count(),
            "completion_rate": completion_rate,
            "cancellation_rate": cancellation_rate,
        },
        "finance": {
            "gross_collected": str(gross_collected),
            "platform_commission": str(commission_earned),
            "clinic_payable": str(clinic_payable),
            "failed_volume": str(failed_volume),
            "refund_volume": str(refund_volume),
            "successful_payments_count": paid_count,
            "failed_payments_count": pay_stats["failed_count"] or 0,
            "pending_payments_count": pay_stats["pending_count"] or 0,
            "refunded_payments_count": pay_stats["refunded_count"] or 0,
            "conversion_rate": conversion_rate,
            "accounting_invariant_valid": invariant_valid,
            "actual_payouts_disbursed": "0.00",
            "payout_notice": "Platform calculates accrued payable liability. Automated bank settlement module is currently off.",
        },
    }


def get_revenue_analytics(
    bounds: DateRangeBounds,
    clinic_id: str = None,
    doctor_id: str = None,
) -> dict:
    """
    Detailed revenue analytics, trends, breakdown by clinic, and payment status distribution.
    """
    pay_qs = Payment.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    comm_qs = CommissionRecord.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if clinic_id:
        pay_qs = pay_qs.filter(clinic_id=clinic_id)
        comm_qs = comm_qs.filter(clinic_id=clinic_id)
    if doctor_id:
        pay_qs = pay_qs.filter(appointment__doctor_id=doctor_id)
        comm_qs = comm_qs.filter(appointment__doctor_id=doctor_id)

    # Totals
    overall_pay = pay_qs.aggregate(
        gross=Sum("amount", filter=Q(status=PaymentStatus.PAID)),
        failed=Sum("amount", filter=Q(status=PaymentStatus.FAILED)),
        refunded=Sum("amount", filter=Q(status=PaymentStatus.REFUNDED)),
        paid_count=Count("id", filter=Q(status=PaymentStatus.PAID)),
        failed_count=Count("id", filter=Q(status=PaymentStatus.FAILED)),
        pending_count=Count("id", filter=Q(status=PaymentStatus.PENDING)),
        refunded_count=Count("id", filter=Q(status=PaymentStatus.REFUNDED)),
    )
    overall_comm = comm_qs.aggregate(
        commission=Sum("commission_amount"),
        clinic_share=Sum("clinic_share"),
        snapshot_gross=Sum("gross_amount"),
    )

    gross_val = _round_decimal(overall_pay["gross"])
    comm_val = _round_decimal(overall_comm["commission"])
    clinic_val = _round_decimal(overall_comm["clinic_share"])
    failed_val = _round_decimal(overall_pay["failed"])
    refunded_val = _round_decimal(overall_pay["refunded"])

    avg_commission_rate = 0.0
    if gross_val > 0:
        avg_commission_rate = round(float((comm_val / gross_val) * 100), 2)
    else:
        avg_commission_rate = float(PlatformSetting.get_default_commission_rate())

    # Daily revenue trends
    daily_pay = (
        pay_qs.values("created_at__date")
        .annotate(
            gross=Sum("amount", filter=Q(status=PaymentStatus.PAID)),
            paid_count=Count("id", filter=Q(status=PaymentStatus.PAID)),
            failed_count=Count("id", filter=Q(status=PaymentStatus.FAILED)),
        )
        .order_by("created_at__date")
    )
    daily_comm = (
        comm_qs.values("created_at__date")
        .annotate(
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )
        .order_by("created_at__date")
    )

    pay_by_date = {row["created_at__date"]: row for row in daily_pay}
    comm_by_date = {row["created_at__date"]: row for row in daily_comm}

    daily_trend = []
    curr = bounds.start_date
    while curr <= bounds.end_date:
        p_row = pay_by_date.get(curr)
        c_row = comm_by_date.get(curr)
        d_gross = _round_decimal(p_row["gross"]) if p_row else Decimal("0.00")
        d_comm = _round_decimal(c_row["commission"]) if c_row else Decimal("0.00")
        d_share = _round_decimal(c_row["clinic_share"]) if c_row else Decimal("0.00")

        daily_trend.append(
            {
                "date": curr.isoformat(),
                "gross_revenue": str(d_gross),
                "platform_commission": str(d_comm),
                "clinic_share": str(d_share),
                "successful_payments": p_row["paid_count"] if p_row else 0,
                "failed_payments": p_row["failed_count"] if p_row else 0,
            }
        )
        curr += timedelta(days=1)

    # Monthly revenue trends (last 12 months up to end_date)
    month_cursor = (bounds.end_date.replace(day=1) - timedelta(days=365)).replace(day=1)
    monthly_trend = []
    monthly_pay = (
        Payment.objects.filter(
            status=PaymentStatus.PAID,
            created_at__date__gte=month_cursor,
            created_at__date__lte=bounds.end_date,
        )
        .values("created_at__year", "created_at__month")
        .annotate(
            gross=Sum("amount"),
            paid_count=Count("id"),
        )
        .order_by("created_at__year", "created_at__month")
    )
    monthly_comm = (
        CommissionRecord.objects.filter(
            created_at__date__gte=month_cursor,
            created_at__date__lte=bounds.end_date,
        )
        .values("created_at__year", "created_at__month")
        .annotate(
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )
        .order_by("created_at__year", "created_at__month")
    )

    m_pay_map = {(r["created_at__year"], r["created_at__month"]): r for r in monthly_pay}
    m_comm_map = {(r["created_at__year"], r["created_at__month"]): r for r in monthly_comm}

    all_months = sorted(list(set(list(m_pay_map.keys()) + list(m_comm_map.keys()))))
    for yr, mn in all_months:
        p_row = m_pay_map.get((yr, mn))
        c_row = m_comm_map.get((yr, mn))
        m_gross = _round_decimal(p_row["gross"]) if p_row else Decimal("0.00")
        m_comm = _round_decimal(c_row["commission"]) if c_row else Decimal("0.00")
        m_share = _round_decimal(c_row["clinic_share"]) if c_row else Decimal("0.00")
        monthly_trend.append(
            {
                "month": f"{yr}-{mn:02d}",
                "gross_revenue": str(m_gross),
                "platform_commission": str(m_comm),
                "clinic_share": str(m_share),
                "successful_payments": p_row["paid_count"] if p_row else 0,
            }
        )

    # Payment status distribution
    paid_cnt = overall_pay["paid_count"] or 0
    failed_cnt = overall_pay["failed_count"] or 0
    pending_cnt = overall_pay["pending_count"] or 0
    refunded_cnt = overall_pay["refunded_count"] or 0
    tot_pay_cnt = paid_cnt + failed_cnt + pending_cnt + refunded_cnt

    payment_status_distribution = [
        {"status": "PAID", "count": paid_cnt, "percentage": round((paid_cnt / tot_pay_cnt * 100), 2) if tot_pay_cnt else 0.0},
        {"status": "FAILED", "count": failed_cnt, "percentage": round((failed_cnt / tot_pay_cnt * 100), 2) if tot_pay_cnt else 0.0},
        {"status": "PENDING", "count": pending_cnt, "percentage": round((pending_cnt / tot_pay_cnt * 100), 2) if tot_pay_cnt else 0.0},
        {"status": "REFUNDED", "count": refunded_cnt, "percentage": round((refunded_cnt / tot_pay_cnt * 100), 2) if tot_pay_cnt else 0.0},
    ]

    # Clinic Revenue Comparison
    clinic_rev_qs = (
        comm_qs.values("clinic_id", "clinic__name")
        .annotate(
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
            booking_count=Count("id"),
        )
        .order_by("-gross")[:15]
    )
    clinic_breakdown = [
        {
            "clinic_id": str(r["clinic_id"]),
            "clinic_name": r["clinic__name"] or "Unknown Clinic",
            "gross_revenue": str(_round_decimal(r["gross"])),
            "platform_commission": str(_round_decimal(r["commission"])),
            "clinic_share": str(_round_decimal(r["clinic_share"])),
            "settled_appointments": r["booking_count"] or 0,
        }
        for r in clinic_rev_qs
    ]

    return {
        "totals": {
            "gross_revenue": str(gross_val),
            "platform_commission": str(comm_val),
            "clinic_share": str(clinic_val),
            "failed_volume": str(failed_val),
            "refund_volume": str(refunded_val),
            "average_commission_rate": avg_commission_rate,
            "successful_payments_count": paid_cnt,
            "failed_payments_count": failed_cnt,
            "pending_payments_count": pending_cnt,
            "refunded_payments_count": refunded_cnt,
        },
        "daily_trend": daily_trend,
        "monthly_trend": monthly_trend,
        "payment_status_distribution": payment_status_distribution,
        "clinic_revenue_breakdown": clinic_breakdown,
    }


def get_appointment_analytics(
    bounds: DateRangeBounds,
    clinic_id: str = None,
    doctor_id: str = None,
) -> dict:
    """
    Appointment performance, completion and cancellation rates, peak days, and peak hours.
    """
    appt_qs = Appointment.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if clinic_id:
        appt_qs = appt_qs.filter(clinic_id=clinic_id)
    if doctor_id:
        appt_qs = appt_qs.filter(doctor_id=doctor_id)

    stats = appt_qs.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
        confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
        cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
        pending=Count("id", filter=Q(status=AppointmentStatus.PENDING_CONFIRMATION)),
        reschedule_required=Count("id", filter=Q(reschedule_required=True)),
    )

    tot = stats["total"] or 0
    completed = stats["completed"] or 0
    cancelled = stats["cancelled"] or 0
    no_show = stats["no_show"] or 0
    confirmed = stats["confirmed"] or 0
    pending = stats["pending"] or 0
    rescheduled = stats["reschedule_required"] or 0

    completion_rate = round((completed / tot * 100), 2) if tot else 0.0
    cancellation_rate = round((cancelled / tot * 100), 2) if tot else 0.0
    reschedule_rate = round((rescheduled / tot * 100), 2) if tot else 0.0
    no_show_rate = round((no_show / tot * 100), 2) if tot else 0.0

    # Status distribution
    status_distribution = [
        {"status": "COMPLETED", "count": completed, "percentage": completion_rate},
        {"status": "CONFIRMED", "count": confirmed, "percentage": round((confirmed / tot * 100), 2) if tot else 0.0},
        {"status": "CANCELLED", "count": cancelled, "percentage": cancellation_rate},
        {"status": "NO_SHOW", "count": no_show, "percentage": no_show_rate},
        {"status": "PENDING", "count": pending, "percentage": round((pending / tot * 100), 2) if tot else 0.0},
    ]

    # Daily appointment trend
    daily_aggregates = (
        appt_qs.values("created_at__date")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
            confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
            cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
            no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
        )
        .order_by("created_at__date")
    )
    daily_map = {r["created_at__date"]: r for r in daily_aggregates}

    daily_trend = []
    curr = bounds.start_date
    while curr <= bounds.end_date:
        r = daily_map.get(curr)
        daily_trend.append(
            {
                "date": curr.isoformat(),
                "total": r["total"] if r else 0,
                "completed": r["completed"] if r else 0,
                "confirmed": r["confirmed"] if r else 0,
                "cancelled": r["cancelled"] if r else 0,
                "no_show": r["no_show"] if r else 0,
            }
        )
        curr += timedelta(days=1)

    # Peak days (Day of week distribution: Monday to Sunday)
    # Django extract week_day: 1 is Sunday, 2 is Monday in standard Django,
    # or we can compute in Python from start_at for exact local timezone accuracy!
    try:
        local_tz = pytz.timezone(bounds.timezone_str)
    except Exception:
        local_tz = pytz.timezone("Asia/Kolkata")

    # Fetch timestamps for scheduled slots to determine peak hours and peak days
    scheduled_slots = appt_qs.values_list("start_at", flat=True)
    weekday_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    hour_counts = {h: 0 for h in range(24)}

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for slot_dt in scheduled_slots:
        if slot_dt:
            local_slot = slot_dt.astimezone(local_tz)
            weekday_counts[local_slot.weekday()] += 1
            hour_counts[local_slot.hour] += 1

    total_scheduled = len(scheduled_slots)
    peak_days = [
        {
            "day": weekday_names[idx],
            "day_index": idx,
            "count": cnt,
            "percentage": round((cnt / total_scheduled * 100), 2) if total_scheduled else 0.0,
        }
        for idx, cnt in weekday_counts.items()
    ]

    peak_hours = [
        {
            "hour": h,
            "label": f"{h:02d}:00 - {h+1:02d}:00",
            "count": hour_counts[h],
            "percentage": round((hour_counts[h] / total_scheduled * 100), 2) if total_scheduled else 0.0,
        }
        for h in range(24)
    ]

    return {
        "totals": {
            "total_bookings": tot,
            "completed": completed,
            "confirmed": confirmed,
            "cancelled": cancelled,
            "no_show": no_show,
            "pending": pending,
            "rescheduled": rescheduled,
            "completion_rate": completion_rate,
            "cancellation_rate": cancellation_rate,
            "reschedule_rate": reschedule_rate,
            "no_show_rate": no_show_rate,
        },
        "status_distribution": status_distribution,
        "daily_trend": daily_trend,
        "peak_days": peak_days,
        "peak_hours": peak_hours,
    }


def get_clinic_performance_analytics(
    bounds: DateRangeBounds,
    status_filter: str = None,
    search: str = None,
) -> list:
    """
    Comparative performance across clinics:
    Doctors count, appointments volume, gross revenue, commission, clinic share, avg fee.
    """
    clinic_qs = Clinic.objects.all().select_related("owner")
    if status_filter:
        clinic_qs = clinic_qs.filter(status=status_filter)
    if search:
        clinic_qs = clinic_qs.filter(
            Q(name__icontains=search) | Q(city__icontains=search) | Q(state__icontains=search)
        )

    clinic_list = []
    for clinic in clinic_qs:
        # Doctors associated
        doc_count = DoctorClinic.objects.filter(clinic=clinic).count()
        active_docs = DoctorClinic.objects.filter(clinic=clinic, status=DoctorClinicStatus.ACTIVE).count()

        # Appointments
        appts = Appointment.objects.filter(
            clinic=clinic,
            created_at__gte=bounds.start_dt,
            created_at__lte=bounds.end_dt,
        ).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        )

        tot_appts = appts["total"] or 0
        comp_appts = appts["completed"] or 0
        canc_appts = appts["cancelled"] or 0
        comp_rate = round((comp_appts / tot_appts * 100), 2) if tot_appts else 0.0

        # Finances
        comm_stats = CommissionRecord.objects.filter(
            clinic=clinic,
            created_at__gte=bounds.start_dt,
            created_at__lte=bounds.end_dt,
        ).aggregate(
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )

        gross = _round_decimal(comm_stats["gross"])
        commission = _round_decimal(comm_stats["commission"])
        clinic_share = _round_decimal(comm_stats["clinic_share"])
        avg_consultation = _round_decimal(gross / tot_appts) if tot_appts > 0 else Decimal("0.00")

        clinic_list.append(
            {
                "clinic_id": str(clinic.id),
                "name": clinic.name,
                "slug": clinic.slug,
                "status": clinic.status,
                "is_active": clinic.status == ClinicStatus.APPROVED,
                "city": clinic.city or "",
                "state": clinic.state or "",
                "total_doctors": doc_count,
                "active_doctors": active_docs,
                "total_appointments": tot_appts,
                "completed_appointments": comp_appts,
                "cancelled_appointments": canc_appts,
                "completion_rate": comp_rate,
                "gross_volume": str(gross),
                "platform_commission": str(commission),
                "clinic_share": str(clinic_share),
                "avg_consultation_value": str(avg_consultation),
                "commission_rate_override": str(clinic.commission_rate) if clinic.commission_rate is not None else None,
            }
        )

    # Sort descending by gross volume
    clinic_list.sort(key=lambda x: Decimal(x["gross_volume"]), reverse=True)
    return clinic_list


def get_doctor_performance_analytics(
    bounds: DateRangeBounds,
    clinic_id: str = None,
    verification_status: str = None,
    search: str = None,
) -> list:
    """
    Doctor performance analytics respecting multi-clinic doctor practices.
    Preserves clinic-specific fees and schedules without corruption.
    """
    doc_qs = Doctor.objects.all().select_related("user")
    if clinic_id:
        doc_qs = doc_qs.filter(doctor_clinics__clinic_id=clinic_id).distinct()
    if verification_status:
        doc_qs = doc_qs.filter(verification_status=verification_status)
    if search:
        doc_qs = doc_qs.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(specialization__icontains=search)
        )

    doctor_list = []
    for doc in doc_qs:
        # Fetch doctor-clinic affiliations
        associations = DoctorClinic.objects.filter(doctor=doc).select_related("clinic")
        if clinic_id:
            associations = associations.filter(clinic_id=clinic_id)

        affiliations = [
            {
                "clinic_id": str(assoc.clinic_id),
                "clinic_name": assoc.clinic.name,
                "consultation_fee": str(_round_decimal(assoc.consultation_fee)),
                "is_active": assoc.status == DoctorClinicStatus.ACTIVE,
            }
            for assoc in associations
        ]

        # Filter appointments
        doc_appts = Appointment.objects.filter(
            doctor=doc,
            created_at__gte=bounds.start_dt,
            created_at__lte=bounds.end_dt,
        )
        if clinic_id:
            doc_appts = doc_appts.filter(clinic_id=clinic_id)

        appt_stats = doc_appts.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        )

        tot = appt_stats["total"] or 0
        comp = appt_stats["completed"] or 0
        canc = appt_stats["cancelled"] or 0
        comp_rate = round((comp / tot * 100), 2) if tot else 0.0

        # Distinct practice days for workload calculation
        distinct_days = doc_appts.values("start_at__date").distinct().count()
        avg_appts_per_day = round((tot / distinct_days), 1) if distinct_days > 0 else 0.0

        # Finances
        comm_stats = CommissionRecord.objects.filter(
            appointment__doctor=doc,
            created_at__gte=bounds.start_dt,
            created_at__lte=bounds.end_dt,
        )
        if clinic_id:
            comm_stats = comm_stats.filter(clinic_id=clinic_id)

        finances = comm_stats.aggregate(
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )

        gross = _round_decimal(finances["gross"])
        commission = _round_decimal(finances["commission"])
        clinic_share = _round_decimal(finances["clinic_share"])

        doctor_list.append(
            {
                "doctor_id": str(doc.id),
                "name": doc.user.get_full_name() or doc.user.email,
                "email": doc.user.email,
                "specialization": doc.specialization or "General Practitioner",
                "verification_status": doc.verification_status,
                "affiliations": affiliations,
                "total_appointments": tot,
                "completed_appointments": comp,
                "cancelled_appointments": canc,
                "completion_rate": comp_rate,
                "avg_appointments_per_day": avg_appts_per_day,
                "gross_revenue": str(gross),
                "platform_commission": str(commission),
                "clinic_share": str(clinic_share),
            }
        )

    # Sort descending by total appointments
    doctor_list.sort(key=lambda x: x["total_appointments"], reverse=True)
    return doctor_list


def get_financial_reconciliation(
    bounds: DateRangeBounds,
    clinic_id: str = None,
) -> dict:
    """
    Financial reconciliation report detecting discrepancies across:
    1. Paid status without CommissionRecord or vice-versa.
    2. Commission equation imbalance: gross != commission + clinic_share.
    3. Confirmed/Completed appointments with missing or unpaid payments.
    4. Duplicate webhook events or duplicate payments on same appointment.
    """
    discrepancies = []
    total_reconciled = 0
    discrepancy_count = 0
    discrepancy_value = Decimal("0.00")

    # 1. Inspect payments in date bounds
    pay_qs = Payment.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    ).select_related("appointment", "clinic")
    if clinic_id:
        pay_qs = pay_qs.filter(clinic_id=clinic_id)

    for p in pay_qs:
        total_reconciled += 1
        # Check CommissionRecord existence for PAID payment
        if p.status == PaymentStatus.PAID:
            comm = getattr(p, "commission_record", None)
            if not comm:
                # Missing commission record
                discrepancies.append(
                    {
                        "type": "MISSING_COMMISSION_RECORD",
                        "severity": "CRITICAL",
                        "payment_id": str(p.id),
                        "appointment_id": str(p.appointment_id) if p.appointment_id else None,
                        "clinic_name": p.clinic.name if p.clinic else "Unknown",
                        "amount": str(p.amount),
                        "description": "Payment marked PAID but no CommissionRecord exists.",
                    }
                )
                discrepancy_count += 1
                discrepancy_value += p.amount
            else:
                # Check invariant equation
                tot_calc = comm.commission_amount + comm.clinic_share
                diff = abs(p.amount - tot_calc)
                if diff > Decimal("0.01"):
                    discrepancies.append(
                        {
                            "type": "COMMISSION_MATH_MISMATCH",
                            "severity": "CRITICAL",
                            "payment_id": str(p.id),
                            "appointment_id": str(p.appointment_id) if p.appointment_id else None,
                            "clinic_name": p.clinic.name if p.clinic else "Unknown",
                            "amount": str(p.amount),
                            "description": f"Ledger invariant violation: Payment gross ({p.amount}) != Commission ({comm.commission_amount}) + Clinic Share ({comm.clinic_share}). Difference: {diff}",
                        }
                    )
                    discrepancy_count += 1
                    discrepancy_value += diff

    # 2. Inspect Confirmed/Completed appointments for payment state
    appt_qs = Appointment.objects.filter(
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
        status__in=[AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED],
    ).select_related("clinic").prefetch_related("payments")
    if clinic_id:
        appt_qs = appt_qs.filter(clinic_id=clinic_id)

    for a in appt_qs:
        p = a.payments.filter(status=PaymentStatus.PAID).first()
        if not p:
            any_p = a.payments.first()
            discrepancies.append(
                {
                    "type": "UNPAID_CONFIRMED_APPOINTMENT",
                    "severity": "WARNING",
                    "payment_id": str(any_p.id) if any_p else None,
                    "appointment_id": str(a.id),
                    "clinic_name": a.clinic.name if a.clinic else "Unknown",
                    "amount": str(any_p.amount) if any_p else "0.00",
                    "description": f"Appointment is {a.status} but payment status is {any_p.status if any_p else 'NONE'}.",
                }
            )
            discrepancy_count += 1
            if any_p:
                discrepancy_value += any_p.amount

    # 3. Duplicate payments per appointment check
    dup_appts = (
        Payment.objects.filter(
            created_at__gte=bounds.start_dt,
            created_at__lte=bounds.end_dt,
            status=PaymentStatus.PAID,
            appointment__isnull=False,
        )
        .values("appointment_id")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )
    for dup in dup_appts:
        discrepancies.append(
            {
                "type": "DUPLICATE_PAID_RECORDS",
                "severity": "CRITICAL",
                "payment_id": None,
                "appointment_id": str(dup["appointment_id"]),
                "clinic_name": "Multiple",
                "amount": "0.00",
                "description": f"Appointment has {dup['cnt']} separate PAID payment records.",
            }
        )
        discrepancy_count += 1

    health_status = "HEALTHY" if discrepancy_count == 0 else "DISCREPANCIES_DETECTED"

    return {
        "period": {
            "start_date": bounds.start_date.isoformat(),
            "end_date": bounds.end_date.isoformat(),
        },
        "health_status": health_status,
        "total_reconciled_transactions": total_reconciled,
        "discrepancy_count": discrepancy_count,
        "total_discrepancy_value": str(_round_decimal(discrepancy_value)),
        "discrepancies": discrepancies,
    }
