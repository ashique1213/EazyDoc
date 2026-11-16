import calendar
from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple
import pytz
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date


class DateRangeBounds:
    def __init__(
        self,
        start_date: date,
        end_date: date,
        start_dt: datetime,
        end_dt: datetime,
        period: str,
        timezone_str: str,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.period = period
        self.timezone_str = timezone_str
        self.days_count = (end_date - start_date).days + 1


def resolve_date_range(
    period: Optional[str] = "last_30_days",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tz_name: Optional[str] = None,
) -> DateRangeBounds:
    """
    Resolves standard or custom date range filters into localized boundaries
    and timezone-aware UTC datetime bounds for accurate database queries.
    """
    tz_str = tz_name or getattr(settings, "TIME_ZONE", "Asia/Kolkata")
    try:
        local_tz = pytz.timezone(tz_str)
    except Exception:
        local_tz = pytz.timezone("Asia/Kolkata")

    now_utc = timezone.now()
    now_local = now_utc.astimezone(local_tz)
    today = now_local.date()

    period = (period or "").lower().strip()

    if date_from or date_to:
        period = "custom"
        parsed_from = parse_date(date_from) if date_from else None
        parsed_to = parse_date(date_to) if date_to else None

        if parsed_from and parsed_to:
            if parsed_from > parsed_to:
                parsed_from, parsed_to = parsed_to, parsed_from
            start_date = parsed_from
            end_date = parsed_to
        elif parsed_from:
            start_date = parsed_from
            end_date = today
        elif parsed_to:
            start_date = parsed_to - timedelta(days=29)
            end_date = parsed_to
        else:
            start_date = today - timedelta(days=29)
            end_date = today

    elif period == "today":
        start_date = today
        end_date = today

    elif period == "yesterday":
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)

    elif period == "last_7_days":
        start_date = today - timedelta(days=6)
        end_date = today

    elif period == "last_90_days":
        start_date = today - timedelta(days=89)
        end_date = today

    elif period == "this_month":
        start_date = today.replace(day=1)
        end_date = today

    elif period == "previous_month":
        # First day of current month minus 1 day gives last day of prev month
        first_of_this_month = today.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_prev_month.replace(day=1)
        end_date = last_of_prev_month

    elif period == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today

    else:
        # Default: last_30_days
        period = "last_30_days"
        start_date = today - timedelta(days=29)
        end_date = today

    # Construct boundary localized datetimes
    start_dt_local = local_tz.localize(datetime.combine(start_date, time.min))
    end_dt_local = local_tz.localize(datetime.combine(end_date, time.max))

    # Convert to UTC for uniform database queries
    start_dt_utc = start_dt_local.astimezone(pytz.UTC)
    end_dt_utc = end_dt_local.astimezone(pytz.UTC)

    return DateRangeBounds(
        start_date=start_date,
        end_date=end_date,
        start_dt=start_dt_utc,
        end_dt=end_dt_utc,
        period=period,
        timezone_str=str(local_tz.zone),
    )

