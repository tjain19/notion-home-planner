"""Date rules, all in US Eastern time."""

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)


def now() -> datetime:
    return datetime.now(TZ)


def parse(value: str) -> date | datetime:
    """Parse a Notion date string, which is either a date or a datetime."""
    if len(value) == 10:
        return date.fromisoformat(value)
    return datetime.fromisoformat(value)


def local_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.astimezone(TZ).date() if value.tzinfo else value.date()
    return value


def week_end(day: date) -> date:
    """The Sunday that ends the Monday-to-Sunday week containing day."""
    return day + timedelta(days=6 - day.weekday())


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def month_end(day: date) -> date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def quarter_end(day: date) -> date:
    last_month = (day.month - 1) // 3 * 3 + 3
    return month_end(day.replace(month=last_month, day=1))


def term_for(due: date, today: date) -> str:
    """Overdue or due by this Sunday is This week, then month, quarter, later."""
    if due <= week_end(today):
        return "This week"
    if due <= month_end(today):
        return "This month"
    if due <= quarter_end(today):
        return "This quarter"
    return "Long term"


def add_months(value: date | datetime, months: int) -> date | datetime:
    """Add months, clamping the day so Jan 31 + 1 month is Feb 28 (or 29)."""
    index = value.month - 1 + months
    year, month = value.year + index // 12, index % 12 + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def format_notion(value: date | datetime) -> str:
    return value.isoformat()


def short(day: date) -> str:
    return f"{day:%b} {day.day}"
