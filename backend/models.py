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


class ReminderStatus(str, Enum):
    SCHEDULED = "scheduled"
    DUE = "due"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    MISSED = "missed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryMethod(str, Enum):
    DASHBOARD = "dashboard"
    GOOGLE_CALENDAR = "google_calendar"


class EventStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ProposedEvent(BaseModel):
    idempotency_key: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    start_time: str
    end_time: str
    duration_minutes: int = 30
    timezone: str = "Asia/Kolkata"
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None


class ProposedReminder(BaseModel):
    idempotency_key: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    scheduled_time: str
    offset_minutes: Optional[int] = None
    delivery_method: DeliveryMethod = DeliveryMethod.DASHBOARD
    target_type: str = "event"
    target_title: Optional[str] = None


class MultiActionBundle(BaseModel):
    thought_id: int
    raw_thought: str
    tasks: List[ExtractedTask] = []
    events: List[ProposedEvent] = []
    reminders: List[ProposedReminder] = []
    ambiguities: List[str] = []
    planner_notes: str = ""
    processing_time_ms: float = 0.0
    created_at: str


class ExecuteBundleRequest(BaseModel):
    thought_id: int
    tasks: List[ExtractedTask] = []
    events: List[ProposedEvent] = []
    reminders: List[ProposedReminder] = []


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_time: str
    end_time: str
    timezone: str = "Asia/Kolkata"


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timezone: Optional[str] = None
    status: Optional[EventStatus] = None


class CalendarEventResponse(BaseModel):
    id: int
    thought_id: Optional[int] = None
    external_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    timezone: str
    status: EventStatus
    is_synced: bool
    created_at: str
    updated_at: str


class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    scheduled_time: str
    offset_minutes: Optional[int] = None
    delivery_method: DeliveryMethod = DeliveryMethod.DASHBOARD
    task_id: Optional[int] = None
    event_id: Optional[int] = None


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_time: Optional[str] = None
    status: Optional[ReminderStatus] = None


class ReminderResponse(BaseModel):
    id: int
    thought_id: Optional[int] = None
    task_id: Optional[int] = None
    event_id: Optional[int] = None
    title: str
    scheduled_time: str
    offset_minutes: Optional[int] = None
    delivery_method: DeliveryMethod
    status: ReminderStatus
    delivered_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: str
    updated_at: str


class AgentActivityResponse(BaseModel):
    id: int
    thought_id: Optional[int] = None
    agent_name: str
    action_type: str
    summary: str
    status: str
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    created_at: str


class ExecutionResult(BaseModel):
    thought_id: int
    created_tasks: List[TaskResponse]
    created_events: List[CalendarEventResponse]
    created_reminders: List[ReminderResponse]
    activity_count: int


class GoogleIntegrationStatus(BaseModel):
    is_connected: bool
    email: Optional[str] = None
    client_id_configured: bool = False
    last_sync: Optional[str] = None
    pending_sync_count: int = 0


class GoogleAuthUrlResponse(BaseModel):
    auth_url: str
    csrf_state: str
