"""Tests for timezone-aware date parsing and boundary handling."""

from datetime import datetime, date, time, timedelta
from dateutil import tz
import pytest
from backend.services.date_parser import DateParser
from backend.models import DeadlineConfidence


@pytest.fixture
def parser():
    return DateParser(timezone_str="Asia/Kolkata")


def test_no_deadline_found(parser):
    text = "Need to finish README and investigate error in model"
    deadline_iso, expr, conf = parser.extract_deadline(text)
    assert deadline_iso is None
    assert expr is None
    assert conf == DeadlineConfidence.UNKNOWN


def test_tomorrow_parsing(parser):
    ref_time = datetime(2026, 10, 26, 11, 30, 0, tzinfo=parser.tz)
    text = "Email mentor tomorrow about project status"
    deadline_iso, expr, conf = parser.extract_deadline(text, reference_time=ref_time)

    assert deadline_iso is not None
    assert "tomorrow" in expr.lower()
    assert conf == DeadlineConfidence.SUGGESTED

    dt = datetime.fromisoformat(deadline_iso)
    assert dt.date() == date(2026, 10, 27)
    assert dt.tzinfo is not None


def test_today_and_tonight_parsing(parser):
    ref_time = datetime(2026, 10, 26, 11, 30, 0, tzinfo=parser.tz)
    deadline_iso, expr, conf = parser.extract_deadline("Submit assignment today", reference_time=ref_time)
    assert deadline_iso is not None
    dt = datetime.fromisoformat(deadline_iso)
    assert dt.date() == date(2026, 10, 26)

    deadline_iso_night, _, _ = parser.extract_deadline("Submit assignment tonight", reference_time=ref_time)
    dt_night = datetime.fromisoformat(deadline_iso_night)
    assert dt_night.hour == 21


def test_day_after_tomorrow(parser):
    ref_time = datetime(2026, 10, 26, 11, 30, 0, tzinfo=parser.tz)
    deadline_iso, expr, conf = parser.extract_deadline("Review code day after tomorrow", reference_time=ref_time)
    assert deadline_iso is not None
    dt = datetime.fromisoformat(deadline_iso)
    assert dt.date() == date(2026, 10, 28)


def test_in_n_days(parser):
    ref_time = datetime(2026, 10, 26, 11, 30, 0, tzinfo=parser.tz)
    deadline_iso, expr, conf = parser.extract_deadline("Prepare slides in 3 days", reference_time=ref_time)
    assert deadline_iso is not None
    dt = datetime.fromisoformat(deadline_iso)
    assert dt.date() == date(2026, 10, 29)


def test_month_boundary_rollover(parser):
    # Reference time on the last day of October
    ref_time = datetime(2026, 10, 31, 15, 0, 0, tzinfo=parser.tz)
    deadline_iso, expr, conf = parser.extract_deadline("Send quarterly report tomorrow", reference_time=ref_time)
    assert deadline_iso is not None
    dt = datetime.fromisoformat(deadline_iso)
    assert dt.date() == date(2026, 11, 1)


def test_year_boundary_rollover(parser):
    # Reference time on New Year's Eve
    ref_time = datetime(2026, 12, 31, 22, 0, 0, tzinfo=parser.tz)
    deadline_iso, expr, conf = parser.extract_deadline("Renew licence tomorrow", reference_time=ref_time)
    assert deadline_iso is not None
    dt = datetime.fromisoformat(deadline_iso)
    assert dt.date() == date(2027, 1, 1)


def test_midnight_transition(parser):
    # Just before midnight: 23:59:50
    before_midnight = datetime(2026, 10, 26, 23, 59, 50, tzinfo=parser.tz)
    d1, _, _ = parser.extract_deadline("Call client tomorrow", reference_time=before_midnight)
    dt1 = datetime.fromisoformat(d1)
    assert dt1.date() == date(2026, 10, 27)

    # Just after midnight: 00:00:10
    after_midnight = datetime(2026, 10, 27, 0, 0, 10, tzinfo=parser.tz)
    d2, _, _ = parser.extract_deadline("Call client tomorrow", reference_time=after_midnight)
    dt2 = datetime.fromisoformat(d2)
    assert dt2.date() == date(2026, 10, 28)
