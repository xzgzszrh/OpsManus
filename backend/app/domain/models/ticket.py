from datetime import UTC, datetime
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    OPEN = "open"
    PROCESSING = "processing"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"


class TicketPriority(str, Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class TicketUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCommentRole(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class TicketEventType(str, Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    COMMENT_ADDED = "comment_added"
    AUTO_DISPATCHED = "auto_dispatched"
    AI_RESPONDED = "ai_responded"
    USER_REPLIED = "user_replied"
    LINKED_SESSION = "linked_session"


class TicketComment(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    role: TicketCommentRole
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TicketEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: TicketEventType
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.P2
    urgency: TicketUrgency = TicketUrgency.MEDIUM
    tags: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    plugin_ids: List[str] = Field(default_factory=list)
    session_id: str
    comments: List[TicketComment] = Field(default_factory=list)
    events: List[TicketEvent] = Field(default_factory=list)
    estimated_minutes: Optional[int] = None
    spent_minutes: int = 0
    sla_due_at: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    reopen_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
