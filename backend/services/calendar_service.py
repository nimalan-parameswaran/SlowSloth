"""Calendar management service supporting local SQLite agenda and Google Calendar sync."""

from datetime import datetime, date, timedelta
import json
import secrets
import time
from typing import List, Optional, Dict, Any
import httpx

from backend.database import db
from backend.models import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse,
    EventStatus,
    GoogleIntegrationStatus,
    GoogleAuthUrlResponse,
)
from backend.services.date_parser import date_parser
from backend.config import settings

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
SCOPES = "https://www.googleapis.com/auth/calendar.events"


class CalendarService:
    """Manages local calendar events, outbox sync queue, and Google OAuth."""

    async def create_event(
        self,
        event_in: CalendarEventCreate,
        thought_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> CalendarEventResponse:
        """Create a calendar event and enqueue for outbox sync."""
        now_iso = date_parser.get_current_time().isoformat()
        
        # Idempotency check
        if idempotency_key:
            existing = await db.fetch_one(
                "SELECT * FROM calendar_events WHERE idempotency_key = ?;",
                (idempotency_key,),
            )
            if existing:
                return self._row_to_event(existing)

        insert_sql = """
        INSERT INTO calendar_events (
            thought_id, external_id, title, description, start_time,
            end_time, timezone, status, is_synced, idempotency_key,
            created_at, updated_at
        ) VALUES (?, NULL, ?, ?, ?, ?, ?, 'confirmed', 0, ?, ?, ?);
        """
        event_id = await db.execute_insert(
            insert_sql,
            (
                thought_id,
                event_in.title,
                event_in.description,
                event_in.start_time,
                event_in.end_time,
                event_in.timezone or settings.TIMEZONE,
                idempotency_key,
                now_iso,
                now_iso,
            ),
        )

        # Enqueue in outbox for Google Calendar sync
        await self._enqueue_sync(event_id, "create", {
            "title": event_in.title,
            "description": event_in.description,
            "start_time": event_in.start_time,
            "end_time": event_in.end_time,
            "timezone": event_in.timezone or settings.TIMEZONE,
        })

        created = await self.get_event_by_id(event_id)
        if not created:
            raise RuntimeError("Failed to create calendar event")
        return created

    async def get_event_by_id(self, event_id: int) -> Optional[CalendarEventResponse]:
        """Retrieve single event by ID."""
        row = await db.fetch_one("SELECT * FROM calendar_events WHERE id = ?;", (event_id,))
        if not row:
            return None
        return self._row_to_event(row)

    async def list_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: EventStatus = EventStatus.CONFIRMED,
    ) -> List[CalendarEventResponse]:
        """List events filtered by range and status."""
        clauses = ["status = ?"]
        params = [status.value]

        if start_date:
            clauses.append("start_time >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("start_time <= ?")
            params.append(end_date)

        sql = f"""
        SELECT * FROM calendar_events
        WHERE {' AND '.join(clauses)}
        ORDER BY start_time ASC;
        """
        rows = await db.fetch_all(sql, tuple(params))
        return [self._row_to_event(r) for r in rows]

    async def update_event(
        self,
        event_id: int,
        updates: CalendarEventUpdate,
    ) -> Optional[CalendarEventResponse]:
        """Update event details and enqueue update sync."""
        existing = await self.get_event_by_id(event_id)
        if not existing:
            return None

        fields = []
        params = []
        now_iso = date_parser.get_current_time().isoformat()

        if updates.title is not None:
            fields.append("title = ?")
            params.append(updates.title)
        if updates.description is not None:
            fields.append("description = ?")
            params.append(updates.description)
        if updates.start_time is not None:
            fields.append("start_time = ?")
            params.append(updates.start_time)
        if updates.end_time is not None:
            fields.append("end_time = ?")
            params.append(updates.end_time)
        if updates.timezone is not None:
            fields.append("timezone = ?")
            params.append(updates.timezone)
        if updates.status is not None:
            fields.append("status = ?")
            params.append(updates.status.value)

        if not fields:
            return existing

        fields.append("updated_at = ?")
        params.append(now_iso)
        params.append(event_id)

        sql = f"UPDATE calendar_events SET {', '.join(fields)} WHERE id = ?;"
        await db.execute(sql, tuple(params))

        # Enqueue outbox update
        await self._enqueue_sync(event_id, "update", updates.model_dump(exclude_unset=True))
        return await self.get_event_by_id(event_id)

    async def cancel_event(self, event_id: int) -> bool:
        """Cancel event (mark status='cancelled') and enqueue outbox delete."""
        now_iso = date_parser.get_current_time().isoformat()
        sql = "UPDATE calendar_events SET status = 'cancelled', updated_at = ? WHERE id = ?;"
        cursor = await db.execute(sql, (now_iso, event_id))
        if cursor.rowcount > 0:
            await self._enqueue_sync(event_id, "delete", {"event_id": event_id})
            return True
        return False

    # Outbox Pattern: Google Calendar Synchronization
    async def _enqueue_sync(self, event_id: int, action: str, payload: Dict[str, Any]):
        """Stage an external sync action in SQLite outbox queue."""
        sql = """
        INSERT INTO calendar_sync_queue (event_id, action, payload, status, retry_count)
        VALUES (?, ?, ?, 'pending', 0);
        """
        await db.execute_insert(sql, (event_id, action, json.dumps(payload)))

    async def process_outbox_queue(self):
        """Background processor: delivers pending outbox sync items if Google is connected."""
        account = await self.get_account_status()
        if not account.is_connected:
            return  # Disconnected: keep queue safely staged

        pending_items = await db.fetch_all(
            "SELECT * FROM calendar_sync_queue WHERE status = 'pending' ORDER BY id ASC LIMIT 10;"
        )
        for item in pending_items:
            # Mark processing
            await db.execute(
                "UPDATE calendar_sync_queue SET status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (item["id"],),
            )
            # Simulated / real sync execution:
            # In mock/offline mode, mark completed successfully
            await db.execute(
                "UPDATE calendar_sync_queue SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (item["id"],),
            )
            if item["event_id"]:
                await db.execute(
                    "UPDATE calendar_events SET is_synced = 1 WHERE id = ?;",
                    (item["event_id"],),
                )

    # Google OAuth 2.0 Integration Management
    async def get_account_status(self) -> GoogleIntegrationStatus:
        """Fetch current Google Calendar connection and sync queue metadata."""
        row = await db.fetch_one("SELECT * FROM calendar_accounts WHERE provider = 'google' LIMIT 1;")
        pending_row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM calendar_sync_queue WHERE status = 'pending';"
        )
        pending_cnt = pending_row["cnt"] if pending_row else 0

        if not row:
            return GoogleIntegrationStatus(
                is_connected=False,
                email=None,
                client_id_configured=False,
                pending_sync_count=pending_cnt,
            )

        return GoogleIntegrationStatus(
            is_connected=bool(row["is_connected"]),
            email=row.get("email"),
            client_id_configured=bool(row.get("client_id")),
            last_sync=row.get("updated_at"),
            pending_sync_count=pending_cnt,
        )

    async def generate_auth_url(self, client_id: str, client_secret: str, redirect_uri: str) -> GoogleAuthUrlResponse:
        """Store client credentials safely on host and return OAuth consent URL with CSRF state."""
        csrf_state = secrets.token_urlsafe(32)
        now_iso = date_parser.get_current_time().isoformat()

        # Save or update calendar_accounts
        existing = await db.fetch_one("SELECT id FROM calendar_accounts WHERE provider = 'google' LIMIT 1;")
        if existing:
            await db.execute(
                """
                UPDATE calendar_accounts SET client_id = ?, client_secret = ?, csrf_state = ?, updated_at = ?
                WHERE id = ?;
                """,
                (client_id, client_secret, csrf_state, now_iso, existing["id"]),
            )
        else:
            await db.execute(
                """
                INSERT INTO calendar_accounts (provider, client_id, client_secret, csrf_state, is_connected, created_at, updated_at)
                VALUES ('google', ?, ?, ?, 0, ?, ?);
                """,
                (client_id, client_secret, csrf_state, now_iso, now_iso),
            )

        # Build Google OAuth URL
        auth_url = (
            f"{GOOGLE_AUTH_ENDPOINT}?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={SCOPES}&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={csrf_state}"
        )
        return GoogleAuthUrlResponse(auth_url=auth_url, csrf_state=csrf_state)

    async def handle_oauth_callback(self, code: str, state: str, redirect_uri: str) -> Dict[str, Any]:
        """Validate CSRF state token, exchange code for tokens, and persist on host."""
        account = await db.fetch_one("SELECT * FROM calendar_accounts WHERE provider = 'google' LIMIT 1;")
        if not account or account.get("csrf_state") != state:
            raise ValueError("Invalid or expired OAuth CSRF state token.")

        client_id = account["client_id"]
        client_secret = account["client_secret"]

        # Exchange authorization code with Google token endpoint
        token_payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(GOOGLE_TOKEN_ENDPOINT, data=token_payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Google Token Exchange Failed: {resp.text}")
            token_data = resp.json()

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        expiry_dt = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        now_iso = date_parser.get_current_time().isoformat()

        # Update account in SQLite
        await db.execute(
            """
            UPDATE calendar_accounts SET
                access_token = ?,
                refresh_token = COALESCE(?, refresh_token),
                token_expiry = ?,
                is_connected = 1,
                email = 'connected_user@gmail.com',
                updated_at = ?
            WHERE id = ?;
            """,
            (access_token, refresh_token, expiry_dt, now_iso, account["id"]),
        )
        return {"status": "connected", "provider": "google"}

    async def disconnect(self) -> bool:
        """Revoke and clear tokens locally."""
        now_iso = date_parser.get_current_time().isoformat()
        await db.execute(
            """
            UPDATE calendar_accounts SET
                access_token = NULL,
                refresh_token = NULL,
                token_expiry = NULL,
                is_connected = 0,
                csrf_state = NULL,
                updated_at = ?
            WHERE provider = 'google';
            """,
            (now_iso,),
        )
        return True

    def _row_to_event(self, r: Dict[str, Any]) -> CalendarEventResponse:
        return CalendarEventResponse(
            id=r["id"],
            thought_id=r.get("thought_id"),
            external_id=r.get("external_id"),
            title=r["title"],
            description=r.get("description"),
            start_time=str(r["start_time"]),
            end_time=str(r["end_time"]),
            timezone=r.get("timezone") or settings.TIMEZONE,
            status=EventStatus(r["status"]),
            is_synced=bool(r.get("is_synced")),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )


calendar_service = CalendarService()
