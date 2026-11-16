import csv
import io
from typing import Generator, List, Optional
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone

from apps.appointments.models import Appointment, AppointmentStatus
from apps.clinics.models import Clinic, DoctorClinic
from apps.doctors.models import Doctor
from apps.payments.models import CommissionRecord, Payment
from .admin_analytics import (
    get_clinic_performance_analytics,
    get_doctor_performance_analytics,
    get_financial_reconciliation,
)
from .date_range import DateRangeBounds


def _mask_patient_name(name: Optional[str]) -> str:
    """Masks patient full name for privacy compliance (e.g. 'John Doe' -> 'John D.')."""
    if not name:
        return "Patient"
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


class Echo:
    """An object that implements just the write method of the file-like interface."""
    def write(self, value):
        return value


def export_admin_csv(
    report_type: str,
    bounds: DateRangeBounds,
    clinic_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
) -> HttpResponse:
    """
    Generates sanitized CSV export for Super Admin reports.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    filename = f"eazydoc-admin-{report_type}-{bounds.start_date.isoformat()}-to-{bounds.end_date.isoformat()}.csv"

    if report_type == "revenue":
        writer.writerow([
            "Payment ID",
            "Date",
            "Clinic Name",
            "Doctor Name",
            "Gross Amount (INR)",
            "Commission Rate (%)",
            "Platform Commission (INR)",
            "Clinic Share (INR)",
            "Payment Status",
            "Settlement Status",
        ])
        comm_qs = (
            CommissionRecord.objects.filter(
                created_at__gte=bounds.start_dt,
                created_at__lte=bounds.end_dt,
            )
            .select_related("payment", "clinic", "appointment__doctor__user")
            .order_by("-created_at")
        )
        if clinic_id:
            comm_qs = comm_qs.filter(clinic_id=clinic_id)
        if doctor_id:
            comm_qs = comm_qs.filter(appointment__doctor_id=doctor_id)

        for rec in comm_qs:
            doc_user = getattr(rec.appointment.doctor, "user", None) if rec.appointment and rec.appointment.doctor else None
            doc_name = doc_user.get_full_name() if doc_user else "N/A"
            writer.writerow([
                str(rec.payment_id),
                rec.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                rec.clinic.name if rec.clinic else "N/A",
                doc_name,
                f"{rec.gross_amount:.2f}",
                f"{rec.commission_rate:.2f}",
                f"{rec.commission_amount:.2f}",
                f"{rec.clinic_share:.2f}",
                rec.payment.status if rec.payment else "N/A",
                rec.status,
            ])

    elif report_type == "clinics":
        writer.writerow([
            "Clinic Name",
            "Status",
            "Active",
            "City",
            "State",
            "Total Doctors",
            "Active Doctors",
            "Total Bookings",
            "Completed",
            "Cancelled",
            "Completion Rate (%)",
            "Gross Volume (INR)",
            "Platform Commission (INR)",
            "Clinic Share (INR)",
            "Avg Consultation (INR)",
        ])
        clinics_data = get_clinic_performance_analytics(bounds)
        for c in clinics_data:
            writer.writerow([
                c["name"],
                c["status"],
                "Yes" if c["is_active"] else "No",
                c["city"],
                c["state"],
                c["total_doctors"],
                c["active_doctors"],
                c["total_appointments"],
                c["completed_appointments"],
                c["cancelled_appointments"],
                f"{c['completion_rate']:.2f}",
                c["gross_volume"],
                c["platform_commission"],
                c["clinic_share"],
                c["avg_consultation_value"],
            ])

    elif report_type == "doctors":
        writer.writerow([
            "Doctor Name",
            "Email",
            "Specialization",
            "Verification Status",
            "Affiliated Clinics Count",
            "Total Appointments",
            "Completed",
            "Cancelled",
            "Completion Rate (%)",
            "Avg Per Active Day",
            "Gross Revenue (INR)",
            "Platform Commission (INR)",
            "Clinic Share (INR)",
        ])
        doctors_data = get_doctor_performance_analytics(bounds, clinic_id=clinic_id)
        for d in doctors_data:
            writer.writerow([
                d["name"],
                d["email"],
                d["specialization"],
                d["verification_status"],
                len(d["affiliations"]),
                d["total_appointments"],
                d["completed_appointments"],
                d["cancelled_appointments"],
                f"{d['completion_rate']:.2f}",
                d["avg_appointments_per_day"],
                d["gross_revenue"],
                d["platform_commission"],
                d["clinic_share"],
            ])

    elif report_type == "reconciliation":
        writer.writerow([
            "Discrepancy Type",
            "Severity",
            "Payment ID",
            "Appointment ID",
            "Clinic Name",
            "Amount (INR)",
            "Description",
        ])
        rec_data = get_financial_reconciliation(bounds, clinic_id=clinic_id)
        for disc in rec_data["discrepancies"]:
            writer.writerow([
                disc["type"],
                disc["severity"],
                disc["payment_id"] or "N/A",
                disc["appointment_id"] or "N/A",
                disc["clinic_name"],
                disc["amount"],
                disc["description"],
            ])

    else:
        # Default: appointments report
        writer.writerow([
            "Appointment ID",
            "Scheduled Start (UTC)",
            "Clinic Name",
            "Doctor Name",
            "Patient Name (Masked)",
            "Status",
            "Fee (INR)",
            "Created At (UTC)",
        ])
        appts = (
            Appointment.objects.filter(
                created_at__gte=bounds.start_dt,
                created_at__lte=bounds.end_dt,
            )
            .select_related("clinic", "doctor__user", "patient")
            .order_by("-created_at")
        )
        if clinic_id:
            appts = appts.filter(clinic_id=clinic_id)
        if doctor_id:
            appts = appts.filter(doctor_id=doctor_id)

        for a in appts:
            doc_user = getattr(a.doctor, "user", None) if a.doctor else None
            patient_user = getattr(a, "patient", None)
            patient_name = _mask_patient_name(patient_user.get_full_name() if patient_user else None)
            writer.writerow([
                str(a.id),
                a.start_at.strftime("%Y-%m-%d %H:%M:%S") if a.start_at else "N/A",
                a.clinic.name if a.clinic else "N/A",
                doc_user.get_full_name() if doc_user else "N/A",
                patient_name,
                a.status,
                f"{a.consultation_fee:.2f}" if a.consultation_fee else "0.00",
                a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def export_clinic_csv(
    clinic: Clinic,
    report_type: str,
    bounds: DateRangeBounds,
    doctor_id: Optional[str] = None,
) -> HttpResponse:
    """
    Generates sanitized CSV export for Clinic Owners scoped to their clinic.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    safe_clinic_name = "".join(c if c.isalnum() else "_" for c in clinic.name.lower())
    filename = f"clinic-{safe_clinic_name}-{report_type}-{bounds.start_date.isoformat()}-to-{bounds.end_date.isoformat()}.csv"

    if report_type == "revenue":
        writer.writerow([
            "Transaction ID",
            "Date",
            "Doctor Name",
            "Gross Collected (INR)",
            "Platform Commission Deducted (INR)",
            "Clinic Net Share (INR)",
            "Payment Status",
        ])
        comm_qs = (
            CommissionRecord.objects.filter(
                clinic=clinic,
                created_at__gte=bounds.start_dt,
                created_at__lte=bounds.end_dt,
            )
            .select_related("payment", "appointment__doctor__user")
            .order_by("-created_at")
        )
        if doctor_id:
            comm_qs = comm_qs.filter(appointment__doctor_id=doctor_id)

        for rec in comm_qs:
            doc_user = getattr(rec.appointment.doctor, "user", None) if rec.appointment and rec.appointment.doctor else None
            writer.writerow([
                str(rec.payment_id),
                rec.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                doc_user.get_full_name() if doc_user else "N/A",
                f"{rec.gross_amount:.2f}",
                f"{rec.commission_amount:.2f}",
                f"{rec.clinic_share:.2f}",
                rec.payment.status if rec.payment else "N/A",
            ])

    elif report_type == "doctors":
        writer.writerow([
            "Doctor Name",
            "Specialization",
            "Consultation Fee (INR)",
            "Active At Clinic",
            "Total Appointments",
            "Completed",
            "Cancelled",
            "Completion Rate (%)",
            "Clinic Share Generated (INR)",
        ])
        from .clinic_analytics import get_clinic_doctor_performance
        doc_data = get_clinic_doctor_performance(clinic, bounds)
        for d in doc_data:
            writer.writerow([
                d["name"],
                d["specialization"],
                d["consultation_fee"],
                "Yes" if d["is_active_at_clinic"] else "No",
                d["total_appointments"],
                d["completed_appointments"],
                d["cancelled_appointments"],
                f"{d['completion_rate']:.2f}",
                d["clinic_share"],
            ])

    elif report_type == "cancellations":
        writer.writerow([
            "Appointment ID",
            "Scheduled Time",
            "Doctor Name",
            "Patient Name (Masked)",
            "Cancelled At",
            "Cancellation Reason",
        ])
        canc_appts = (
            Appointment.objects.filter(
                clinic=clinic,
                status=AppointmentStatus.CANCELLED,
                created_at__gte=bounds.start_dt,
                created_at__lte=bounds.end_dt,
            )
            .select_related("doctor__user", "patient")
            .order_by("-updated_at")
        )
        if doctor_id:
            canc_appts = canc_appts.filter(doctor_id=doctor_id)

        for a in canc_appts:
            doc_user = getattr(a.doctor, "user", None) if a.doctor else None
            patient_user = getattr(a, "patient", None)
            writer.writerow([
                str(a.id),
                a.start_at.strftime("%Y-%m-%d %H:%M:%S") if a.start_at else "N/A",
                doc_user.get_full_name() if doc_user else "N/A",
                _mask_patient_name(patient_user.get_full_name() if patient_user else None),
                a.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                a.cancellation_reason or "N/A",
            ])

    else:
        # Default: appointments
        writer.writerow([
            "Appointment ID",
            "Scheduled Time",
            "Doctor Name",
            "Patient Name (Masked)",
            "Status",
            "Consultation Fee (INR)",
            "Booked At",
        ])
        appts = (
            Appointment.objects.filter(
                clinic=clinic,
                created_at__gte=bounds.start_dt,
                created_at__lte=bounds.end_dt,
            )
            .select_related("doctor__user", "patient")
            .order_by("-created_at")
        )
        if doctor_id:
            appts = appts.filter(doctor_id=doctor_id)

        for a in appts:
            doc_user = getattr(a.doctor, "user", None) if a.doctor else None
            patient_user = getattr(a, "patient", None)
            writer.writerow([
                str(a.id),
                a.start_at.strftime("%Y-%m-%d %H:%M:%S") if a.start_at else "N/A",
                doc_user.get_full_name() if doc_user else "N/A",
                _mask_patient_name(patient_user.get_full_name() if patient_user else None),
                a.status,
                f"{a.consultation_fee:.2f}" if a.consultation_fee else "0.00",
                a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
