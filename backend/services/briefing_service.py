"""Daily briefing generator strictly grounded in SQLite database state."""

from datetime import datetime, timedelta
from typing import Dict, List
from backend.models import (
    BriefingResponse,
    BriefingSection,
    TaskResponse,
    TaskView,
    Priority,
)
from backend.services.task_service import task_service
from backend.services.calendar_service import calendar_service
from backend.services.date_parser import date_parser
from backend.config import settings


class BriefingService:
    """Produces on-demand daily briefings grounded in stored tasks and calendar events."""

    async def generate_briefing(self) -> BriefingResponse:
        now = date_parser.get_current_time()
        now_iso = now.isoformat()

        # Fetch categorized task slices
        overdue_tasks = await task_service.get_tasks(view=TaskView.OVERDUE)
        today_tasks = await task_service.get_tasks(view=TaskView.TODAY)
        upcoming_tasks_all = await task_service.get_tasks(view=TaskView.UPCOMING)

        # Check today's calendar events
        today_start_iso = datetime.combine(now.date(), datetime.min.time(), tzinfo=now.tzinfo).isoformat()
        today_end_iso = datetime.combine(now.date(), datetime.max.time(), tzinfo=now.tzinfo).isoformat()
        today_events = await calendar_service.list_events(start_date=today_start_iso, end_date=today_end_iso)

        # Filter upcoming to next 3 days
        three_days_future = (now + timedelta(days=3)).date()
        upcoming_tasks = [
            t for t in upcoming_tasks_all
            if t.deadline and datetime.fromisoformat(t.deadline).date() <= three_days_future
        ]

        # Incomplete high-priority tasks without deadlines
        inbox_tasks = await task_service.get_tasks(view=TaskView.INBOX)
        high_priority_inbox = [t for t in inbox_tasks if t.priority == Priority.HIGH]

        total_open = len(overdue_tasks) + len(today_tasks) + len(upcoming_tasks_all) + len(inbox_tasks)

        # Build readable grounded executive summary
        summary_sentences = []
        if total_open == 0 and len(today_events) == 0:
            summary = "You're all caught up! There are no open tasks or upcoming deadlines recorded in your SlowSloth notebook."
        else:
            summary_sentences.append(f"Good day! You currently have {total_open} active task{'s' if total_open != 1 else ''}.")
            if today_events:
                event_titles = ", ".join(f'"{e.title}"' for e in today_events[:2])
                summary_sentences.append(
                    f"Scheduled today: {len(today_events)} calendar event{'s' if len(today_events) != 1 else ''} ({event_titles})."
                )
            if overdue_tasks:
                summary_sentences.append(
                    f"Attention needed: {len(overdue_tasks)} task{'s are' if len(overdue_tasks) != 1 else ' is'} overdue, starting with \"{overdue_tasks[0].title}\"."
                )
            if today_tasks:
                summary_sentences.append(
                    f"Due today: {len(today_tasks)} item{'s' if len(today_tasks) != 1 else ''} scheduled, including \"{today_tasks[0].title}\"."
                )
            elif not overdue_tasks and not today_events:
                summary_sentences.append("No immediate deadlines are due today.")

            if high_priority_inbox:
                summary_sentences.append(
                    f"Notice: You have {len(high_priority_inbox)} high-priority item{'s' if len(high_priority_inbox) != 1 else ''} waiting in your inbox without a confirmed deadline."
                )

            summary = " ".join(summary_sentences)

        sections: Dict[str, BriefingSection] = {
            "overdue": BriefingSection(
                title="Overdue Tasks",
                count=len(overdue_tasks),
                tasks=overdue_tasks,
            ),
            "today": BriefingSection(
                title="Due Today",
                count=len(today_tasks),
                tasks=today_tasks,
            ),
            "upcoming": BriefingSection(
                title="Upcoming in Next 3 Days",
                count=len(upcoming_tasks),
                tasks=upcoming_tasks,
            ),
            "high_priority_inbox": BriefingSection(
                title="High Priority Without Deadline",
                count=len(high_priority_inbox),
                tasks=high_priority_inbox,
            ),
        }

        # Log activity
        from backend.services.agent_service import ActivityLogger
        await ActivityLogger.log(
            agent_name="briefing",
            action_type="generate_briefing",
            summary=f"Compiled daily briefing: {total_open} open tasks, {len(today_events)} events.",
        )

        return BriefingResponse(
            summary=summary,
            generated_at=now_iso,
            timezone=settings.TIMEZONE,
            total_open_tasks=total_open,
            sections=sections,
        )


briefing_service = BriefingService()
