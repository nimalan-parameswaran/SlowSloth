"""API endpoints for external integrations (Google Calendar OAuth & status)."""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.models import (
    GoogleIntegrationStatus,
    GoogleAuthUrlResponse,
)
from backend.services.calendar_service import calendar_service

router = APIRouter(prefix="/api/integrations/google", tags=["integrations"])


class GoogleConfigRequest(BaseModel):
    client_id: str = Field(..., min_length=5)
    client_secret: str = Field(..., min_length=5)
    redirect_uri: str = Field(default="http://127.0.0.1:8000/api/integrations/google/callback")


@router.get("/status", response_model=GoogleIntegrationStatus)
async def get_google_status():
    """Check connection status and sync outbox queue size."""
    return await calendar_service.get_account_status()


@router.post("/auth-url", response_model=GoogleAuthUrlResponse)
async def generate_google_auth_url(req: GoogleConfigRequest):
    """Save client credentials securely on host and generate Google OAuth consent URL with CSRF state."""
    try:
        return await calendar_service.generate_auth_url(
            client_id=req.client_id,
            client_secret=req.client_secret,
            redirect_uri=req.redirect_uri,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not generate authorization URL: {str(e)}",
        )


@router.get("/callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """OAuth callback endpoint: validates CSRF state token and stores tokens on host."""
    redirect_uri = "http://127.0.0.1:8000/api/integrations/google/callback"
    try:
        await calendar_service.handle_oauth_callback(
            code=code,
            state=state,
            redirect_uri=redirect_uri,
        )
        # Return helpful response to the browser redirect
        return {
            "status": "success",
            "message": "Google Calendar successfully connected! You can close this window and return to SlowSloth.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth verification failed: {str(e)}",
        )


@router.post("/disconnect")
async def disconnect_google():
    """Disconnect Google Calendar account and purge local access tokens."""
    await calendar_service.disconnect()
    return {"status": "disconnected"}
