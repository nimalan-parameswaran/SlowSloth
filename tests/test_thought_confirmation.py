"""Tests for thought organization and task confirmation safeguards."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_organize_and_confirm_workflow(async_client: AsyncClient):
    organize_payload = {
        "text": "Need to finish README, check battery model results, and email mentor tomorrow."
    }
    org_resp = await async_client.post("/api/thoughts/organize", json=organize_payload)
    assert org_resp.status_code == 200
    data = org_resp.json()

    assert data["thought_id"] is not None
    assert data["is_mock"] is True
    assert data["backend"] == "dev_mock"
    assert len(data["tasks"]) >= 3

    thought_id = data["thought_id"]
    suggested_tasks = data["tasks"]

    # Modify one task (user review step)
    suggested_tasks[0]["title"] = "Finish complete SlowSloth README"
    suggested_tasks[0]["deadline_confirmed"] = True

    confirm_payload = {
        "thought_id": thought_id,
        "tasks": suggested_tasks,
    }
    conf_resp = await async_client.post("/api/thoughts/confirm", json=confirm_payload)
    assert conf_resp.status_code == 201
    confirmed = conf_resp.json()
    assert len(confirmed) == len(suggested_tasks)
    assert confirmed[0]["title"] == "Finish complete SlowSloth README"
    assert confirmed[0]["deadline_confirmed"] is True

    # Duplicate confirmation safeguard:
    # Submitting the same thought confirmation again must NOT create duplicate tasks!
    conf_resp_2 = await async_client.post("/api/thoughts/confirm", json=confirm_payload)
    assert conf_resp_2.status_code == 201
    confirmed_2 = conf_resp_2.json()
    assert len(confirmed_2) == len(suggested_tasks)

    # Verify total task count in database is still equal to len(suggested_tasks)
    all_tasks_resp = await async_client.get("/api/tasks")
    assert len(all_tasks_resp.json()) == len(suggested_tasks)


@pytest.mark.asyncio
async def test_confirm_nonexistent_thought(async_client: AsyncClient):
    payload = {
        "thought_id": 99999,
        "tasks": [{"title": "Phantom task", "priority": "medium", "category": "general"}],
    }
    resp = await async_client.post("/api/thoughts/confirm", json=payload)
    assert resp.status_code == 404
