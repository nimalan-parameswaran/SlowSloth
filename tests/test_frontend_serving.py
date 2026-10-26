"""Tests for static file serving and frontend dashboard entrypoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_frontend_index_serving(async_client: AsyncClient):
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert "SlowSloth" in resp.text
    assert "Capture Raw Thought" in resp.text
    assert "Organize Thought" in resp.text


@pytest.mark.asyncio
async def test_static_assets_serving(async_client: AsyncClient):
    css_resp = await async_client.get("/static/css/styles.css")
    assert css_resp.status_code == 200
    assert "--bg-color: #0B132B;" in css_resp.text

    svg_resp = await async_client.get("/static/assets/sloth.svg")
    assert svg_resp.status_code == 200
    assert "<svg" in svg_resp.text

    js_resp = await async_client.get("/static/js/app.js")
    assert js_resp.status_code == 200
    assert "handleOrganizeThought" in js_resp.text
