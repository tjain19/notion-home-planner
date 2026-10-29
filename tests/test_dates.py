from datetime import date, datetime, timezone

import pytest

from family_tasks import dates

WED = date(2026, 10, 28)


@pytest.mark.parametrize("due, term", [
    (date(2026, 10, 1), "This week"),      # overdue
    (WED, "This week"),
    (date(2026, 11, 1), "This week"),      # this Sunday, even though it's next month
    (date(2026, 10, 30), "This week"),
    (date(2026, 11, 2), "This quarter"),   # past October, within Q4
    (date(2026, 12, 31), "This quarter"),
    (date(2027, 1, 1), "Long term"),
])
def test_term_for(due, term):
    assert dates.term_for(due, WED) == term


def test_term_for_this_month():
    assert dates.term_for(date(2026, 10, 20), date(2026, 10, 7)) == "This month"


def test_term_on_sunday_rolls_over_on_monday():
    sunday, monday = date(2026, 11, 1), date(2026, 11, 2)
    assert dates.term_for(date(2026, 11, 6), sunday) == "This month"
    assert dates.term_for(date(2026, 11, 6), monday) == "This week"


def test_add_months_clamps_day():
    assert dates.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert dates.add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert dates.add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)


def test_add_months_keeps_time():
    value = datetime(2026, 10, 31, 9, 30, tzinfo=timezone.utc)
    assert dates.add_months(value, 1) == datetime(2026, 11, 30, 9, 30, tzinfo=timezone.utc)


def test_local_date_converts_to_eastern():
    # 02:00 UTC on Nov 1 is still Oct 31 in New York.
    assert dates.local_date(dates.parse("2026-11-01T02:00:00.000+00:00")) == date(2026, 10, 31)
    assert dates.local_date(dates.parse("2026-11-01")) == date(2026, 11, 1)


def test_quarter_end():
    assert dates.quarter_end(date(2026, 2, 3)) == date(2026, 3, 31)
    assert dates.quarter_end(date(2026, 9, 30)) == date(2026, 9, 30)
