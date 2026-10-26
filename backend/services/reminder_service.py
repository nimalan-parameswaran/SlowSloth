"""Reminder management service with restart recovery and delivery status lifecycle."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from backend.database import db
from backend.models import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderStatus,
    DeliveryMethod,
)
from backend.services.date_parser import date_parser


class ReminderService:
    """Manages reminder persistence, restart recovery, and status transitions."""

    async def schedule_reminder(
        self,
        reminder_in: ReminderCreate,
        thought_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> ReminderResponse:
        """Schedule a new reminder with idempotency protection."""
        now_iso = date_parser.get_current_time().isoformat()

        # Check idempotency
        if idempotency_key:
            existing = await db.fetch_one(
                "SELECT * FROM reminders WHERE idempotency_key = ?;",
                (idempotency_key,),
            )
            if existing:
                return self._row_to_reminder(existing)

        insert_sql = """
        INSERT INTO reminders (
            thought_id, task_id, event_id, title, scheduled_time,
            offset_minutes, delivery_method, status, idempotency_key,
            retry_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, 0, ?, ?);
        """
        reminder_id = await db.execute_insert(
            insert_sql,
            (
                thought_id,
                reminder_in.task_id,
                reminder_in.event_id,
                reminder_in.title,
                reminder_in.scheduled_time,
                reminder_in.offset_minutes,
                reminder_in.delivery_method.value,
                idempotency_key,
                now_iso,
                now_iso,
            ),
        )

        created = await self.get_reminder_by_id(reminder_id)
        if not created:
            raise RuntimeError("Failed to retrieve created reminder")
        return created

    async def get_reminder_by_id(self, reminder_id: int) -> Optional[ReminderResponse]:
        """Retrieve single reminder by ID."""
        row = await db.fetch_one("SELECT * FROM reminders WHERE id = ?;", (reminder_id,))
        if not row:
            return None
        return self._row_to_reminder(row)

    async def list_reminders(
        self,
        status: Optional[ReminderStatus] = None,
        delivery_method: Optional[DeliveryMethod] = None,
    ) -> List[ReminderResponse]:
        """List reminders filtered by status or delivery method."""
        clauses = []
        params = []

        if status:
            clauses.append("status = ?")
            params.append(status.value)
        if delivery_method:
            clauses.append("delivery_method = ?")
            params.append(delivery_method.value)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT * FROM reminders
        {where_sql}
        ORDER BY scheduled_time ASC;
        """
        rows = await db.fetch_all(sql, tuple(params))
        return [self._row_to_reminder(r) for r in rows]

    async def acknowledge_reminder(self, reminder_id: int) -> Optional[ReminderResponse]:
        """Mark reminder as acknowledged by user."""
        now_iso = date_parser.get_current_time().isoformat()
        sql = """
        UPDATE reminders SET
            status = 'acknowledged',
            acknowledged_at = ?,
            updated_at = ?
        WHERE id = ?;
        """
        await db.execute(sql, (now_iso, now_iso, reminder_id))
        return await self.get_reminder_by_id(reminder_id)

    async def cancel_reminder(self, reminder_id: int) -> bool:
        """Cancel a reminder."""
        now_iso = date_parser.get_current_time().isoformat()
        sql = "UPDATE reminders SET status = 'cancelled', updated_at = ? WHERE id = ?;"
        cursor = await db.execute(sql, (now_iso, reminder_id))
        return cursor.rowcount > 0

    async def recover_and_process_pending(self) -> Dict[str, int]:
        """
        Restart recovery & delivery engine:
        Scans all reminders in 'scheduled' status where scheduled_time <= NOW().
        If scheduled_time is > 1 hour in the past, marks 'missed'.
        Otherwise marks 'delivered' with delivered_at timestamp.
        """
        now = date_parser.get_current_time()
        now_iso = now.isoformat()
        one_hour_ago = now - timedelta(hours=1)

        pending = await db.fetch_all(
            "SELECT * FROM reminders WHERE status = 'scheduled' AND scheduled_time <= ?;",
            (now_iso,),
        )

        counts = {"delivered": 0, "missed": 0}

        for r in pending:
            sched_time = datetime.fromisoformat(r["scheduled_time"])
            if sched_time < one_hour_ago:
                # Server was down or reminder is severely past due
                await db.execute(
                    """
                    UPDATE reminders SET
                        status = 'missed',
                        failure_reason = 'Server was offline or reminder was past due by >1h',
                        updated_at = ?
                    WHERE id = ?;
                    """,
                    (now_iso, r["id"]),
                )
                counts["missed"] += 1
            else:
                # Deliver to dashboard
                await db.execute(
                    """
                    UPDATE reminders SET
                        status = 'delivered',
                        delivered_at = ?,
                        updated_at = ?
                    WHERE id = ?;
                    """,
                    (now_iso, now_iso, r["id"]),
                )
                counts["delivered"] += 1

        return counts

    def _row_to_reminder(self, r: Dict[str, Any]) -> ReminderResponse:
        return ReminderResponse(
            id=r["id"],
            thought_id=r.get("thought_id"),
            task_id=r.get("task_id"),
            event_id=r.get("event_id"),
            title=r["title"],
            scheduled_time=str(r["scheduled_time"]),
            offset_minutes=r.get("offset_minutes"),
            delivery_method=DeliveryMethod(r["delivery_method"]),
            status=ReminderStatus(r["status"]),
            delivered_at=str(r["delivered_at"]) if r.get("delivered_at") else None,
            acknowledged_at=str(r["acknowledged_at"]) if r.get("acknowledged_at") else None,
            failure_reason=r.get("failure_reason"),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )


reminder_service = ReminderService()
