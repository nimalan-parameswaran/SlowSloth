"""Timezone-aware date parser for SlowSloth task extraction."""

from datetime import datetime, date, time, timedelta
import re
from typing import Optional, Tuple
from dateutil import tz
from dateutil.parser import parse as dateutil_parse
from backend.models import DeadlineConfidence
from backend.config import settings

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


class DateParser:
    """Extract and normalize relative date expressions to timezone-aware ISO timestamps."""

    def __init__(self, timezone_str: Optional[str] = None):
        self.timezone_str = timezone_str or settings.TIMEZONE
        self.tz = tz.gettz(self.timezone_str) or tz.UTC

    def get_current_time(self, reference_time: Optional[datetime] = None) -> datetime:
        """Get current localized datetime, or convert reference_time to target timezone."""
        if reference_time is not None:
            if reference_time.tzinfo is None:
                return reference_time.replace(tzinfo=self.tz)
            return reference_time.astimezone(self.tz)
        return datetime.now(self.tz)

    def extract_deadline(
        self,
        text: str,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[Optional[str], Optional[str], DeadlineConfidence]:
        """
        Extract deadline from text string.
        Returns:
            (iso_deadline_str, deadline_expression, confidence)
        """
        now = self.get_current_time(reference_time)
        today = now.date()
        lower = text.lower()

        # 1. Day after tomorrow
        match = re.search(r"\bday after tomorrow\b", lower)
        if match:
            target_date = today + timedelta(days=2)
            target_dt = datetime.combine(target_date, time(18, 0, 0), tzinfo=self.tz)
            return target_dt.isoformat(), match.group(0), DeadlineConfidence.SUGGESTED

        # 2. Tomorrow (with optional time of day)
        match = re.search(r"\btomorrow(?:\s+(morning|afternoon|evening|night|at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?))?\b", lower)
        if match:
            expr = match.group(0)
            target_date = today + timedelta(days=1)
            target_time = time(18, 0, 0)
            confidence = DeadlineConfidence.SUGGESTED

            sub = match.group(1)
            if sub:
                if "morning" in sub:
                    target_time = time(9, 0, 0)
                elif "afternoon" in sub:
                    target_time = time(14, 0, 0)
                elif "evening" in sub or "night" in sub:
                    target_time = time(20, 0, 0)
                elif "at" in sub:
                    try:
                        time_part = dateutil_parse(sub).time()
                        target_time = time_part
                        confidence = DeadlineConfidence.EXACT
                    except Exception:
                        pass
            target_dt = datetime.combine(target_date, target_time, tzinfo=self.tz)
            return target_dt.isoformat(), expr, confidence

        # 3. Today / Tonight / EOD
        match = re.search(r"\b(today|tonight|end of day|by eod)\b", lower)
        if match:
            expr = match.group(0)
            target_time = time(21, 0, 0) if "tonight" in expr else time(18, 0, 0)
            target_dt = datetime.combine(today, target_time, tzinfo=self.tz)
            return target_dt.isoformat(), expr, DeadlineConfidence.SUGGESTED

        # 4. In N days / weeks
        match = re.search(r"\bin\s+(\d+)\s+(day|days|week|weeks)\b", lower)
        if match:
            count = int(match.group(1))
            unit = match.group(2)
            expr = match.group(0)
            days_to_add = count * 7 if "week" in unit else count
            target_date = today + timedelta(days=days_to_add)
            target_dt = datetime.combine(target_date, time(18, 0, 0), tzinfo=self.tz)
            return target_dt.isoformat(), expr, DeadlineConfidence.SUGGESTED

        # 5. Next <Weekday> or This <Weekday> or By <Weekday>
        match = re.search(r"\b(?:(next|this|by)\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b", lower)
        if match:
            prefix = match.group(1) or ""
            day_name = match.group(2)
            expr = match.group(0)
            target_weekday = WEEKDAYS[day_name]
            current_weekday = now.weekday()

            days_ahead = target_weekday - current_weekday
            if prefix == "next":
                days_ahead += 7
            elif days_ahead <= 0:
                days_ahead += 7

            target_date = today + timedelta(days=days_ahead)
            target_dt = datetime.combine(target_date, time(18, 0, 0), tzinfo=self.tz)
            return target_dt.isoformat(), expr, DeadlineConfidence.SUGGESTED

        # 6. Specific date patterns like "by 2026-11-15" or "on Oct 30" or "by 30th October"
        date_pattern = re.search(
            r"\b(?:by|on|before|due)\s+((?:\d{4}-\d{1,2}-\d{1,2})|(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s+\d{4})?)|(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?))\b",
            lower,
        )
        if date_pattern:
            expr = date_pattern.group(0)
            raw_date = date_pattern.group(1)
            # Remove ordinals
            cleaned_date = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw_date)
            try:
                parsed = dateutil_parse(cleaned_date, default=now)
                # If parsed date is in past and year wasn't specified, roll forward to next year
                if parsed.date() < today and not re.search(r"\b\d{4}\b", raw_date):
                    parsed = parsed.replace(year=today.year + 1)
                parsed_dt = parsed.replace(tzinfo=self.tz) if parsed.tzinfo is None else parsed.astimezone(self.tz)
                return parsed_dt.isoformat(), expr, DeadlineConfidence.EXACT
            except Exception:
                pass

        # No deadline explicitly detected
        return None, None, DeadlineConfidence.UNKNOWN


date_parser = DateParser()
