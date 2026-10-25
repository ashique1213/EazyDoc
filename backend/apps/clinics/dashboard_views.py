from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.appointments.models import Appointment, AppointmentStatus
from apps.clinics.models import Clinic, ClinicStaffPermission, DoctorClinic, DoctorClinicStatus
from apps.clinics.permissions import check_clinic_access
from apps.payments.models import CommissionRecord, Payment, PaymentStatus


def get_clinic_date_bounds(clinic: Clinic, period: str = None, from_date_str: str = None, to_date_str: str = None):
    try:
        clinic_tz = ZoneInfo(clinic.timezone)
    except Exception:
        clinic_tz = ZoneInfo("Asia/Kolkata")

    now_local = timezone.now().astimezone(clinic_tz)
    today_local = now_local.date()

    if period == "today":
        start_date = today_local
        end_date = today_local
    elif period == "this_week":
        start_date = today_local - timedelta(days=today_local.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == "this_month":
        start_date = today_local.replace(day=1)
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month - timedelta(days=1)
    elif period == "custom" and from_date_str and to_date_str:
        try:
            start_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = today_local
            end_date = today_local
    else:
        # Default to this month for scoped metrics
        start_date = today_local.replace(day=1)
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month - timedelta(days=1)

    start_dt_local = datetime.combine(start_date, time.min, tzinfo=clinic_tz)
    end_dt_local = datetime.combine(end_date, time.max, tzinfo=clinic_tz)
    start_utc = start_dt_local.astimezone(ZoneInfo("UTC"))
    end_utc = end_dt_local.astimezone(ZoneInfo("UTC"))

    # Also compute today UTC bounds in clinic timezone
    today_start_dt = datetime.combine(today_local, time.min, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))
    today_end_dt = datetime.combine(today_local, time.max, tzinfo=clinic_tz).astimezone(ZoneInfo("UTC"))

    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "today_local": today_local,
        "today_start_utc": today_start_dt,
        "today_end_utc": today_end_dt,
        "clinic_tz": clinic_tz,
    }


