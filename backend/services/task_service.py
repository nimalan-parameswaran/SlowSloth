"""Task management service for database CRUD and status operations."""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from backend.database import db
from backend.models import (
    TaskResponse,
    ExtractedTask,
    TaskCreate,
    TaskUpdate,
    TaskView,
    Priority,
    DeadlineConfidence,
)
from backend.services.date_parser import date_parser


class TaskService:
    """Service handling task persistence and query filters."""

    async def create_thought(self, raw_text: str) -> int:
        """Persist a captured raw thought and return its ID."""
        sql = "INSERT INTO thoughts (raw_text, status) VALUES (?, 'captured');"
        return await db.execute_insert(sql, (raw_text,))

    async def get_thought(self, thought_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a thought record by ID."""
        sql = "SELECT id, raw_text, status, created_at FROM thoughts WHERE id = ?;"
        return await db.fetch_one(sql, (thought_id,))

    async def confirm_thought_tasks(
        self,
        thought_id: int,
        tasks: List[ExtractedTask],
    ) -> List[TaskResponse]:
        """
        Confirm and persist extracted tasks for a thought.
        Guards against duplicate confirmations for the same thought.
        """
        thought = await self.get_thought(thought_id)
        if not thought:
            raise ValueError(f"Thought with id {thought_id} not found.")

        if thought["status"] == "confirmed":
            # If already confirmed, retrieve existing tasks to prevent duplicates
            existing_sql = "SELECT * FROM tasks WHERE thought_id = ? ORDER BY id ASC;"
            rows = await db.fetch_all(existing_sql, (thought_id,))
            return [self._row_to_task(r) for r in rows]

        saved_tasks: List[TaskResponse] = []
        now_iso = date_parser.get_current_time().isoformat()

        insert_sql = """
        INSERT INTO tasks (
            thought_id, title, description, priority, deadline,
            deadline_expression, deadline_confidence, deadline_confirmed,
            suggested_next_step, category, is_completed, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
        """

        for t in tasks:
            task_id = await db.execute_insert(
                insert_sql,
                (
                    thought_id,
                    t.title,
                    t.description,
                    t.priority.value,
                    t.deadline,
                    t.deadline_expression,
                    t.deadline_confidence.value,
                    1 if t.deadline_confirmed else 0,
                    t.suggested_next_step,
                    t.category,
                    now_iso,
                    now_iso,
                ),
            )
            created = await self.get_task_by_id(task_id)
            if created:
                saved_tasks.append(created)

        # Mark thought as confirmed
        await db.execute(
            "UPDATE thoughts SET status = 'confirmed' WHERE id = ?;",
            (thought_id,),
        )

        return saved_tasks

    async def create_manual_task(self, task_in: TaskCreate) -> TaskResponse:
        """Manually create a single task."""
        now_iso = date_parser.get_current_time().isoformat()
        confidence = DeadlineConfidence.EXACT if task_in.deadline else DeadlineConfidence.UNKNOWN
        
        insert_sql = """
        INSERT INTO tasks (
            thought_id, title, description, priority, deadline,
            deadline_expression, deadline_confidence, deadline_confirmed,
            suggested_next_step, category, is_completed, created_at, updated_at
        ) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
        """
        task_id = await db.execute_insert(
            insert_sql,
            (
                task_in.title,
                task_in.description,
                task_in.priority.value,
                task_in.deadline,
                task_in.deadline_expression,
                confidence.value,
                1 if task_in.deadline_confirmed else 0,
                task_in.suggested_next_step,
                task_in.category,
                now_iso,
                now_iso,
            ),
        )
        task = await self.get_task_by_id(task_id)
        if not task:
            raise RuntimeError("Failed to retrieve created task")
        return task

    async def get_task_by_id(self, task_id: int) -> Optional[TaskResponse]:
        """Fetch a single task by ID."""
        sql = "SELECT * FROM tasks WHERE id = ?;"
        row = await db.fetch_one(sql, (task_id,))
        if not row:
            return None
        return self._row_to_task(row)

    async def update_task(self, task_id: int, update: TaskUpdate) -> Optional[TaskResponse]:
        """Update fields on an existing task."""
        existing = await self.get_task_by_id(task_id)
        if not existing:
            return None

        updates = []
        params = []

        if update.title is not None:
            updates.append("title = ?")
            params.append(update.title)
        if update.description is not None:
            updates.append("description = ?")
            params.append(update.description)
        if update.priority is not None:
            updates.append("priority = ?")
            params.append(update.priority.value)
        if update.deadline is not None:
            updates.append("deadline = ?")
            params.append(update.deadline)
        if update.deadline_expression is not None:
            updates.append("deadline_expression = ?")
            params.append(update.deadline_expression)
        if update.deadline_confirmed is not None:
            updates.append("deadline_confirmed = ?")
            params.append(1 if update.deadline_confirmed else 0)
        if update.suggested_next_step is not None:
            updates.append("suggested_next_step = ?")
            params.append(update.suggested_next_step)
        if update.category is not None:
            updates.append("category = ?")
            params.append(update.category)
        if update.is_completed is not None:
            updates.append("is_completed = ?")
            params.append(1 if update.is_completed else 0)
            if update.is_completed:
                updates.append("completed_at = ?")
                params.append(date_parser.get_current_time().isoformat())
            else:
                updates.append("completed_at = NULL")

        if not updates:
            return existing

        now_iso = date_parser.get_current_time().isoformat()
        updates.append("updated_at = ?")
        params.append(now_iso)

        params.append(task_id)
        sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?;"
        await db.execute(sql, tuple(params))
        return await self.get_task_by_id(task_id)

    async def toggle_complete(self, task_id: int) -> Optional[TaskResponse]:
        """Toggle task completion state (completing or reopening)."""
        existing = await self.get_task_by_id(task_id)
        if not existing:
            return None

        now_iso = date_parser.get_current_time().isoformat()
        if existing.is_completed:
            # Reopen
            sql = "UPDATE tasks SET is_completed = 0, completed_at = NULL, updated_at = ? WHERE id = ?;"
            await db.execute(sql, (now_iso, task_id))
        else:
            # Complete
            sql = "UPDATE tasks SET is_completed = 1, completed_at = ?, updated_at = ? WHERE id = ?;"
            await db.execute(sql, (now_iso, now_iso, task_id))

        return await self.get_task_by_id(task_id)

    async def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID."""
        sql = "DELETE FROM tasks WHERE id = ?;"
        cursor = await db.execute(sql, (task_id,))
        return cursor.rowcount > 0

    async def get_tasks(
        self,
        view: TaskView = TaskView.ALL,
        priority: Optional[Priority] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[TaskResponse]:
        """Filter tasks according to view, priority, category, and search query."""
        now = date_parser.get_current_time()
        today_start_iso = datetime.combine(now.date(), datetime.min.time(), tzinfo=now.tzinfo).isoformat()
        today_end_iso = datetime.combine(now.date(), datetime.max.time(), tzinfo=now.tzinfo).isoformat()

        clauses = []
        params = []

        if view == TaskView.TODAY:
            clauses.append("is_completed = 0")
            clauses.append("deadline >= ? AND deadline <= ?")
            params.extend([today_start_iso, today_end_iso])
        elif view == TaskView.UPCOMING:
            clauses.append("is_completed = 0")
            clauses.append("deadline > ?")
            params.append(today_end_iso)
        elif view == TaskView.OVERDUE:
            clauses.append("is_completed = 0")
            clauses.append("deadline < ?")
            params.append(today_start_iso)
        elif view == TaskView.INBOX:
            clauses.append("is_completed = 0")
            clauses.append("(deadline IS NULL OR deadline = '')")

        if priority is not None:
            clauses.append("priority = ?")
            params.append(priority.value)

        if category and category.lower() != "all":
            clauses.append("LOWER(category) = ?")
            params.append(category.lower())

        if search and search.strip():
            query_term = f"%{search.strip().lower()}%"
            clauses.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
            params.extend([query_term, query_term])

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT * FROM tasks
        {where_stmt}
        ORDER BY
            is_completed ASC,
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END ASC,
            deadline ASC NULLS LAST,
            id DESC;
        """
        rows = await db.fetch_all(sql, tuple(params))
        return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, r: Dict[str, Any]) -> TaskResponse:
        return TaskResponse(
            id=r["id"],
            thought_id=r.get("thought_id"),
            title=r["title"],
            description=r.get("description"),
            priority=Priority(r["priority"]),
            deadline=r.get("deadline"),
            deadline_expression=r.get("deadline_expression"),
            deadline_confidence=DeadlineConfidence(r.get("deadline_confidence") or "unknown"),
            deadline_confirmed=bool(r.get("deadline_confirmed")),
            suggested_next_step=r.get("suggested_next_step"),
            category=r.get("category") or "general",
            is_completed=bool(r["is_completed"]),
            completed_at=r.get("completed_at"),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )


task_service = TaskService()
