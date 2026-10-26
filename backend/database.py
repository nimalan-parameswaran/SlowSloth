"""Database layer for SlowSloth using aiosqlite and parameterized queries."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import aiosqlite
from backend.config import settings

# Migration definitions: (version, description, SQL statement)
MIGRATIONS = [
    (
        1,
        "Initial schema with thoughts, tasks, and system_settings",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'captured',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thought_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT CHECK(priority IN ('low', 'medium', 'high')) NOT NULL DEFAULT 'medium',
            deadline TIMESTAMP,
            deadline_expression TEXT,
            deadline_confidence TEXT CHECK(deadline_confidence IN ('exact', 'suggested', 'unknown')) NOT NULL DEFAULT 'unknown',
            deadline_confirmed INTEGER NOT NULL DEFAULT 0,
            suggested_next_step TEXT,
            category TEXT NOT NULL DEFAULT 'general',
            is_completed INTEGER NOT NULL DEFAULT 0,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thought_id) REFERENCES thoughts (id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(is_completed);
        CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
        CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
        CREATE INDEX IF NOT EXISTS idx_tasks_thought_id ON tasks(thought_id);
        """
    ),
    (
        2,
        "Multi-agent schema: calendar accounts, events, outbox sync queue, reminders, and agent activity log",
        """
        -- Calendar integration accounts (OAuth metadata)
        CREATE TABLE IF NOT EXISTS calendar_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL DEFAULT 'google',
            email TEXT,
            client_id TEXT,
            client_secret TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expiry TIMESTAMP,
            csrf_state TEXT,
            is_connected INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Calendar Events
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thought_id INTEGER,
            external_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
            status TEXT CHECK(status IN ('confirmed', 'cancelled')) NOT NULL DEFAULT 'confirmed',
            is_synced INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thought_id) REFERENCES thoughts (id) ON DELETE SET NULL
        );

        -- Outbox Sync Queue for external Google Calendar calls
        CREATE TABLE IF NOT EXISTS calendar_sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            action TEXT CHECK(action IN ('create', 'update', 'delete')) NOT NULL,
            payload TEXT,
            status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) NOT NULL DEFAULT 'pending',
            retry_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES calendar_events (id) ON DELETE CASCADE
        );

        -- Reminders with full lifecycle status
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thought_id INTEGER,
            task_id INTEGER,
            event_id INTEGER,
            title TEXT NOT NULL,
            scheduled_time TIMESTAMP NOT NULL,
            offset_minutes INTEGER,
            delivery_method TEXT CHECK(delivery_method IN ('dashboard', 'google_calendar')) NOT NULL DEFAULT 'dashboard',
            status TEXT CHECK(status IN ('scheduled', 'due', 'delivered', 'acknowledged', 'missed', 'failed', 'cancelled')) NOT NULL DEFAULT 'scheduled',
            idempotency_key TEXT UNIQUE,
            delivered_at TIMESTAMP,
            acknowledged_at TIMESTAMP,
            retry_count INTEGER NOT NULL DEFAULT 0,
            failure_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thought_id) REFERENCES thoughts (id) ON DELETE SET NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
            FOREIGN KEY (event_id) REFERENCES calendar_events (id) ON DELETE CASCADE
        );

        -- Privacy-conscious Agent Activity Log
        CREATE TABLE IF NOT EXISTS agent_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thought_id INTEGER,
            agent_name TEXT NOT NULL,
            action_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            status TEXT CHECK(status IN ('success', 'error', 'skipped')) NOT NULL DEFAULT 'success',
            error_message TEXT,
            latency_ms REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thought_id) REFERENCES thoughts (id) ON DELETE SET NULL
        );

        -- Add idempotency_key to tasks safely if missing
        ALTER TABLE tasks ADD COLUMN idempotency_key TEXT;

        -- Indexes for high-performance edge queries
        CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(start_time);
        CREATE INDEX IF NOT EXISTS idx_calendar_events_status ON calendar_events(status);
        CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON calendar_sync_queue(status);
        CREATE INDEX IF NOT EXISTS idx_reminders_status_time ON reminders(status, scheduled_time);
        CREATE INDEX IF NOT EXISTS idx_agent_activity_created ON agent_activity(created_at);
        """
    )
]


class Database:
    """Async SQLite Database manager with schema migration."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DB_PATH

    def _ensure_dir(self):
        """Ensure parent directory for database exists."""
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def get_connection(self):
        """Context manager yielding an initialized connection with row_factory and foreign keys."""
        self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            yield conn

    async def run_migrations(self):
        """Safely execute pending migrations."""
        self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await conn.commit()

            cursor = await conn.execute("SELECT version FROM schema_migrations;")
            applied_rows = await cursor.fetchall()
            applied_versions = {row[0] for row in applied_rows}

            for version, description, sql in MIGRATIONS:
                if version not in applied_versions:
                    try:
                        await conn.executescript(sql)
                    except aiosqlite.OperationalError as e:
                        if "duplicate column name" in str(e).lower():
                            pass
                        else:
                            raise
                    await conn.execute(
                        "INSERT INTO schema_migrations (version, description) VALUES (?, ?);",
                        (version, description),
                    )
                    await conn.commit()

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a parameterized SQL statement."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor

    async def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """Execute insert and return lastrowid."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.lastrowid

    async def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row as dictionary."""
        async with self.get_connection() as conn:
            async with conn.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return dict(row)

    async def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries."""
        async with self.get_connection() as conn:
            async with conn.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


db = Database()
