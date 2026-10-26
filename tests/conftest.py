"""Pytest configuration and test fixtures for SlowSloth."""

import os
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing app modules
test_db_path = "data/test_slowsloth.db"
os.environ["SLOWSLOTH_DB_PATH"] = test_db_path
os.environ["SLOWSLOTH_TIMEZONE"] = "Asia/Kolkata"
os.environ["AI_BACKEND"] = "dev_mock"
os.environ["ALLOW_DEV_FALLBACK"] = "true"
os.environ["ENABLE_LAN_ACCESS"] = "false"

from backend.config import settings
settings.DB_PATH = test_db_path
settings.TIMEZONE = "Asia/Kolkata"
settings.AI_BACKEND = "dev_mock"
settings.ALLOW_DEV_FALLBACK = True
settings.ENABLE_LAN_ACCESS = False

from backend.database import db
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Ensure clean test database for each test session/module."""
    Path("data").mkdir(exist_ok=True)
    db.db_path = test_db_path
    
    # Run migrations
    await db.run_migrations()

    # Clear tables before each test
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM reminders;")
        await conn.execute("DELETE FROM calendar_sync_queue;")
        await conn.execute("DELETE FROM calendar_events;")
        await conn.execute("DELETE FROM tasks;")
        await conn.execute("DELETE FROM agent_activity;")
        await conn.execute("DELETE FROM thoughts;")
        await conn.execute("DELETE FROM calendar_accounts;")
        await conn.commit()

    yield

    # Clean up after test
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM reminders;")
        await conn.execute("DELETE FROM calendar_sync_queue;")
        await conn.execute("DELETE FROM calendar_events;")
        await conn.execute("DELETE FROM tasks;")
        await conn.execute("DELETE FROM agent_activity;")
        await conn.execute("DELETE FROM thoughts;")
        await conn.execute("DELETE FROM calendar_accounts;")
        await conn.commit()


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for FastAPI endpoint testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
