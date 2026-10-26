"""System status, health audit, and configuration endpoints."""

import os
import platform
import shutil
import sys
from typing import Dict, Any, Optional
from fastapi import APIRouter
from backend.models import SystemStatusResponse
from backend.config import settings
from backend.database import db

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Audit hardware resources, platform architecture, and active AI engine.
    Real inference verified will only be True when real local AI is active and tested.
    """
    total_ram_mb: Optional[float] = None
    free_ram_mb: Optional[float] = None

    try:
        import psutil
        vm = psutil.virtual_memory()
        total_ram_mb = round(vm.total / (1024 * 1024), 1)
        free_ram_mb = round(vm.available / (1024 * 1024), 1)
    except Exception:
        pass

    disk_free_gb: Optional[float] = None
    try:
        total, used, free = shutil.disk_usage(os.path.abspath("."))
        disk_free_gb = round(free / (1024 * 1024 * 1024), 2)
    except Exception:
        pass

    is_mock = (settings.AI_BACKEND.lower() == "dev_mock")
    # Real inference verified is False for dev_mock, or evaluated during live health-checks
    real_verified = False if is_mock else False

    return SystemStatusResponse(
        platform_os=f"{platform.system()} {platform.release()}",
        architecture=platform.machine(),
        python_version=platform.python_version(),
        active_backend=settings.AI_BACKEND,
        model_identifier=settings.AI_MODEL_IDENTIFIER,
        is_mock=is_mock,
        real_inference_verified=real_verified,
        total_ram_mb=total_ram_mb,
        free_ram_mb=free_ram_mb,
        disk_free_gb=disk_free_gb,
        database_path=str(settings.get_absolute_db_path()),
        timezone=settings.TIMEZONE,
        lan_enabled=settings.ENABLE_LAN_ACCESS,
    )


@router.get("/health")
async def health_check():
    """Simple ping endpoint for process supervisors and health probes."""
    return {"status": "ok", "service": "SlowSloth"}
