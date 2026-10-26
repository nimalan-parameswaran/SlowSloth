"""Main application entry point for SlowSloth FastAPI server."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import db
from backend.routes.tasks import router as tasks_router
from backend.routes.ai import router as ai_router
from backend.routes.briefing import router as briefing_router
from backend.routes.system import router as system_router
from backend.routes.agents import router as agents_router
from backend.routes.calendar import router as calendar_router
from backend.routes.reminders import router as reminders_router
from backend.routes.integrations import router as integrations_router
from backend.services.reminder_service import reminder_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler: run migrations and recover reminders on startup."""
    # Ensure database tables exist and migrations are applied
    await db.run_migrations()
    # Recover and process any reminders that came due while the server was offline
    await reminder_service.recover_and_process_pending()
    yield


app = FastAPI(
    title="SlowSloth Multi-Agent Personal Assistant",
    description="Local-first AI personal assistant for tasks, calendars, and reminders.",
    version="0.2.0",
    lifespan=lifespan,
)

# Restrict CORS to localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_lan_guard(request: Request, call_next):
    """
    Security middleware enforcing access rules.
    If LAN access is enabled with an API key, non-localhost callers must supply X-SlowSloth-Key.
    """
    client_host = request.client.host if request.client else "127.0.0.1"
    is_local = client_host in ("127.0.0.1", "::1", "localhost")

    if not is_local:
        if not settings.ENABLE_LAN_ACCESS:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "LAN access is disabled on this SlowSloth instance."},
            )
        if settings.LAN_API_KEY:
            key_header = request.headers.get("X-SlowSloth-Key")
            if key_header != settings.LAN_API_KEY:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or missing X-SlowSloth-Key header."},
                )

    response = await call_next(request)
    return response


# Include API Routers
app.include_router(tasks_router)
app.include_router(ai_router)
app.include_router(briefing_router)
app.include_router(system_router)

# Mount frontend static directory if exists
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse({"message": "SlowSloth backend running. Frontend index.html not found."})
else:
    @app.get("/")
    async def root():
        return {
            "message": "SlowSloth backend running.",
            "docs": "/docs",
            "backend": settings.AI_BACKEND,
        }
