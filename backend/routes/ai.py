"""Endpoints for organizing thoughts and confirming extracted tasks."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.models import (
    OrganizeThoughtRequest,
    OrganizeThoughtResponse,
    ConfirmTasksRequest,
    TaskResponse,
)
from backend.services.ai_service import ai_service
from backend.services.task_service import task_service
from backend.services.date_parser import date_parser

router = APIRouter(prefix="/api/thoughts", tags=["ai"])


@router.post("/organize", response_model=OrganizeThoughtResponse)
async def organize_thought(req: OrganizeThoughtRequest):
    """
    Ingest a free-form thought, extract structured tasks via AI or deterministic rule-based engine,
    and return suggestions for user review.
    """
    # 1. Persist the thought record in SQLite
    thought_id = await task_service.create_thought(req.text)

    # 2. Extract tasks using active AI backend or fallback
    tasks, backend_name, model_id, is_mock, latency_ms = await ai_service.extract_tasks(req.text)

    now_iso = date_parser.get_current_time().isoformat()

    return OrganizeThoughtResponse(
        thought_id=thought_id,
        raw_thought=req.text,
        tasks=tasks,
        backend=backend_name,
        model_name=model_id,
        is_mock=is_mock,
        processing_time_ms=latency_ms,
        created_at=now_iso,
    )


@router.post("/confirm", response_model=List[TaskResponse], status_code=status.HTTP_201_CREATED)
async def confirm_tasks(req: ConfirmTasksRequest):
    """
    Save reviewed and user-confirmed tasks to SQLite database.
    Guards against duplicate confirmations.
    """
    try:
        saved_tasks = await task_service.confirm_thought_tasks(
            thought_id=req.thought_id,
            tasks=req.tasks,
        )
        return saved_tasks
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
