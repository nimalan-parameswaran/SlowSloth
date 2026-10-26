"""Tests for SQLite persistence, schema migrations, and database constraints."""

import pytest
from backend.database import db


@pytest.mark.asyncio
async def test_migration_idempotency():
    # Calling run_migrations multiple times should succeed cleanly
    await db.run_migrations()
    await db.run_migrations()

    rows = await db.fetch_all("SELECT version, description FROM schema_migrations;")
    assert len(rows) >= 1
    assert rows[0]["version"] == 1


@pytest.mark.asyncio
async def test_data_persistence_across_connections():
    thought_sql = "INSERT INTO thoughts (raw_text, status) VALUES (?, 'captured');"
    thought_id = await db.execute_insert(thought_sql, ("Sample test thought",))

    task_sql = """
    INSERT INTO tasks (thought_id, title, priority, deadline_confidence, category)
    VALUES (?, 'Persisted Task', 'high', 'unknown', 'project');
    """
    task_id = await db.execute_insert(task_sql, (thought_id,))

    # Query afresh through a new query call
    row = await db.fetch_one("SELECT * FROM tasks WHERE id = ?;", (task_id,))
    assert row is not None
    assert row["title"] == "Persisted Task"
    assert row["priority"] == "high"
    assert row["thought_id"] == thought_id


@pytest.mark.asyncio
async def test_foreign_key_on_delete_set_null():
    thought_id = await db.execute_insert(
        "INSERT INTO thoughts (raw_text, status) VALUES (?, 'captured');",
        ("Parent thought",),
    )
    task_id = await db.execute_insert(
        "INSERT INTO tasks (thought_id, title, priority, deadline_confidence) VALUES (?, 'Child task', 'medium', 'unknown');",
        (thought_id,),
    )

    # Delete parent thought
    await db.execute("DELETE FROM thoughts WHERE id = ?;", (thought_id,))

    # Child task should still exist, with thought_id set to NULL
    task = await db.fetch_one("SELECT * FROM tasks WHERE id = ?;", (task_id,))
    assert task is not None
    assert task["thought_id"] is None
