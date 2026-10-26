"""API endpoints for Scheduled Reminders."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, status

from backend.models import (
    ReminderCreate,
    ReminderResponse,
    ReminderStatus,
    DeliveryMethod,
)
from backend.services.reminder_service import reminder_service

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=List[ReminderResponse])
async def list_reminders(
    status: Optional[ReminderStatus] = Query(default=None),
    delivery_method: Optional[DeliveryMethod] = Query(default=None),
):
    """List scheduled, delivered, or missed reminders."""
    return await reminder_service.list_reminders(status=status, delivery_method=delivery_method)


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(reminder_in: ReminderCreate):
    """Manually create a scheduled reminder."""
    return await reminder_service.schedule_reminder(reminder_in)


@router.patch("/{reminder_id}/acknowledge", response_model=ReminderResponse)
async def acknowledge_reminder(reminder_id: int = Path(..., ge=1)):
    """Acknowledge/dismiss a delivered reminder in the dashboard."""
    rem = await reminder_service.acknowledge_reminder(reminder_id)
    if not rem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder {reminder_id} not found",
        )
    return rem


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(reminder_id: int = Path(..., ge=1)):
    """Cancel a reminder."""
    deleted = await reminder_service.cancel_reminder(reminder_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder {reminder_id} not found",
        )
    return None


@router.post("/process-due", response_model=dict)
async def trigger_due_reminders():
    """Trigger reminder delivery check (used by background task or dashboard polling)."""
    return await reminder_service.recover_and_process_pending()
