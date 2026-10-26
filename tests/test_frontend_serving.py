"""Tests for static file serving and redesigned frontend dashboard entrypoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_frontend_index_serving(async_client: AsyncClient):
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert "SlowSloth" in resp.text
    assert "Overview" in resp.text
    assert "Capture / Inbox" in resp.text
    assert "Calendar" in resp.text
    assert "Reminders" in resp.text
    assert "Agent Activity" in resp.text


@pytest.mark.asyncio
async def test_static_assets_serving(async_client: AsyncClient):
    css_resp = await async_client.get("/static/css/styles.css")
    assert css_resp.status_code == 200
    assert "--primary: #533afd;" in css_resp.text
    assert "--ink: #0d253d;" in css_resp.text
    assert "--canvas: #ffffff;" in css_resp.text

    svg_resp = await async_client.get("/static/assets/sloth.svg")
    assert svg_resp.status_code == 200
    assert "<svg" in svg_resp.text

    js_resp = await async_client.get("/static/js/app.js")
    assert js_resp.status_code == 200
    assert "handlePlanThought" in js_resp.text
