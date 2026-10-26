"""Tests for Calendar Service, agenda listing, and outbox sync queue."""

from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from backend.services.date_parser import date_parser
from backend.database import db


@pytest.mark.asyncio
async def test_calendar_crud_and_outbox(async_client: AsyncClient):
    now = date_parser.get_current_time()
    start_iso = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0).isoformat()
    end_iso = (now + timedelta(days=1)).replace(hour=15, minute=0, second=0).isoformat()

    # 1. Create event
    create_payload = {
        "title": "Architecture Review",
        "description": "Discuss edge memory optimizations",
        "start_time": start_iso,
        "end_time": end_iso,
        "timezone": "Asia/Kolkata",
    }
    create_resp = await async_client.post("/api/calendar/events", json=create_payload)
    assert create_resp.status_code == 201
    event = create_resp.json()
    assert event["id"] is not None
    assert event["title"] == "Architecture Review"
    assert event["status"] == "confirmed"

    # Verify Outbox queue entry created
    outbox_items = await db.fetch_all("SELECT * FROM calendar_sync_queue WHERE event_id = ?;", (event["id"],))
    assert len(outbox_items) == 1
    assert outbox_items[0]["action"] == "create"
    assert outbox_items[0]["status"] == "pending"

    # 2. Update event
    update_payload = {"title": "Architecture & Memory Review"}
    put_resp = await async_client.put(f"/api/calendar/events/{event['id']}", json=update_payload)
    assert put_resp.status_code == 200
    assert put_resp.json()["title"] == "Architecture & Memory Review"

    # Verify Update Outbox entry
    outbox_items = await db.fetch_all("SELECT * FROM calendar_sync_queue WHERE event_id = ?;", (event["id"],))
    assert len(outbox_items) == 2

    # 3. Cancel event
    del_resp = await async_client.delete(f"/api/calendar/events/{event['id']}")
    assert del_resp.status_code == 204

    # Cancelled event should not appear in active confirmed agenda
    list_resp = await async_client.get("/api/calendar/events?status=confirmed")
    assert len(list_resp.json()) == 0
