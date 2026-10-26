"""API endpoints for Multi-Agent Planning, Execution, and Activity Logging."""

from typing import List
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.models import (
    MultiActionBundle,
    ExecuteBundleRequest,
    ExecutionResult,
    AgentActivityResponse,
)
from backend.services.agent_service import planner_agent, coordinator_agent, ActivityLogger

router = APIRouter(prefix="/api/agents", tags=["agents"])


class PlanThoughtRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=4000)


@router.post("/plan", response_model=MultiActionBundle)
async def plan_thought(req: PlanThoughtRequest):
    """
    Planner Agent: Analyzes incoming thought, identifies intent (meetings, reminders, tasks),
    detects ambiguities, and proposes structured actions for user review.
    Does NOT mutate external services without user approval.
    """
    try:
        return await planner_agent.plan(req.text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Planner agent error: {str(e)}",
        )


@router.post("/execute", response_model=ExecutionResult, status_code=status.HTTP_201_CREATED)
async def execute_approved_bundle(req: ExecuteBundleRequest):
    """
    Coordinator Agent: Executes user-approved and edited bundle across specialist
    Task, Calendar, and Reminder agents in an atomic SQLite transaction.
    """
    try:
        return await coordinator_agent.execute_bundle(req)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action execution error: {str(e)}",
        )


@router.get("/activity", response_model=List[AgentActivityResponse])
async def list_agent_activity(limit: int = Query(default=50, ge=1, le=200)):
    """Fetch transparent, privacy-conscious agent activity logs."""
    return await ActivityLogger.get_recent_activity(limit=limit)
