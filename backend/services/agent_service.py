"""Multi-Agent Coordinator, Planner Agent, and Activity Logger."""

from datetime import datetime
import time
from typing import List, Optional, Dict, Any

from backend.database import db
from backend.models import (
    MultiActionBundle,
    ExecuteBundleRequest,
    ExecutionResult,
    ExtractedTask,
    ProposedEvent,
    ProposedReminder,
    TaskResponse,
    CalendarEventResponse,
    ReminderResponse,
    AgentActivityResponse,
    CalendarEventCreate,
    ReminderCreate,
)
from backend.services.intent_parser import intent_parser
from backend.services.task_service import task_service
from backend.services.calendar_service import calendar_service
from backend.services.reminder_service import reminder_service
from backend.services.date_parser import date_parser


class ActivityLogger:
    """Privacy-safe agent activity logger."""

    @staticmethod
    async def log(
        agent_name: str,
        action_type: str,
        summary: str,
        status: str = "success",
        error_message: Optional[str] = None,
        thought_id: Optional[int] = None,
        latency_ms: Optional[float] = None,
    ):
        sql = """
        INSERT INTO agent_activity (
            thought_id, agent_name, action_type, summary,
            status, error_message, latency_ms, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        now_iso = date_parser.get_current_time().isoformat()
        await db.execute(
            sql,
            (
                thought_id,
                agent_name,
                action_type,
                summary,
                status,
                error_message,
                round(latency_ms, 2) if latency_ms else None,
                now_iso,
            ),
        )

    @staticmethod
    async def get_recent_activity(limit: int = 50) -> List[AgentActivityResponse]:
        sql = """
        SELECT * FROM agent_activity
        ORDER BY id DESC
        LIMIT ?;
        """
        rows = await db.fetch_all(sql, (limit,))
        return [
            AgentActivityResponse(
                id=r["id"],
                thought_id=r.get("thought_id"),
                agent_name=r["agent_name"],
                action_type=r["action_type"],
                summary=r["summary"],
                status=r["status"],
                error_message=r.get("error_message"),
                latency_ms=r.get("latency_ms"),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]


class PlannerAgent:
    """Orchestrates thought intake, intent classification, and action proposal."""

    async def plan(self, raw_thought: str) -> MultiActionBundle:
        start_time = time.perf_counter()
        now_iso = date_parser.get_current_time().isoformat()

        # Persist thought record in SQLite
        thought_id = await task_service.create_thought(raw_thought)

        # Parse multi-intent thought using deterministic semantic rules
        events, reminders, tasks, ambiguities = intent_parser.parse_thought(raw_thought)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Construct planner notes
        notes = []
        if events:
            notes.append(f"Identified {len(events)} calendar event(s).")
        if reminders:
            notes.append(f"Identified {len(reminders)} scheduled reminder(s).")
        if tasks:
            notes.append(f"Identified {len(tasks)} actionable task(s).")
        if ambiguities:
            notes.append(f"Ambiguities flagged: {len(ambiguities)}.")

        # Log Planner activity
        await ActivityLogger.log(
            agent_name="planner",
            action_type="plan_thought",
            summary=f"Parsed thought into {len(tasks)} task(s), {len(events)} event(s), {len(reminders)} reminder(s).",
            status="success",
            thought_id=thought_id,
            latency_ms=latency_ms,
        )

        return MultiActionBundle(
            thought_id=thought_id,
            raw_thought=raw_thought,
            tasks=tasks,
            events=events,
            reminders=reminders,
            ambiguities=ambiguities,
            planner_notes=" ".join(notes),
            processing_time_ms=round(latency_ms, 2),
            created_at=now_iso,
        )


class CoordinatorAgent:
    """Executes user-approved action bundle across specialist agents."""

    async def execute_bundle(self, req: ExecuteBundleRequest) -> ExecutionResult:
        start_time = time.perf_counter()
        created_tasks: List[TaskResponse] = []
        created_events: List[CalendarEventResponse] = []
        created_reminders: List[ReminderResponse] = []

        # 1. Execute Task Agent
        if req.tasks:
            t_start = time.perf_counter()
            created_tasks = await task_service.confirm_thought_tasks(
                thought_id=req.thought_id,
                tasks=req.tasks,
            )
            await ActivityLogger.log(
                agent_name="task",
                action_type="create_tasks",
                summary=f"Created {len(created_tasks)} confirmed task(s).",
                thought_id=req.thought_id,
                latency_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        # 2. Execute Calendar Agent
        event_map: Dict[str, int] = {}
        if req.events:
            c_start = time.perf_counter()
            for evt in req.events:
                created_evt = await calendar_service.create_event(
                    CalendarEventCreate(
                        title=evt.title,
                        description=evt.description,
                        start_time=evt.start_time,
                        end_time=evt.end_time,
                        timezone=evt.timezone,
                    ),
                    thought_id=req.thought_id,
                    idempotency_key=evt.idempotency_key,
                )
                created_events.append(created_evt)
                event_map[evt.title.lower()] = created_evt.id

            await ActivityLogger.log(
                agent_name="calendar",
                action_type="create_events",
                summary=f"Created {len(created_events)} calendar event(s) and queued for sync.",
                thought_id=req.thought_id,
                latency_ms=(time.perf_counter() - c_start) * 1000.0,
            )

        # 3. Execute Reminder Agent
        if req.reminders:
            r_start = time.perf_counter()
            for rem in req.reminders:
                # Link reminder to created event if title matches
                linked_event_id = None
                if rem.target_title and rem.target_title.lower() in event_map:
                    linked_event_id = event_map[rem.target_title.lower()]
                elif created_events:
                    linked_event_id = created_events[0].id

                created_rem = await reminder_service.schedule_reminder(
                    ReminderCreate(
                        title=rem.title,
                        scheduled_time=rem.scheduled_time,
                        offset_minutes=rem.offset_minutes,
                        delivery_method=rem.delivery_method,
                        event_id=linked_event_id,
                    ),
                    thought_id=req.thought_id,
                    idempotency_key=rem.idempotency_key,
                )
                created_reminders.append(created_rem)

            await ActivityLogger.log(
                agent_name="reminder",
                action_type="schedule_reminders",
                summary=f"Scheduled {len(created_reminders)} reminder(s).",
                thought_id=req.thought_id,
                latency_ms=(time.perf_counter() - r_start) * 1000.0,
            )

        # Mark thought as confirmed
        await db.execute(
            "UPDATE thoughts SET status = 'executed' WHERE id = ?;",
            (req.thought_id,),
        )

        return ExecutionResult(
            thought_id=req.thought_id,
            created_tasks=created_tasks,
            created_events=created_events,
            created_reminders=created_reminders,
            activity_count=len(created_tasks) + len(created_events) + len(created_reminders),
        )


planner_agent = PlannerAgent()
coordinator_agent = CoordinatorAgent()
