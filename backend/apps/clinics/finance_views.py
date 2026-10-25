from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clinics.dashboard_views import get_clinic_date_bounds
from apps.clinics.models import Clinic, ClinicStaffPermission
from apps.clinics.permissions import check_clinic_access
from apps.payments.models import CommissionRecord, Payment, PaymentStatus


class ClinicFinanceSummaryView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/finance/summary/
    Returns clinic-specific financial overview:
    - Gross patient payments
    - Recorded platform commission
    - Calculated clinic share
    - Payment failures
    - Refund totals
    - Settlement / payout status notice
    Restricted to clinic owners and staff with VIEW_FINANCIAL_SUMMARY.
    """

    @extend_schema(
        summary="Clinic Financial Summary",
        description="Returns date-filtered financial metrics scoped strictly to the clinic.",
        parameters=[
            OpenApiParameter(name="period", type=str, description="today | this_week | this_month | custom"),
            OpenApiParameter(name="from_date", type=str, description="YYYY-MM-DD"),
            OpenApiParameter(name="to_date", type=str, description="YYYY-MM-DD"),
        ],
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.VIEW_FINANCIAL_SUMMARY):
            raise PermissionDenied("You do not have permission to view financial records for this clinic.")

        period = request.query_params.get("period", "this_month")
        from_date_str = request.query_params.get("from_date")
        to_date_str = request.query_params.get("to_date")

        bounds = get_clinic_date_bounds(clinic, period, from_date_str, to_date_str)
        start_utc = bounds["start_utc"]
        end_utc = bounds["end_utc"]

        # Scope queries to this clinic only
        payments_qs = Payment.objects.filter(clinic_id=clinic.id)
        commissions_qs = CommissionRecord.objects.filter(clinic_id=clinic.id)

        # Gross payments in period
        period_paid_qs = payments_qs.filter(status=PaymentStatus.PAID, paid_at__range=(start_utc, end_utc))
        gross_period_amount = period_paid_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        gross_period_count = period_paid_qs.count()

        # Commissions in period
        period_comm_qs = commissions_qs.filter(created_at__range=(start_utc, end_utc))
        comm_agg = period_comm_qs.aggregate(
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )
        period_commission = comm_agg["commission"] or Decimal("0.00")
        period_clinic_share = comm_agg["clinic_share"] or Decimal("0.00")

        # Payment failures in period
        period_failed_qs = payments_qs.filter(status=PaymentStatus.FAILED, created_at__range=(start_utc, end_utc))
        failed_count = period_failed_qs.count()

        # Refunds in period
        period_refund_qs = payments_qs.filter(
            status__in=[PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED, PaymentStatus.REFUND_PENDING],
            updated_at__range=(start_utc, end_utc),
        )
        refund_agg = period_refund_qs.aggregate(total=Sum("amount"), count=Count("id"))
        refunded_amount = refund_agg["total"] or Decimal("0.00")
        refunded_count = refund_agg["count"]

        # All-time totals for reference
        all_time_paid = payments_qs.filter(status=PaymentStatus.PAID).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        all_time_comm = commissions_qs.aggregate(
            commission=Sum("commission_amount"),
            clinic_share=Sum("clinic_share"),
        )

        return Response(
            {
                "success": True,
                "data": {
                    "clinic": {
                        "id": str(clinic.id),
                        "name": clinic.name,
                        "timezone": clinic.timezone,
                    },
                    "period_info": {
                        "period": period,
                        "from_date": bounds["start_date"].isoformat(),
                        "to_date": bounds["end_date"].isoformat(),
                    },
                    "period_metrics": {
                        "gross_payments": str(gross_period_amount),
                        "successful_payments_count": gross_period_count,
                        "recorded_platform_commission": str(period_commission),
                        "calculated_clinic_share": str(period_clinic_share),
                        "failed_payments_count": failed_count,
                        "refunded_total": str(refunded_amount),
                        "refunded_count": refunded_count,
                        "actual_payouts": "0.00",
                        "payout_notice": (
                            "Calculated clinic share is stored for reporting purposes. "
                            "No bank payout or direct settlement integration is active."
                        ),
                    },
                    "all_time_metrics": {
                        "all_time_gross": str(all_time_paid),
                        "all_time_commission": str(all_time_comm["commission"] or Decimal("0.00")),
                        "all_time_clinic_share": str(all_time_comm["clinic_share"] or Decimal("0.00")),
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class ClinicFinancePaymentsListView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/finance/payments/
    Paginated, searchable transaction log for the clinic.
    Enforces read-only access and tenant isolation.
    """

    @extend_schema(
        summary="List Clinic Payment Transactions",
        description="Returns paginated payment and commission records for the clinic.",
        parameters=[
            OpenApiParameter(name="status", type=str, description="PaymentStatus filter"),
            OpenApiParameter(name="search", type=str, description="Booking reference or patient keyword"),
            OpenApiParameter(name="page", type=int, description="Page number (default: 1)"),
            OpenApiParameter(name="page_size", type=int, description="Page size (default: 20, max: 100)"),
        ],
    )
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, id=clinic_id)
        if not check_clinic_access(request.user, clinic, required_permission=ClinicStaffPermission.VIEW_FINANCIAL_SUMMARY):
            raise PermissionDenied("You do not have permission to view payment transactions for this clinic.")

        qs = (
            Payment.objects.filter(clinic_id=clinic.id)
            .select_related("appointment", "appointment__doctor", "patient", "commission_record")
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        if status_param and status_param.upper() != "ALL":
            qs = qs.filter(status=status_param.upper())

        search_param = request.query_params.get("search")
        if search_param:
            search_val = search_param.strip()
            qs = qs.filter(
                Q(appointment__booking_reference__icontains=search_val)
                | Q(patient__first_name__icontains=search_val)
                | Q(patient__last_name__icontains=search_val)
                | Q(patient__email__icontains=search_val)
                | Q(gateway_payment_id__icontains=search_val)
                | Q(gateway_order_id__icontains=search_val)
            )

        page_number = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page_number)

        records = []
        for p in page_obj:
            comm = getattr(p, "commission_record", None)
            records.append({
                "id": str(p.id),
                "amount": str(p.amount),
                "currency": p.currency,
                "status": p.status,
                "gateway_name": p.gateway_name,
                "gateway_order_id": p.gateway_order_id,
                "gateway_payment_id": p.gateway_payment_id or "",
                "created_at": p.created_at.isoformat(),
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "booking_reference": p.appointment.booking_reference if p.appointment else "",
                "doctor_name": p.appointment.doctor.full_name if (p.appointment and p.appointment.doctor) else "",
                "patient": {
                    "id": str(p.patient_id),
                    "name": f"{p.patient.first_name} {p.patient.last_name}".strip() or p.patient.email,
                    "email": p.patient.email,
                },
                "commission_snapshot": {
                    "commission_rate": str(comm.commission_rate) if comm else None,
                    "commission_amount": str(comm.commission_amount) if comm else None,
                    "clinic_share": str(comm.clinic_share) if comm else None,
                    "status": comm.status if comm else None,
                } if comm else None,
            })

        return Response(
            {
                "success": True,
                "data": {
                    "count": paginator.count,
                    "total_pages": paginator.num_pages,
                    "current_page": page_obj.number,
                    "page_size": page_size,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                    "results": records,
                },
            },
            status=status.HTTP_200_OK,
        )
