"""Endpoint for on-demand daily briefings."""

from fastapi import APIRouter
from backend.models import BriefingResponse
from backend.services.briefing_service import briefing_service

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.get("", response_model=BriefingResponse)
async def get_briefing():
    """Generate an on-demand daily briefing grounded in current database state."""
    return await briefing_service.generate_briefing()
