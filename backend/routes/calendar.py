"""API endpoints for Calendar agenda management."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, status

from backend.models import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse,
    EventStatus,
)
from backend.services.calendar_service import calendar_service

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/events", response_model=List[CalendarEventResponse])
async def list_calendar_events(
    start_date: Optional[str] = Query(default=None, description="Start date filter (ISO)"),
    end_date: Optional[str] = Query(default=None, description="End date filter (ISO)"),
    status: EventStatus = Query(default=EventStatus.CONFIRMED),
):
    """List calendar events in agenda view."""
    return await calendar_service.list_events(start_date=start_date, end_date=end_date, status=status)


@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(event_in: CalendarEventCreate):
    """Manually create a calendar event."""
    return await calendar_service.create_event(event_in)


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
async def get_calendar_event(event_id: int = Path(..., ge=1)):
    """Retrieve single event by ID."""
    evt = await calendar_service.get_event_by_id(event_id)
    if not evt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar event {event_id} not found",
        )
    return evt


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(updates: CalendarEventUpdate, event_id: int = Path(..., ge=1)):
    """Edit calendar event details."""
    evt = await calendar_service.update_event(event_id, updates)
    if not evt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar event {event_id} not found",
        )
    return evt


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_event(event_id: int = Path(..., ge=1)):
    """Cancel calendar event."""
    deleted = await calendar_service.cancel_event(event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar event {event_id} not found",
        )
    return None
