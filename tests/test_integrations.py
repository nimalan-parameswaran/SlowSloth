"""Tests for Google Calendar integration endpoints, CSRF validation, and disconnect."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_google_integration_initial_status(async_client: AsyncClient):
    resp = await async_client.get("/api/integrations/google/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_connected"] is False
    assert data["pending_sync_count"] == 0


@pytest.mark.asyncio
async def test_google_auth_url_generation(async_client: AsyncClient):
    payload = {
        "client_id": "test-client-id-12345.apps.googleusercontent.com",
        "client_secret": "test-client-secret-abcde",
        "redirect_uri": "http://127.0.0.1:8000/api/integrations/google/callback",
    }
    resp = await async_client.post("/api/integrations/google/auth-url", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "accounts.google.com" in data["auth_url"]
    assert "state=" in data["auth_url"]
    assert len(data["csrf_state"]) >= 20


@pytest.mark.asyncio
async def test_google_oauth_callback_invalid_state(async_client: AsyncClient):
    # Attempt callback with fake CSRF state -> should fail with 400
    resp = await async_client.get("/api/integrations/google/callback?code=mock_code&state=invalid_csrf_state")
    assert resp.status_code == 400
    assert "CSRF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_google_disconnect(async_client: AsyncClient):
    resp = await async_client.post("/api/integrations/google/disconnect")
    assert resp.status_code == 200
    assert resp.json()["status"] == "disconnected"
