"""Data models and Pydantic schemas for SlowSloth."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DeadlineConfidence(str, Enum):
    EXACT = "exact"
    SUGGESTED = "suggested"
    UNKNOWN = "unknown"


class TaskView(str, Enum):
    ALL = "all"
    TODAY = "today"
    UPCOMING = "upcoming"
    OVERDUE = "overdue"
    INBOX = "inbox"


class ExtractedTask(BaseModel):
    """Structured task extracted from an unstructured thought."""

    title: str = Field(..., min_length=1, max_length=200, description="Clear, concise task title")
    description: Optional[str] = Field(default=None, max_length=1000, description="Task details or context")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task urgency and importance")
    deadline: Optional[str] = Field(
        default=None,
        description="ISO-8601 formatted datetime string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS), or None if no deadline",
    )
    deadline_expression: Optional[str] = Field(
        default=None,
        description="Original text expression used, e.g. 'tomorrow', 'Friday 5pm'",
    )
    deadline_confidence: DeadlineConfidence = Field(
        default=DeadlineConfidence.UNKNOWN,
        description="Confidence level of the deadline extraction",
    )
    deadline_confirmed: bool = Field(
        default=False,
        description="Whether the user explicitly reviewed and accepted the deadline",
    )
    suggested_next_step: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Immediate concrete next action step",
    )
    category: str = Field(
        default="general",
        max_length=50,
        description="Category classification (e.g., project, communication, errands)",
    )


class OrganizeThoughtRequest(BaseModel):
    """User input for thought capture."""

    text: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Free-form thought or notes to organize",
    )

    @field_validator("text")
    @classmethod
    def strip_and_validate_text(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Thought text must be at least 3 characters long")
        return cleaned


class OrganizeThoughtResponse(BaseModel):
    """Response returned after processing a thought with AI or rule-based parser."""

    thought_id: int
    raw_thought: str
    tasks: List[ExtractedTask]
    backend: str = Field(..., description="Active backend: dev_mock, llama_cpp, ollama")
    model_name: str
    is_mock: bool = Field(..., description="Whether extraction came from deterministic mock/rules")
    processing_time_ms: float
    created_at: str


class ConfirmTasksRequest(BaseModel):
    """User confirmed task payload."""

    thought_id: int
    tasks: List[ExtractedTask]


class TaskCreate(BaseModel):
    """Manual task creation."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    priority: Priority = Field(default=Priority.MEDIUM)
    deadline: Optional[str] = None
    deadline_expression: Optional[str] = None
    deadline_confirmed: bool = False
    suggested_next_step: Optional[str] = None
    category: str = "general"


class TaskUpdate(BaseModel):
    """Task update schema."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    deadline: Optional[str] = None
    deadline_expression: Optional[str] = None
    deadline_confirmed: Optional[bool] = None
    suggested_next_step: Optional[str] = None
    category: Optional[str] = None
    is_completed: Optional[bool] = None


class TaskResponse(BaseModel):
    """Full task schema returned to the client."""

    id: int
    thought_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    priority: Priority
    deadline: Optional[str] = None
    deadline_expression: Optional[str] = None
    deadline_confidence: DeadlineConfidence
    deadline_confirmed: bool
    suggested_next_step: Optional[str] = None
    category: str
    is_completed: bool
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


class BriefingSection(BaseModel):
    title: str
    count: int
    tasks: List[TaskResponse]


class BriefingResponse(BaseModel):
    summary: str
    generated_at: str
    timezone: str
    total_open_tasks: int
    sections: Dict[str, BriefingSection]


class SystemStatusResponse(BaseModel):
    """System health and hardware status."""

    platform_os: str
    architecture: str
    python_version: str
    active_backend: str
    model_identifier: str
    is_mock: bool
    real_inference_verified: bool
    total_ram_mb: Optional[float] = None
    free_ram_mb: Optional[float] = None
    disk_free_gb: Optional[float] = None
    database_path: str
    timezone: str
    lan_enabled: bool