class ClinicDashboardSummaryView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/dashboard/summary/
    Retrieves operational, clinical, and financial metrics scoped exclusively to the requested clinic.
    Enforces multi-tenant authorization, object-level permissions, and clinic-timezone date filtering.
    """

    @extend_schema(
        summary="Clinic Dashboard Summary",
        description="Returns trusted aggregated operational metrics for the authorized clinic.",
        parameters=[
            OpenApiParameter(name="period", type=str, description="today | this_week | this_month | custom"),
            OpenApiParameter(name="from_date", type=str, description="YYYY-MM-DD for custom period"),
            OpenApiParameter(name="to_date", type=str, description="YYYY-MM-DD for custom period"),
        ],
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic):
            raise PermissionDenied("You do not have permission to access dashboard data for this clinic.")

        period = request.query_params.get("period", "this_month")
        from_date_str = request.query_params.get("from_date")
        to_date_str = request.query_params.get("to_date")

        bounds = get_clinic_date_bounds(clinic, period, from_date_str, to_date_str)
        start_utc = bounds["start_utc"]
        end_utc = bounds["end_utc"]
        today_start_utc = bounds["today_start_utc"]
        today_end_utc = bounds["today_end_utc"]

        # Doctor affiliations
        total_active_doctors = DoctorClinic.objects.filter(
            clinic_id=clinic.id, status=DoctorClinicStatus.ACTIVE
        ).count()
        pending_doctor_invitations = DoctorClinic.objects.filter(
            clinic_id=clinic.id, status=DoctorClinicStatus.INVITED
        ).count()

        # Appointments
        now_utc = timezone.now()
        today_appointments_count = Appointment.objects.filter(
            clinic_id=clinic.id,
            start_at__range=(today_start_utc, today_end_utc),
        ).count()

        upcoming_appointments_count = Appointment.objects.filter(
            clinic_id=clinic.id,
            start_at__gte=now_utc,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.PENDING_CONFIRMATION,
                AppointmentStatus.RESCHEDULE_REQUIRED,
            ],
        ).count()

        appointments_requiring_attention_count = Appointment.objects.filter(
            clinic_id=clinic.id,
        ).filter(
            Q(reschedule_required=True)
            | Q(status=AppointmentStatus.RESCHEDULE_REQUIRED)
            | Q(status=AppointmentStatus.PENDING_CONFIRMATION)
        ).count()

        # Date-filtered appointment stats
        period_appts_qs = Appointment.objects.filter(
            clinic_id=clinic.id,
            start_at__range=(start_utc, end_utc),
        )
        total_period_appointments = period_appts_qs.count()
        completed_appointments_count = period_appts_qs.filter(status=AppointmentStatus.COMPLETED).count()
        cancelled_appointments_count = period_appts_qs.filter(status=AppointmentStatus.CANCELLED).count()

        cancellation_rate = 0.0
        if total_period_appointments > 0:
            cancellation_rate = round((cancelled_appointments_count / total_period_appointments) * 100, 2)

        # Financial totals
        gross_patient_payments = Payment.objects.filter(
            clinic_id=clinic.id,
            status=PaymentStatus.PAID,
            paid_at__range=(start_utc, end_utc),
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        commission_agg = CommissionRecord.objects.filter(
            clinic_id=clinic.id,
            created_at__range=(start_utc, end_utc),
        ).aggregate(
            platform_commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )
        recorded_platform_commission = commission_agg["platform_commission"] or Decimal("0.00")
        calculated_clinic_share = commission_agg["clinic_share"] or Decimal("0.00")

        return Response(
            {
                "success": True,
                "data": {
                    "clinic": {
                        "id": str(clinic.id),
                        "name": clinic.name,
                        "slug": clinic.slug,
                        "status": clinic.status,
                        "timezone": clinic.timezone,
                    },
                    "period_info": {
                        "period": period,
                        "from_date": bounds["start_date"].isoformat(),
                        "to_date": bounds["end_date"].isoformat(),
                        "timezone": clinic.timezone,
                    },
                    "doctor_metrics": {
                        "total_active_doctors": total_active_doctors,
                        "pending_doctor_invitations": pending_doctor_invitations,
                    },
                    "appointment_metrics": {
                        "today_appointments": today_appointments_count,
                        "upcoming_appointments": upcoming_appointments_count,
                        "completed_appointments": completed_appointments_count,
                        "cancelled_appointments": cancelled_appointments_count,
                        "appointments_requiring_attention": appointments_requiring_attention_count,
                        "total_appointments_in_period": total_period_appointments,
                        "cancellation_rate_percentage": cancellation_rate,
                    },
                    "financial_metrics": {
                        "currency": "INR",
                        "gross_patient_payments": str(gross_patient_payments),
                        "recorded_platform_commission": str(recorded_platform_commission),
                        "calculated_clinic_share": str(calculated_clinic_share),
                        "actual_payouts": "0.00",
                        "payout_status_notice": (
                            "No automated bank settlement integration. Calculated clinic share "
                            "is recorded for accounting reporting and not yet disbursed."
                        ),
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class ClinicDashboardTrendsView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/dashboard/appointment-trends/
    Returns daily appointment counts by status for trend visualization.
    """

    @extend_schema(
        summary="Clinic Appointment Trends",
        description="Returns daily appointment distribution for charts in clinic timezone.",
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic):
            raise PermissionDenied("You do not have permission to view trends for this clinic.")

        period = request.query_params.get("period", "this_month")
        from_date_str = request.query_params.get("from_date")
        to_date_str = request.query_params.get("to_date")

        bounds = get_clinic_date_bounds(clinic, period, from_date_str, to_date_str)
        start_utc = bounds["start_utc"]
        end_utc = bounds["end_utc"]
        clinic_tz = bounds["clinic_tz"]

        appts = Appointment.objects.filter(
            clinic_id=clinic.id,
            start_at__range=(start_utc, end_utc),
        ).values("start_at", "status")

        daily_data = {}
        curr = bounds["start_date"]
        while curr <= bounds["end_date"]:
            key = curr.isoformat()
            daily_data[key] = {
                "date": key,
                "total": 0,
                "confirmed": 0,
                "completed": 0,
                "cancelled": 0,
                "no_show": 0,
            }
            curr += timedelta(days=1)

        for appt in appts:
            local_dt = appt["start_at"].astimezone(clinic_tz)
            date_key = local_dt.date().isoformat()
            if date_key in daily_data:
                daily_data[date_key]["total"] += 1
                st = appt["status"]
                if st == AppointmentStatus.CONFIRMED:
                    daily_data[date_key]["confirmed"] += 1
                elif st == AppointmentStatus.COMPLETED:
                    daily_data[date_key]["completed"] += 1
                elif st == AppointmentStatus.CANCELLED:
                    daily_data[date_key]["cancelled"] += 1
                elif st == AppointmentStatus.NO_SHOW:
                    daily_data[date_key]["no_show"] += 1

        return Response(
            {
                "success": True,
                "data": {
                    "timezone": clinic.timezone,
                    "trends": list(daily_data.values()),
                },
            },
            status=status.HTTP_200_OK,
        )


