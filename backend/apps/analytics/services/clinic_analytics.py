from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
import pytz
from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.appointments.models import Appointment, AppointmentStatus
from apps.clinics.models import Clinic, DoctorClinic, DoctorClinicStatus
from apps.payments.models import CommissionRecord, Payment, PaymentStatus
from .date_range import DateRangeBounds


def _round_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_clinic_overview_analytics(
    clinic: Clinic,
    bounds: DateRangeBounds,
    doctor_id: str = None,
) -> dict:
    """
    Computes tenant-isolated clinic KPI overview.
    Strictly verifies and enforces clinic scope.
    """
    # 1. Appointment stats
    appt_qs = Appointment.objects.filter(
        clinic=clinic,
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if doctor_id:
        appt_qs = appt_qs.filter(doctor_id=doctor_id)

    appt_stats = appt_qs.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
        confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
        cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
        pending=Count("id", filter=Q(status=AppointmentStatus.PENDING_CONFIRMATION)),
        reschedule_required=Count("id", filter=Q(reschedule_required=True)),
    )

    tot = appt_stats["total"] or 0
    comp = appt_stats["completed"] or 0
    canc = appt_stats["cancelled"] or 0
    conf = appt_stats["confirmed"] or 0
    no_show = appt_stats["no_show"] or 0
    comp_rate = round((comp / tot * 100), 2) if tot else 0.0
    canc_rate = round((canc / tot * 100), 2) if tot else 0.0

    # Today's appointments (in clinic timezone)
    try:
        clinic_tz = pytz.timezone(clinic.timezone or "Asia/Kolkata")
    except Exception:
        clinic_tz = pytz.timezone("Asia/Kolkata")

    now_utc = timezone.now()
    now_local = now_utc.astimezone(clinic_tz)
    today_start = clinic_tz.localize(datetime.combine(now_local.date(), time.min)).astimezone(pytz.UTC)
    today_end = clinic_tz.localize(datetime.combine(now_local.date(), time.max)).astimezone(pytz.UTC)

    today_count = Appointment.objects.filter(
        clinic=clinic,
        start_at__gte=today_start,
        start_at__lte=today_end,
    ).count()

    upcoming_count = Appointment.objects.filter(
        clinic=clinic,
        start_at__gt=now_utc,
        status=AppointmentStatus.CONFIRMED,
    ).count()

    # 2. Financial stats
    comm_qs = CommissionRecord.objects.filter(
        clinic=clinic,
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if doctor_id:
        comm_qs = comm_qs.filter(appointment__doctor_id=doctor_id)

    fin_stats = comm_qs.aggregate(
        gross=Sum("gross_amount"),
        commission=Sum("commission_amount"),
        clinic_share=Sum("clinic_share"),
    )

    pay_qs = Payment.objects.filter(
        clinic=clinic,
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if doctor_id:
        pay_qs = pay_qs.filter(appointment__doctor_id=doctor_id)

    pay_stats = pay_qs.aggregate(
        paid_count=Count("id", filter=Q(status=PaymentStatus.PAID)),
        failed_count=Count("id", filter=Q(status=PaymentStatus.FAILED)),
        refund_amount=Sum("amount", filter=Q(status=PaymentStatus.REFUNDED)),
    )

    gross = _round_decimal(fin_stats["gross"])
    commission = _round_decimal(fin_stats["commission"])
    clinic_share = _round_decimal(fin_stats["clinic_share"])
    refunds = _round_decimal(pay_stats["refund_amount"])

    # Active doctors in clinic
    total_docs = DoctorClinic.objects.filter(clinic=clinic).count()
    active_docs = DoctorClinic.objects.filter(clinic=clinic, status=DoctorClinicStatus.ACTIVE).count()

    return {
        "clinic": {
            "id": str(clinic.id),
            "name": clinic.name,
            "timezone": clinic.timezone or "Asia/Kolkata",
            "commission_rate": str(clinic.commission_rate) if clinic.commission_rate is not None else "5.00",
        },
        "period": {
            "name": bounds.period,
            "start_date": bounds.start_date.isoformat(),
            "end_date": bounds.end_date.isoformat(),
            "days_count": bounds.days_count,
        },
        "appointments": {
            "total": tot,
            "completed": comp,
            "confirmed": conf,
            "cancelled": canc,
            "no_show": no_show,
            "pending": appt_stats["pending"] or 0,
            "reschedule_required": appt_stats["reschedule_required"] or 0,
            "today": today_count,
            "upcoming": upcoming_count,
            "completion_rate": comp_rate,
            "cancellation_rate": canc_rate,
        },
        "finance": {
            "gross_revenue": str(gross),
            "platform_commission_deducted": str(commission),
            "clinic_payable_share": str(clinic_share),
            "refund_volume": str(refunds),
            "successful_payments_count": pay_stats["paid_count"] or 0,
            "failed_payments_count": pay_stats["failed_count"] or 0,
            "payout_status": "ACCUMULATING",
            "payout_notice": "Your clinic earnings reflect net accrued payable share. Bank disbursements are processed manually or via scheduled gateway settlements.",
        },
        "doctors": {
            "total": total_docs,
            "active": active_docs,
        },
    }


def get_clinic_revenue_analytics(
    clinic: Clinic,
    bounds: DateRangeBounds,
    doctor_id: str = None,
) -> dict:
    """
    Detailed daily and monthly revenue analytics scoped to the clinic.
    """
    comm_qs = CommissionRecord.objects.filter(
        clinic=clinic,
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    pay_qs = Payment.objects.filter(
        clinic=clinic,
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if doctor_id:
        comm_qs = comm_qs.filter(appointment__doctor_id=doctor_id)
        pay_qs = pay_qs.filter(appointment__doctor_id=doctor_id)

    # Totals
    overall = comm_qs.aggregate(
        gross=Sum("gross_amount"),
        commission=Sum("commission_amount"),
        clinic_share=Sum("clinic_share"),
    )
    pay_overall = pay_qs.aggregate(
        paid_count=Count("id", filter=Q(status=PaymentStatus.PAID)),
        failed_count=Count("id", filter=Q(status=PaymentStatus.FAILED)),
        refunded_count=Count("id", filter=Q(status=PaymentStatus.REFUNDED)),
    )

    gross_val = _round_decimal(overall["gross"])
    comm_val = _round_decimal(overall["commission"])
    share_val = _round_decimal(overall["clinic_share"])

    # Daily revenue
    daily_comm = (
        comm_qs.values("created_at__date")
        .annotate(
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
            count=Count("id"),
        )
        .order_by("created_at__date")
    )
    comm_map = {r["created_at__date"]: r for r in daily_comm}

    daily_trend = []
    curr = bounds.start_date
    while curr <= bounds.end_date:
        r = comm_map.get(curr)
        daily_trend.append(
            {
                "date": curr.isoformat(),
                "gross_revenue": str(_round_decimal(r["gross"])) if r else "0.00",
                "platform_commission": str(_round_decimal(r["commission"])) if r else "0.00",
                "clinic_share": str(_round_decimal(r["clinic_share"])) if r else "0.00",
                "paid_appointments": r["count"] if r else 0,
            }
        )
        curr += timedelta(days=1)

    # Doctor-wise revenue breakdown in this clinic
    doc_breakdown = (
        comm_qs.values("appointment__doctor_id", "appointment__doctor__user__first_name", "appointment__doctor__user__last_name", "appointment__doctor__specialization")
        .annotate(
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
            count=Count("id"),
        )
        .order_by("-clinic_share")
    )

    doctors_revenue = [
        {
            "doctor_id": str(r["appointment__doctor_id"]),
            "doctor_name": f"{r['appointment__doctor__user__first_name'] or ''} {r['appointment__doctor__user__last_name'] or ''}".strip() or "Doctor",
            "specialization": r["appointment__doctor__specialization"] or "Specialist",
            "gross_revenue": str(_round_decimal(r["gross"])),
            "platform_commission": str(_round_decimal(r["commission"])),
            "clinic_share": str(_round_decimal(r["clinic_share"])),
            "appointments_count": r["count"],
        }
        for r in doc_breakdown
        if r["appointment__doctor_id"] is not None
    ]

    return {
        "totals": {
            "gross_revenue": str(gross_val),
            "platform_commission_deducted": str(comm_val),
            "clinic_share": str(share_val),
            "paid_count": pay_overall["paid_count"] or 0,
            "failed_count": pay_overall["failed_count"] or 0,
            "refunded_count": pay_overall["refunded_count"] or 0,
        },
        "daily_trend": daily_trend,
        "doctor_breakdown": doctors_revenue,
    }


def get_clinic_appointment_analytics(
    clinic: Clinic,
    bounds: DateRangeBounds,
    doctor_id: str = None,
) -> dict:
    """
    Appointment trends, hourly peak breakdown, and cancellation summary for this clinic.
    """
    appt_qs = Appointment.objects.filter(
        clinic=clinic,
        created_at__gte=bounds.start_dt,
        created_at__lte=bounds.end_dt,
    )
    if doctor_id:
        appt_qs = appt_qs.filter(doctor_id=doctor_id)

    # Aggregate by status
    status_stats = appt_qs.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
        confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
        cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
        pending=Count("id", filter=Q(status=AppointmentStatus.PENDING_CONFIRMATION)),
    )

    tot = status_stats["total"] or 0
    comp = status_stats["completed"] or 0
    canc = status_stats["cancelled"] or 0

    # Peak hours in clinic local timezone
    try:
        clinic_tz = pytz.timezone(clinic.timezone or "Asia/Kolkata")
    except Exception:
        clinic_tz = pytz.timezone("Asia/Kolkata")

    slots = appt_qs.values_list("start_at", flat=True)
    hourly_counts = {h: 0 for h in range(24)}
    for slot_dt in slots:
        if slot_dt:
            loc = slot_dt.astimezone(clinic_tz)
            hourly_counts[loc.hour] += 1

    peak_hours = [
        {
            "hour": h,
            "label": f"{h:02d}:00 - {h+1:02d}:00",
            "count": hourly_counts[h],
            "percentage": round((hourly_counts[h] / len(slots) * 100), 2) if len(slots) else 0.0,
        }
        for h in range(24)
    ]

    # Daily trend
    daily_qs = (
        appt_qs.values("created_at__date")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
            confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
            cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        )
        .order_by("created_at__date")
    )
    daily_map = {r["created_at__date"]: r for r in daily_qs}

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
            }
        )
        curr += timedelta(days=1)

    # Cancellation reasons
    canc_reasons = (
        appt_qs.filter(status=AppointmentStatus.CANCELLED)
        .values("cancellation_reason")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    cancellation_summary = [
        {
            "reason": r["cancellation_reason"] or "No reason provided",
            "count": r["count"],
            "percentage": round((r["count"] / canc * 100), 2) if canc else 0.0,
        }
        for r in canc_reasons
    ]

    return {
        "totals": {
            "total_bookings": tot,
            "completed": comp,
            "confirmed": status_stats["confirmed"] or 0,
            "cancelled": canc,
            "no_show": status_stats["no_show"] or 0,
            "pending": status_stats["pending"] or 0,
            "completion_rate": round((comp / tot * 100), 2) if tot else 0.0,
            "cancellation_rate": round((canc / tot * 100), 2) if tot else 0.0,
        },
        "daily_trend": daily_trend,
        "peak_hours": peak_hours,
        "cancellation_summary": cancellation_summary,
    }


def get_clinic_doctor_performance(
    clinic: Clinic,
    bounds: DateRangeBounds,
) -> list:
    """
    Performance of doctors practicing at this specific clinic.
    Preserves clinic-specific consultation fees.
    """
    associations = (
        DoctorClinic.objects.filter(clinic=clinic)
        .select_related("doctor__user")
        .order_by("doctor__user__first_name")
    )

    doctors_list = []
    for assoc in associations:
        doc = assoc.doctor
        doc_appts = Appointment.objects.filter(
            clinic=clinic,
            doctor=doc,
            created_at__gte=bounds.start_dt,
            created_at__lte=bounds.end_dt,
        )

        appt_stats = doc_appts.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
            cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
        )

        tot = appt_stats["total"] or 0
        comp = appt_stats["completed"] or 0
        canc = appt_stats["cancelled"] or 0

        fin_stats = CommissionRecord.objects.filter(
            clinic=clinic,
            appointment__doctor=doc,
            created_at__gte=bounds.start_dt,
            created_at__lte=bounds.end_dt,
        ).aggregate(
            gross=Sum("gross_amount"),
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )

        doctors_list.append(
            {
                "doctor_id": str(doc.id),
                "name": doc.user.get_full_name() or doc.user.email,
                "email": doc.user.email,
                "specialization": doc.specialization or "Specialist",
                "consultation_fee": str(_round_decimal(assoc.consultation_fee)),
                "is_active_at_clinic": assoc.status == DoctorClinicStatus.ACTIVE,
                "total_appointments": tot,
                "completed_appointments": comp,
                "cancelled_appointments": canc,
                "completion_rate": round((comp / tot * 100), 2) if tot else 0.0,
                "gross_revenue": str(_round_decimal(fin_stats["gross"])),
                "platform_commission": str(_round_decimal(fin_stats["commission"])),
                "clinic_share": str(_round_decimal(fin_stats["clinic_share"])),
            }
        )

    doctors_list.sort(key=lambda x: Decimal(x["clinic_share"]), reverse=True)
    return doctors_list
