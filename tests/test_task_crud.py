"""Tests for task CRUD endpoints, filters, search, and completion/reopening."""

from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from backend.services.date_parser import date_parser


@pytest.mark.asyncio
async def test_task_create_and_read(async_client: AsyncClient):
    payload = {
        "title": "Build battery thermal model",
        "description": "Simulation for edge devices",
        "priority": "high",
        "deadline": None,
        "suggested_next_step": "Define cell parameters",
        "category": "project",
    }
    resp = await async_client.post("/api/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["priority"] == "high"
    assert data["is_completed"] is False

    task_id = data["id"]
    get_resp = await async_client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == task_id


@pytest.mark.asyncio
async def test_task_update(async_client: AsyncClient):
    create_resp = await async_client.post(
        "/api/tasks",
        json={"title": "Draft paper", "priority": "medium"},
    )
    task_id = create_resp.json()["id"]

    update_payload = {
        "title": "Draft revised conference paper",
        "priority": "high",
        "category": "publication",
    }
    put_resp = await async_client.put(f"/api/tasks/{task_id}", json=update_payload)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["title"] == "Draft revised conference paper"
    assert updated_data["priority"] == "high"
    assert updated_data["category"] == "publication"


@pytest.mark.asyncio
async def test_task_complete_and_reopen(async_client: AsyncClient):
    create_resp = await async_client.post("/api/tasks", json={"title": "Test toggle task"})
    task_id = create_resp.json()["id"]

    # 1. Complete
    complete_resp = await async_client.patch(f"/api/tasks/{task_id}/complete")
    assert complete_resp.status_code == 200
    comp_data = complete_resp.json()
    assert comp_data["is_completed"] is True
    assert comp_data["completed_at"] is not None

    # 2. Reopen
    reopen_resp = await async_client.patch(f"/api/tasks/{task_id}/complete")
    assert reopen_resp.status_code == 200
    reopen_data = reopen_resp.json()
    assert reopen_data["is_completed"] is False
    assert reopen_data["completed_at"] is None


@pytest.mark.asyncio
async def test_task_deletion(async_client: AsyncClient):
    create_resp = await async_client.post("/api/tasks", json={"title": "Temporary task"})
    task_id = create_resp.json()["id"]

    del_resp = await async_client.delete(f"/api/tasks/{task_id}")
    assert del_resp.status_code == 204

    # Verify 404 on subsequent get
    get_resp = await async_client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_view_filters(async_client: AsyncClient):
    now = date_parser.get_current_time()
    today_iso = now.isoformat()
    yesterday_iso = (now - timedelta(days=2)).isoformat()
    next_week_iso = (now + timedelta(days=5)).isoformat()

    # 1. Overdue task
    await async_client.post("/api/tasks", json={"title": "Overdue item", "deadline": yesterday_iso})
    # 2. Due today
    await async_client.post("/api/tasks", json={"title": "Today item", "deadline": today_iso})
    # 3. Upcoming item
    await async_client.post("/api/tasks", json={"title": "Future item", "deadline": next_week_iso})
    # 4. Inbox item (no deadline)
    await async_client.post("/api/tasks", json={"title": "Inbox item", "deadline": None})

    # Test Today filter
    resp_today = await async_client.get("/api/tasks?view=today")
    assert len(resp_today.json()) == 1
    assert resp_today.json()[0]["title"] == "Today item"

    # Test Overdue filter
    resp_overdue = await async_client.get("/api/tasks?view=overdue")
    assert len(resp_overdue.json()) == 1
    assert resp_overdue.json()[0]["title"] == "Overdue item"

    # Test Upcoming filter
    resp_upcoming = await async_client.get("/api/tasks?view=upcoming")
    assert len(resp_upcoming.json()) == 1
    assert resp_upcoming.json()[0]["title"] == "Future item"

    # Test Inbox filter
    resp_inbox = await async_client.get("/api/tasks?view=inbox")
    assert len(resp_inbox.json()) == 1
    assert resp_inbox.json()[0]["title"] == "Inbox item"


@pytest.mark.asyncio
async def test_search_filter(async_client: AsyncClient):
    await async_client.post("/api/tasks", json={"title": "Check Arduino UNO Q memory limits"})
    await async_client.post("/api/tasks", json={"title": "Buy groceries at supermarket"})

    resp = await async_client.get("/api/tasks?search=arduino")
    assert len(resp.json()) == 1
    assert "Arduino" in resp.json()[0]["title"]
