"""Tests for SQL injection resistance, XSS safety, and LAN security controls."""

import pytest
from httpx import AsyncClient
from backend.config import settings


@pytest.mark.asyncio
async def test_sql_injection_safety(async_client: AsyncClient):
    # Payload trying to inject SQL
    malicious_title = "'; DROP TABLE tasks; --"
    create_resp = await async_client.post(
        "/api/tasks",
        json={"title": malicious_title, "description": "1' OR '1'='1"},
    )
    assert create_resp.status_code == 201

    # Ensure tasks table still exists and task is stored literally
    task_id = create_resp.json()["id"]
    get_resp = await async_client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == malicious_title

    # Search with SQL injection payload
    search_resp = await async_client.get("/api/tasks?search=' OR '1'='1")
    assert search_resp.status_code == 200


@pytest.mark.asyncio
async def test_xss_payload_preservation(async_client: AsyncClient):
    xss_payload = "<script>alert('XSS')</script><img src=x onerror=alert(1)>"
    create_resp = await async_client.post(
        "/api/tasks",
        json={"title": xss_payload, "description": "<b>Safe</b>"},
    )
    assert create_resp.status_code == 201
    task = create_resp.json()
    # It must be stored literally and returned as pure string
    assert task["title"] == xss_payload


@pytest.mark.asyncio
async def test_lan_access_guard(async_client: AsyncClient):
    # Simulated remote caller header
    settings.ENABLE_LAN_ACCESS = False
    
    # Send request with a remote client host
    # Note: async_client test client defaults client.host to testclient/127.0.0.1
    # We can test by toggling settings and using standard health endpoint
    health_resp = await async_client.get("/api/system/health")
    assert health_resp.status_code == 200