class ClinicDashboardFinancialSummaryView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/dashboard/financial-summary/
    Convenience alias returning financial breakdown and recent transactions for the dashboard.
    """

    @extend_schema(
        summary="Clinic Dashboard Financial Breakdown",
        description="Returns financial summary and recent transactions scoped to the clinic.",
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.VIEW_FINANCIAL_SUMMARY):
            raise PermissionDenied("You do not have permission to view financial data for this clinic.")

        period = request.query_params.get("period", "this_month")
        bounds = get_clinic_date_bounds(clinic, period)

        payments_qs = Payment.objects.filter(clinic_id=clinic.id)
        commissions_qs = CommissionRecord.objects.filter(clinic_id=clinic.id)

        paid_agg = payments_qs.filter(status=PaymentStatus.PAID).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        comm_agg = commissions_qs.aggregate(
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )
        failed_count = payments_qs.filter(status=PaymentStatus.FAILED).count()
        refunded_agg = payments_qs.filter(status__in=[PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED]).aggregate(
            total=Sum("amount"), count=Count("id")
        )

        recent_commissions = (
            commissions_qs.select_related("appointment", "payment")
            .order_by("-created_at")[:10]
        )

        transactions = []
        for c in recent_commissions:
            transactions.append({
                "id": str(c.id),
                "payment_id": str(c.payment_id),
                "booking_reference": c.appointment.booking_reference if c.appointment else "",
                "gross_amount": str(c.gross_amount),
                "commission_rate": str(c.commission_rate),
                "commission_amount": str(c.commission_amount),
                "clinic_share": str(c.clinic_share),
                "currency": c.currency,
                "status": c.status,
                "created_at": c.created_at.isoformat(),
            })

        return Response(
            {
                "success": True,
                "data": {
                    "summary": {
                        "gross_payments": str(paid_agg),
                        "platform_commission": str(comm_agg["commission"] or Decimal("0.00")),
                        "calculated_clinic_share": str(comm_agg["clinic_share"] or Decimal("0.00")),
                        "failed_payments_count": failed_count,
                        "refunded_total": str(refunded_agg["total"] or Decimal("0.00")),
                        "refunded_count": refunded_agg["count"],
                        "actual_payouts": "0.00",
                        "payout_notice": "Calculated clinic share is stored for reporting. No external bank transfer integration exists.",
                    },
                    "recent_transactions": transactions,
                },
            },
            status=status.HTTP_200_OK,
        )
