"""Tests for AI task extraction, schema validation, and fallback mechanisms."""

import pytest
from backend.services.ai_service import DevMockProvider, AIService
from backend.models import Priority, DeadlineConfidence
from backend.config import settings


@pytest.mark.asyncio
async def test_deterministic_mock_extraction():
    provider = DevMockProvider()
    thought = (
        "I need to finish the README for my AI project, check the battery model results, "
        "and email my mentor tomorrow. I should probably do the results first."
    )
    tasks, engine_name, is_mock = await provider.extract_tasks(thought)

    assert is_mock is True
    assert "Rule-Based" in engine_name
    assert len(tasks) >= 3

    # Check that battery results has high priority
    battery_task = next((t for t in tasks if "battery" in t.title.lower() or "result" in t.title.lower()), None)
    assert battery_task is not None
    assert battery_task.priority == Priority.HIGH
    assert battery_task.suggested_next_step is not None

    # Check that email mentor task has a deadline for tomorrow
    email_task = next((t for t in tasks if "mentor" in t.title.lower() or "email" in t.title.lower()), None)
    assert email_task is not None
    assert email_task.deadline is not None
    assert "tomorrow" in email_task.deadline_expression.lower()
    assert email_task.category == "communication"

    # Check README task has medium priority and project category
    readme_task = next((t for t in tasks if "readme" in t.title.lower()), None)
    assert readme_task is not None
    assert readme_task.priority == Priority.MEDIUM
    assert readme_task.category == "project"


@pytest.mark.asyncio
async def test_extraction_is_deterministic():
    provider = DevMockProvider()
    thought = "Buy groceries, check the project deadline, and finish the report tomorrow."
    
    tasks1, _, _ = await provider.extract_tasks(thought)
    tasks2, _, _ = await provider.extract_tasks(thought)

    assert len(tasks1) == len(tasks2)
    for t1, t2 in zip(tasks1, tasks2):
        assert t1.title == t2.title
        assert t1.priority == t2.priority
        assert t1.deadline == t2.deadline
        assert t1.suggested_next_step == t2.suggested_next_step


@pytest.mark.asyncio
async def test_fallback_when_runtime_missing():
    service = AIService()
    settings.AI_BACKEND = "llama_cpp"
    settings.INFERENCE_ENDPOINT = "http://127.0.0.1:9999"  # Deliberately unreachable port
    settings.ALLOW_DEV_FALLBACK = True

    tasks, backend, model_id, is_mock, latency = await service.extract_tasks(
        "Remember to investigate that error when I have time."
    )

    assert is_mock is True
    assert backend == "dev_mock"
    assert "Fallback" in model_id
    assert len(tasks) >= 1
    # Check that 'when I have time' inferred low priority
    assert tasks[0].priority == Priority.LOW

    # Restore settings
    settings.AI_BACKEND = "dev_mock"


@pytest.mark.asyncio
async def test_error_raised_if_fallback_disabled():
    service = AIService()
    settings.AI_BACKEND = "llama_cpp"
    settings.INFERENCE_ENDPOINT = "http://127.0.0.1:9999"
    settings.ALLOW_DEV_FALLBACK = False

    with pytest.raises(RuntimeError) as exc_info:
        await service.extract_tasks("Investigate bug")

    assert "dev fallback is disabled" in str(exc_info.value)

    # Restore settings
    settings.AI_BACKEND = "dev_mock"
    settings.ALLOW_DEV_FALLBACK = True
