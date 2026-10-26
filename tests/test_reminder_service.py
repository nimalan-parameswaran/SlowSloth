"""Tests for Reminder Service lifecycle, restart recovery, and status transitions."""

from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from backend.services.date_parser import date_parser
from backend.services.reminder_service import reminder_service
from backend.database import db


@pytest.mark.asyncio
async def test_reminder_lifecycle(async_client: AsyncClient):
    now = date_parser.get_current_time()
    sched_iso = (now + timedelta(hours=2)).isoformat()

    # 1. Schedule reminder
    create_resp = await async_client.post(
        "/api/reminders",
        json={
            "title": "Check battery test setup",
            "scheduled_time": sched_iso,
            "delivery_method": "dashboard",
        },
    )
    assert create_resp.status_code == 201
    rem = create_resp.json()
    assert rem["status"] == "scheduled"
    reminder_id = rem["id"]

    # 2. Acknowledge reminder
    ack_resp = await async_client.patch(f"/api/reminders/{reminder_id}/acknowledge")
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    # 3. Cancel reminder
    del_resp = await async_client.delete(f"/api/reminders/{reminder_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_restart_recovery_and_missed_status():
    now = date_parser.get_current_time()
    # 1. Reminder due 10 minutes ago (within 1 hour) -> should be delivered
    due_recent_iso = (now - timedelta(minutes=10)).isoformat()
    # 2. Reminder due 3 hours ago (> 1 hour) -> should be marked missed
    due_old_iso = (now - timedelta(hours=3)).isoformat()

    r1_id = await db.execute_insert(
        """
        INSERT INTO reminders (title, scheduled_time, delivery_method, status, created_at, updated_at)
        VALUES ('Recent reminder', ?, 'dashboard', 'scheduled', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """,
        (due_recent_iso,),
    )
    r2_id = await db.execute_insert(
        """
        INSERT INTO reminders (title, scheduled_time, delivery_method, status, created_at, updated_at)
        VALUES ('Old reminder', ?, 'dashboard', 'scheduled', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """,
        (due_old_iso,),
    )

    # Trigger restart recovery
    counts = await reminder_service.recover_and_process_pending()
    assert counts["delivered"] >= 1
    assert counts["missed"] >= 1

    r1 = await reminder_service.get_reminder_by_id(r1_id)
    assert r1.status.value == "delivered"
    assert r1.delivered_at is not None

    r2 = await reminder_service.get_reminder_by_id(r2_id)
    assert r2.status.value == "missed"
    assert r2.failure_reason is not None
