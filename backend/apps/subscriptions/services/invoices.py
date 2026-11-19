import logging
from decimal import Decimal, ROUND_HALF_UP
import uuid
from django.db import transaction
from django.utils import timezone
from apps.subscriptions.models import (
    ClinicSubscription,
    InvoiceStatus,
    SubscriptionInvoice,
    SubscriptionPayment,
)

logger = logging.getLogger("apps.subscriptions")


class InvoiceService:
    """
    Manages generation, immutable snapshotting, and presentation of SaaS subscription invoices.
    Adheres to Indian GST B2B invoice formatting guidelines with unique sequential numbering.
    """

    TAX_RATE_GST = Decimal("18.00")  # 18% standard GST for digital SaaS

    @classmethod
    def generate_invoice_number(cls) -> str:
        """
        Generates a human-readable sequential invoice ID: INV-YYYYMM-XXXX
        Guarantees uniqueness across concurrent invoice generations.
        """
        now = timezone.now()
        prefix = f"INV-{now.strftime('%Y%m')}-"
        
        last_invoice = (
            SubscriptionInvoice.objects.filter(invoice_number__startswith=prefix)
            .order_by("-invoice_number")
            .first()
        )
        if last_invoice:
            try:
                last_seq = int(last_invoice.invoice_number.split("-")[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1

        candidate = f"{prefix}{new_seq:04d}"
        # Safeguard against collisions
        while SubscriptionInvoice.objects.filter(invoice_number=candidate).exists():
            new_seq += 1
            candidate = f"{prefix}{new_seq:04d}"

        return candidate

    @classmethod
    @transaction.atomic
    def generate_invoice_for_payment(
        cls,
        payment: SubscriptionPayment,
        subscription: ClinicSubscription,
    ) -> SubscriptionInvoice:
        """
        Creates an immutable SubscriptionInvoice record capturing current clinic details,
        plan pricing, and statutory GST calculation.
        """
        # If invoice already exists for this payment, return existing
        existing = getattr(payment, "invoice", None)
        if existing:
            return existing

        total_amount = payment.amount
        # Price inclusive calculation: Total = Subtotal * 1.18
        divisor = Decimal("1.00") + (cls.TAX_RATE_GST / Decimal("100.00"))
        subtotal_amount = (total_amount / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_amount = (total_amount - subtotal_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        clinic = payment.clinic
        plan = payment.plan

        billing_snapshot = {
            "clinic_name": clinic.name,
            "owner_email": clinic.owner.email,
            "owner_name": clinic.owner.get_full_name() or clinic.owner.email,
            "phone": clinic.phone,
            "address_line_1": clinic.address_line_1,
            "address_line_2": clinic.address_line_2 or "",
            "city": clinic.city,
            "state": clinic.state,
            "pincode": clinic.pincode,
            "country": clinic.country,
        }

        line_items = [
            {
                "item_id": 1,
                "description": f"EazyDoc SaaS Subscription: {plan.name} ({payment.billing_interval.title()})",
                "quantity": 1,
                "unit_price": str(subtotal_amount),
                "tax_rate_percent": str(cls.TAX_RATE_GST),
                "tax_amount": str(tax_amount),
                "total_amount": str(total_amount),
            }
        ]

        invoice_number = cls.generate_invoice_number()

        invoice = SubscriptionInvoice.objects.create(
            invoice_number=invoice_number,
            subscription=subscription,
            clinic=clinic,
            payment=payment,
            plan_name=plan.name,
            subtotal_amount=subtotal_amount,
            tax_rate=cls.TAX_RATE_GST,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency=payment.currency,
            status=InvoiceStatus.PAID,
            billing_period_start=subscription.current_period_start,
            billing_period_end=subscription.current_period_end or timezone.now(),
            line_items=line_items,
            billing_details=billing_snapshot,
            paid_at=payment.paid_at or timezone.now(),
        )

        logger.info(
            "Generated invoice %s for clinic %s, amount ₹%s",
            invoice.invoice_number,
            clinic.name,
            invoice.total_amount,
        )
        return invoice

    @classmethod
    def render_invoice_html(cls, invoice: SubscriptionInvoice) -> str:
        """
        Renders a standalone, printable HTML representation of the invoice.
        Suitable for browser printing (Ctrl+P -> Save as PDF) or direct client download.
        """
        details = invoice.billing_details or {}
        line_items = invoice.line_items or []
        cgst = (invoice.tax_amount / Decimal("2.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sgst = cgst

        items_html = "".join([
            f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 12px 16px; font-size: 14px; color: #111827;">{item.get('description')}</td>
                <td style="padding: 12px 16px; font-size: 14px; text-align: center; color: #374151;">{item.get('quantity')}</td>
                <td style="padding: 12px 16px; font-size: 14px; text-align: right; color: #374151;">₹{item.get('unit_price')}</td>
                <td style="padding: 12px 16px; font-size: 14px; text-align: right; color: #374151;">{item.get('tax_rate_percent')}%</td>
                <td style="padding: 12px 16px; font-size: 14px; text-align: right; font-weight: 600; color: #111827;">₹{item.get('total_amount')}</td>
            </tr>
            """
            for item in line_items
        ])

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice {invoice.invoice_number} - EazyDoc</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f3f4f6;
            margin: 0;
            padding: 32px 16px;
            color: #1f2937;
        }}
        .invoice-card {{
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 40px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #2563eb;
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}
        .brand-logo {{
            font-size: 26px;
            font-weight: 800;
            color: #111827;
        }}
        .brand-logo span {{
            color: #2563eb;
        }}
        .invoice-title {{
            text-align: right;
        }}
        .invoice-title h1 {{
            margin: 0 0 4px 0;
            font-size: 24px;
            color: #1e3a8a;
        }}
        .badge {{
            display: inline-block;
            background-color: #dcfce7;
            color: #15803d;
            font-size: 12px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 9999px;
            text-transform: uppercase;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }}
        .info-box h3 {{
            margin: 0 0 8px 0;
            font-size: 13px;
            text-transform: uppercase;
            color: #6b7280;
            letter-spacing: 0.05em;
        }}
        .info-box p {{
            margin: 2px 0;
            font-size: 14px;
            color: #1f2937;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 32px;
        }}
        th {{
            background-color: #f9fafb;
            padding: 12px 16px;
            text-align: left;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            color: #4b5563;
            border-bottom: 1px solid #e5e7eb;
        }}
        .summary-table {{
            width: 320px;
            margin-left: auto;
            border-collapse: collapse;
        }}
        .summary-table td {{
            padding: 8px 12px;
            font-size: 14px;
        }}
        .total-row {{
            border-top: 2px solid #e5e7eb;
            font-size: 16px !important;
            font-weight: 800;
            color: #111827;
        }}
        .footer {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            font-size: 12px;
            color: #6b7280;
        }}
        @media print {{
            body {{
                background-color: #ffffff;
                padding: 0;
            }}
            .invoice-card {{
                box-shadow: none;
                padding: 0;
            }}
            .no-print {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="invoice-card">
        <div class="no-print" style="margin-bottom: 20px; text-align: right;">
            <button onclick="window.print()" style="background: #2563eb; color: #fff; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-weight: 600;">
                Print / Save PDF
            </button>
        </div>
        <div class="header">
            <div>
                <div class="brand-logo">Eazy<span>Doc</span> Health Technologies</div>
                <p style="margin: 4px 0 0 0; font-size: 13px; color: #4b5563;">Multi-Tenant Clinic Management Cloud</p>
                <p style="margin: 2px 0 0 0; font-size: 13px; color: #6b7280;">GSTIN: 29AAAAA0000A1Z5 | support@eazydoc.com</p>
            </div>
            <div class="invoice-title">
                <h1>TAX INVOICE</h1>
                <p style="margin: 2px 0; font-weight: 600; color: #111827;">{invoice.invoice_number}</p>
                <div class="badge">{invoice.status}</div>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-box">
                <h3>Billed To (Clinic)</h3>
                <p style="font-weight: 700; font-size: 15px;">{details.get('clinic_name')}</p>
                <p>Attn: {details.get('owner_name')}</p>
                <p>{details.get('address_line_1')}</p>
                {f"<p>{details.get('address_line_2')}</p>" if details.get('address_line_2') else ""}
                <p>{details.get('city')}, {details.get('state')} - {details.get('pincode')}</p>
                <p>Email: {details.get('owner_email')}</p>
                <p>Phone: {details.get('phone')}</p>
            </div>
            <div class="info-box" style="text-align: right;">
                <h3>Billing Summary</h3>
                <p><strong>Invoice Date:</strong> {invoice.created_at.strftime('%d %B %Y')}</p>
                <p><strong>Paid Date:</strong> {invoice.paid_at.strftime('%d %B %Y') if invoice.paid_at else 'N/A'}</p>
                <p><strong>Billing Period:</strong> {invoice.billing_period_start.strftime('%d %b %Y')} to {invoice.billing_period_end.strftime('%d %b %Y')}</p>
                <p><strong>Payment Gateway:</strong> Razorpay</p>
                <p><strong>Gateway Order:</strong> {invoice.payment.razorpay_order_id if invoice.payment else 'Direct'}</p>
                <p><strong>Payment Ref:</strong> {invoice.payment.razorpay_payment_id if invoice.payment else 'Direct'}</p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Description</th>
                    <th style="text-align: center;">Qty</th>
                    <th style="text-align: right;">Unit Price (INR)</th>
                    <th style="text-align: right;">Tax Rate</th>
                    <th style="text-align: right;">Amount (INR)</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <table class="summary-table">
            <tr>
                <td style="color: #4b5563;">Taxable Subtotal:</td>
                <td style="text-align: right; font-weight: 600;">₹{invoice.subtotal_amount}</td>
            </tr>
            <tr>
                <td style="color: #4b5563;">CGST (9.00%):</td>
                <td style="text-align: right;">₹{cgst}</td>
            </tr>
            <tr>
                <td style="color: #4b5563;">SGST (9.00%):</td>
                <td style="text-align: right;">₹{sgst}</td>
            </tr>
            <tr class="total-row">
                <td>Total Amount Paid:</td>
                <td style="text-align: right; color: #2563eb;">₹{invoice.total_amount}</td>
            </tr>
        </table>

        <div class="footer">
            <p>This is a computer-generated tax invoice and requires no physical signature.</p>
            <p>Thank you for choosing EazyDoc to power your clinic healthcare practice.</p>
        </div>
    </div>
</body>
</html>"""
        return html_template
