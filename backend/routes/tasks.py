"""Task endpoints for listing, updating, completing, and deleting tasks."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, status
from backend.models import (
    TaskResponse,
    TaskCreate,
    TaskUpdate,
    TaskView,
    Priority,
)
from backend.services.task_service import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    view: TaskView = Query(default=TaskView.ALL, description="Task view filter"),
    priority: Optional[Priority] = Query(default=None, description="Priority filter"),
    category: Optional[str] = Query(default=None, description="Category filter"),
    search: Optional[str] = Query(default=None, description="Search term in title/description"),
):
    """List tasks matching the specified view and filters."""
    return await task_service.get_tasks(
        view=view,
        priority=priority,
        category=category,
        search=search,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: TaskCreate):
    """Manually create a new task."""
    return await task_service.create_manual_task(task_in)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int = Path(..., ge=1)):
    """Fetch task by ID."""
    task = await task_service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_in: TaskUpdate, task_id: int = Path(..., ge=1)):
    """Update task details."""
    updated = await task_service.update_task(task_id, task_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return updated


@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def toggle_task_completion(task_id: int = Path(..., ge=1)):
    """Toggle task completion state (reopen if completed, mark done if open)."""
    toggled = await task_service.toggle_complete(task_id)
    if not toggled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return toggled


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int = Path(..., ge=1)):
    """Delete a task."""
    deleted = await task_service.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return None
