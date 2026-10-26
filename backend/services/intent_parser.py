"""Intent and multi-action semantic parser for Planner Agent."""

from datetime import datetime, date, time, timedelta
import re
from typing import List, Tuple, Optional
from dateutil import tz
from dateutil.parser import parse as dateutil_parse

from backend.models import (
    ProposedEvent,
    ProposedReminder,
    ExtractedTask,
    Priority,
    DeadlineConfidence,
    DeliveryMethod,
)
from backend.services.date_parser import date_parser
from backend.config import settings

MEETING_TRIGGERS = [
    "meeting", "sync", "call", "interview", "appointment", "standup",
    "presentation", "session", "discussion", "demo", "webinar", "workshop"
]


class IntentParser:
    """Parses multi-intent thoughts into events, reminders, and tasks."""

    def __init__(self, timezone_str: Optional[str] = None):
        self.timezone_str = timezone_str or settings.TIMEZONE
        self.tz = tz.gettz(self.timezone_str) or tz.UTC

    def parse_thought(
        self,
        raw_text: str,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[ProposedEvent], List[ProposedReminder], List[ExtractedTask], List[str]]:
        """
        Analyze thought and return (events, reminders, tasks, ambiguities).
        """
        now = date_parser.get_current_time(reference_time)
        today = now.date()
        text = raw_text.strip()
        lower = text.lower()

        events: List[ProposedEvent] = []
        reminders: List[ProposedReminder] = []
        tasks: List[ExtractedTask] = []
        ambiguities: List[str] = []

        # 1. Split compound thought into meaningful action clauses
        clauses = re.split(
            r"(?<=[.!?])\s+|\s+(?:and\s+then|also|additionally)\s+|;\s*|,\s*(?:and\s+)?(?=(?:i\s+have|remind\s+me|prepare|finish|check|email|draft|write|review|schedule|buy|call|need\s+to|have\s+to)\b)|\s+and\s+(?=(?:i\s+have|remind\s+me|prepare|finish|check|email|draft|write|review|schedule|buy|call|need\s+to|have\s+to)\b)",
            text,
            flags=re.IGNORECASE,
        )
        clauses = [c.strip(" ,.-") for c in clauses if c.strip(" ,.-")]

        meeting_clause: Optional[str] = None
        reminder_clause: Optional[str] = None
        task_clauses: List[str] = []

        for c in clauses:
            low_c = c.lower()
            if any(m in low_c for m in MEETING_TRIGGERS) and not low_c.startswith("prepare"):
                meeting_clause = c
            elif "remind" in low_c:
                # Check if reminder clause has a conjoined task: e.g. "remind me 10 minutes before, and draft notes today"
                if re.search(r",?\s+and\s+(?=(?:draft|write|prepare|finish|check|email|buy|call)\b)", c, re.IGNORECASE):
                    sub_parts = re.split(r",?\s+and\s+(?=(?:draft|write|prepare|finish|check|email|buy|call)\b)", c, flags=re.IGNORECASE)
                    reminder_clause = sub_parts[0]
                    for sp in sub_parts[1:]:
                        if sp.strip():
                            task_clauses.append(sp.strip())
                else:
                    reminder_clause = c
            else:
                task_clauses.append(c)

        # Fallback if whole text wasn't separated into distinct clauses
        if not meeting_clause and any(m in lower for m in MEETING_TRIGGERS):
            meeting_clause = text
        if not reminder_clause and "remind" in lower:
            # find reminder part
            rem_m = re.search(r"remind\s+me\s+[^.!?]+", text, re.IGNORECASE)
            if rem_m:
                reminder_clause = rem_m.group(0)

        # 2. Extract Event if meeting clause present
        parsed_event: Optional[ProposedEvent] = None
        if meeting_clause:
            parsed_event, event_ambiguities = self._extract_event(meeting_clause, now)
            if parsed_event:
                events.append(parsed_event)
                ambiguities.extend(event_ambiguities)

        # 3. Extract Reminder if reminder clause present
        if reminder_clause:
            parsed_reminder, rem_ambiguities = self._extract_reminder(
                reminder_clause, parsed_event, now
            )
            if parsed_reminder:
                reminders.append(parsed_reminder)
                ambiguities.extend(rem_ambiguities)

        # 4. Extract Tasks from remaining clauses
        for tc in task_clauses:
            low_tc = tc.lower()
            # Skip if clause was purely the reminder or meeting
            if meeting_clause and tc in meeting_clause:
                continue
            if reminder_clause and tc in reminder_clause:
                continue

            clean_tc = re.sub(r"^(and\s+|i\s+need\s+to|i\s+have\s+to|please\s+|remember\s+to)\s+", "", tc, flags=re.IGNORECASE).strip()
            if len(clean_tc) < 3:
                continue

            iso_deadline, deadline_expr, deadline_conf = date_parser.extract_deadline(clean_tc, reference_time=now)
            
            # Clean title
            clean_title = clean_tc
            if deadline_expr:
                clean_title = re.sub(re.escape(deadline_expr), "", clean_title, flags=re.IGNORECASE).strip(" ,.-")
            clean_title = clean_title[0].upper() + clean_title[1:] if clean_title else clean_tc

            # Category & Next step
            category = "project" if any(w in low_tc for w in ["presentation", "slide", "readme", "model", "code"]) else "general"
            if parsed_event and any(w in low_tc for w in ["prepare", "prep", "presentation", "deck", "notes"]):
                next_step = f"Review requirements and assemble notes for {parsed_event.title}."
                desc = f"Preparation task linked to: {parsed_event.title}"
            else:
                next_step = "Review task details and begin initial draft."
                desc = f"Extracted from: \"{tc}\""

            task = ExtractedTask(
                title=clean_title,
                description=desc,
                priority=Priority.HIGH if "prepare" in low_tc or "urgent" in low_tc else Priority.MEDIUM,
                deadline=iso_deadline,
                deadline_expression=deadline_expr,
                deadline_confidence=deadline_conf,
                deadline_confirmed=False,
                suggested_next_step=next_step,
                category=category,
            )
            tasks.append(task)

        # 5. If nothing extracted at all, produce standard fallback task
        if not events and not reminders and not tasks:
            iso_deadline, deadline_expr, deadline_conf = date_parser.extract_deadline(text, reference_time=now)
            tasks.append(
                ExtractedTask(
                    title=text[:100],
                    description=text,
                    priority=Priority.MEDIUM,
                    deadline=iso_deadline,
                    deadline_expression=deadline_expr,
                    deadline_confidence=deadline_conf,
                    deadline_confirmed=False,
                    suggested_next_step="Review the captured item and define the first concrete action.",
                    category="general",
                )
            )

        return events, reminders, tasks, ambiguities

    def _extract_event(self, clause: str, now: datetime) -> Tuple[Optional[ProposedEvent], List[str]]:
        ambiguities = []
        low = clause.lower()

        # Date extraction
        iso_date, date_expr, _ = date_parser.extract_deadline(clause, reference_time=now)
        event_date = datetime.fromisoformat(iso_date).date() if iso_date else (now.date() + timedelta(days=1))
        if not iso_date:
            ambiguities.append("Meeting date not explicitly specified; assumed tomorrow.")

        # Time extraction: e.g. "at 10 AM", "at 10:30 am", "at 2:00 pm", "at 14:00"
        time_match = re.search(r"\bat\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", low)
        start_t = time(10, 0, 0)  # default
        if time_match:
            raw_time = time_match.group(1).strip()
            try:
                parsed_time = dateutil_parse(raw_time).time()
                start_t = parsed_time
            except Exception:
                ambiguities.append(f"Could not parse meeting time '{raw_time}'; defaulted to 10:00 AM.")
        else:
            ambiguities.append("Meeting time not explicitly specified; defaulted to 10:00 AM.")

        # Duration extraction: e.g. "for 30 minutes", "for 1 hour", "for 45 mins"
        duration_minutes = 30
        dur_match = re.search(r"\bfor\s+(\d+)\s*(minute|minutes|min|mins|hour|hours|hr|hrs)\b", low)
        if dur_match:
            val = int(dur_match.group(1))
            unit = dur_match.group(2)
            if "hour" in unit or "hr" in unit:
                duration_minutes = val * 60
            else:
                duration_minutes = val

        start_dt = datetime.combine(event_date, start_t, tzinfo=self.tz)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # Title cleaning: extract subject like "project meeting"
        clean_title = "Meeting"
        title_match = re.search(r"\b([a-zA-Z0-9_-]+\s+(?:meeting|sync|call|interview|appointment|discussion))\b", clause, re.IGNORECASE)
        if title_match:
            clean_title = title_match.group(1).title()
        else:
            clean_title = "Project Meeting"

        event = ProposedEvent(
            idempotency_key=f"evt_{int(start_dt.timestamp())}_{clean_title.lower().replace(' ', '_')}",
            title=clean_title,
            description=f"Scheduled meeting extracted from: \"{clause.strip()}\"",
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
            duration_minutes=duration_minutes,
            timezone=self.timezone_str,
            is_ambiguous=len(ambiguities) > 0,
            ambiguity_reason="; ".join(ambiguities) if ambiguities else None,
        )
        return event, ambiguities

    def _extract_reminder(
        self,
        clause: str,
        linked_event: Optional[ProposedEvent],
        now: datetime,
    ) -> Tuple[Optional[ProposedReminder], List[str]]:
        ambiguities = []
        low = clause.lower()

        # Check for relative offset: e.g. "15 minutes before", "10 min prior", "1 hour before"
        offset_match = re.search(r"(\d+)\s*(minute|minutes|min|mins|hour|hours|hr|hrs)?\s*(?:before|prior|ahead)", low)
        offset_minutes = 15  # default
        if offset_match:
            val = int(offset_match.group(1))
            unit = offset_match.group(2) or "minutes"
            if "hour" in unit or "hr" in unit:
                offset_minutes = val * 60
            else:
                offset_minutes = val

        # If linked event exists, calculate scheduled_time from event start_time
        if linked_event:
            event_start = datetime.fromisoformat(linked_event.start_time)
            scheduled_dt = event_start - timedelta(minutes=offset_minutes)
            title = f"Reminder: {linked_event.title} in {offset_minutes} minutes"
            target_title = linked_event.title
            target_type = "event"
        else:
            # Standalone reminder: parse absolute or relative time
            iso_deadline, _, _ = date_parser.extract_deadline(clause, reference_time=now)
            if iso_deadline:
                scheduled_dt = datetime.fromisoformat(iso_deadline)
            else:
                scheduled_dt = now + timedelta(hours=1)
                ambiguities.append("Reminder time not clearly specified; defaulted to 1 hour from now.")
            title = f"Reminder: {clause.replace('remind me', '').strip()}"
            target_title = None
            target_type = "custom"

        reminder = ProposedReminder(
            idempotency_key=f"rem_{int(scheduled_dt.timestamp())}_{title.lower()[:30].replace(' ', '_')}",
            title=title,
            scheduled_time=scheduled_dt.isoformat(),
            offset_minutes=offset_minutes if linked_event else None,
            delivery_method=DeliveryMethod.DASHBOARD,
            target_type=target_type,
            target_title=target_title,
        )
        return reminder, ambiguities


intent_parser = IntentParser()
