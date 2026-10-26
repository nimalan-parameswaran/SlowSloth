"""Tests for Multi-Agent Planner, Intent Parser, and Coordinator Execution."""

from datetime import datetime, date, timedelta
import pytest
from httpx import AsyncClient
from backend.services.date_parser import date_parser


@pytest.mark.asyncio
async def test_multi_action_thought_planning(async_client: AsyncClient):
    """
    Test the canonical multi-intent thought:
    'I have a project meeting tomorrow at 10 AM for 30 minutes. Remind me 15 minutes before, and prepare the presentation today.'
    """
    thought_text = (
        "I have a project meeting tomorrow at 10 AM for 30 minutes. "
        "Remind me 15 minutes before, and prepare the presentation today."
    )
    resp = await async_client.post("/api/agents/plan", json={"text": thought_text})
    assert resp.status_code == 200
    bundle = resp.json()

    assert bundle["thought_id"] is not None
    assert len(bundle["events"]) == 1
    assert len(bundle["reminders"]) == 1
    assert len(bundle["tasks"]) >= 1

    # Verify Meeting Event
    event = bundle["events"][0]
    assert "Meeting" in event["title"]
    assert event["duration_minutes"] == 30
    event_start = datetime.fromisoformat(event["start_time"])
    now = date_parser.get_current_time()
    assert event_start.date() == (now.date() + timedelta(days=1))
    assert event_start.hour == 10
    assert event_start.minute == 0

    # Verify Reminder
    reminder = bundle["reminders"][0]
    assert reminder["offset_minutes"] == 15
    rem_time = datetime.fromisoformat(reminder["scheduled_time"])
    assert rem_time == event_start - timedelta(minutes=15)
    assert rem_time.hour == 9
    assert rem_time.minute == 45

    # Verify Preparation Task
    prep_task = next((t for t in bundle["tasks"] if "presentation" in t["title"].lower() or "prepare" in t["title"].lower()), None)
    assert prep_task is not None
    assert prep_task["deadline"] is not None
    prep_deadline = datetime.fromisoformat(prep_task["deadline"])
    assert prep_deadline.date() == now.date()


@pytest.mark.asyncio
async def test_ambiguity_detection(async_client: AsyncClient):
    # Meeting with no explicit time
    thought_text = "I have a sync with mentor tomorrow"
    resp = await async_client.post("/api/agents/plan", json={"text": thought_text})
    assert resp.status_code == 200
    bundle = resp.json()
    assert len(bundle["events"]) == 1
    assert bundle["events"][0]["is_ambiguous"] is True
    assert len(bundle["ambiguities"]) >= 1


@pytest.mark.asyncio
async def test_coordinator_execution_and_idempotency(async_client: AsyncClient):
    thought_text = "Project sync tomorrow at 11 AM for 45 minutes, remind me 10 minutes before, and draft notes today."
    plan_resp = await async_client.post("/api/agents/plan", json={"text": thought_text})
    assert plan_resp.status_code == 200
    bundle = plan_resp.json()

    # User reviews and approves
    exec_resp = await async_client.post("/api/agents/execute", json=bundle)
    assert exec_resp.status_code == 201
    result = exec_resp.json()

    assert len(result["created_events"]) == 1
    assert len(result["created_reminders"]) == 1
    assert len(result["created_tasks"]) >= 1

    # Verify agent activity was logged
    act_resp = await async_client.get("/api/agents/activity")
    assert act_resp.status_code == 200
    activities = act_resp.json()
    agent_names = {a["agent_name"] for a in activities}
    assert "planner" in agent_names
    assert "calendar" in agent_names
    assert "reminder" in agent_names
    assert "task" in agent_names

    # Idempotency Test: re-executing same bundle does not duplicate events or reminders
    exec_resp_2 = await async_client.post("/api/agents/execute", json=bundle)
    assert exec_resp_2.status_code == 201
    
    events_list = await async_client.get("/api/calendar/events")
    assert len(events_list.json()) == 1

    reminders_list = await async_client.get("/api/reminders")
    assert len(reminders_list.json()) == 1
