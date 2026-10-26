"""Tests for daily briefing generation and database grounding."""

from datetime import timedelta
import pytest
from httpx import AsyncClient
from backend.services.date_parser import date_parser


@pytest.mark.asyncio
async def test_empty_briefing(async_client: AsyncClient):
    resp = await async_client.get("/api/briefing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_open_tasks"] == 0
    assert "caught up" in data["summary"].lower()


@pytest.mark.asyncio
async def test_grounded_briefing_with_tasks(async_client: AsyncClient):
    now = date_parser.get_current_time()
    yesterday_iso = (now - timedelta(days=2)).isoformat()
    today_iso = now.isoformat()

    # 1. Overdue task
    await async_client.post(
        "/api/tasks",
        json={"title": "Fix memory leak in edge loop", "deadline": yesterday_iso, "priority": "high"},
    )
    # 2. Due today
    await async_client.post(
        "/api/tasks",
        json={"title": "Submit draft report", "deadline": today_iso, "priority": "medium"},
    )
    # 3. High priority inbox
    await async_client.post(
        "/api/tasks",
        json={"title": "Order replacement parts", "priority": "high", "deadline": None},
    )

    resp = await async_client.get("/api/briefing")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_open_tasks"] == 3
    assert data["sections"]["overdue"]["count"] == 1
    assert data["sections"]["today"]["count"] == 1
    assert data["sections"]["high_priority_inbox"]["count"] == 1

    summary = data["summary"]
    assert "Fix memory leak in edge loop" in summary
    assert "Submit draft report" in summary
