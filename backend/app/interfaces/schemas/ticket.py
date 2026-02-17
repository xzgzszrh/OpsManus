from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.models.ticket import (
    Ticket,
    TicketComment,
    TicketCommentRole,
    TicketEvent,
    TicketPriority,
    TicketStatus,
    TicketUrgency,
)


class CreateTicketRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    node_ids: List[str] = Field(default_factory=list)
    plugin_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    priority: TicketPriority = TicketPriority.P2
    urgency: TicketUrgency = TicketUrgency.MEDIUM
    estimated_minutes: Optional[int] = Field(default=None, ge=0, le=60 * 24 * 30)
    sla_hours: Optional[int] = Field(default=None, ge=1, le=24 * 90)


class TicketReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class UpdateTicketRequest(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    urgency: Optional[TicketUrgency] = None
    tags: Optional[List[str]] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0, le=60 * 24 * 30)
    spent_minutes: Optional[int] = Field(default=None, ge=0, le=60 * 24 * 30)
    sla_due_at: Optional[datetime] = None


class TicketCommentResponse(BaseModel):
    comment_id: str
    role: TicketCommentRole
    message: str
    created_at: datetime

    @classmethod
    def from_model(cls, comment: TicketComment) -> "TicketCommentResponse":
        return cls(
            comment_id=comment.id,
            role=comment.role,
            message=comment.message,
            created_at=comment.created_at,
        )


class TicketEventResponse(BaseModel):
    event_id: str
    event_type: str
    message: str
    created_at: datetime

    @classmethod
    def from_model(cls, event: TicketEvent) -> "TicketEventResponse":
        return cls(
            event_id=event.id,
            event_type=event.event_type.value,
            message=event.message,
            created_at=event.created_at,
        )


class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    urgency: TicketUrgency
    tags: List[str]
    node_ids: List[str]
    plugin_ids: List[str]
    session_id: str
    comments: List[TicketCommentResponse]
    events: List[TicketEventResponse]
    estimated_minutes: Optional[int]
    spent_minutes: int
    sla_due_at: Optional[datetime]
    first_response_at: Optional[datetime]
    resolved_at: Optional[datetime]
    reopen_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, ticket: Ticket, include_comments: bool = True) -> "TicketResponse":
        return cls(
            ticket_id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            urgency=ticket.urgency,
            tags=ticket.tags,
            node_ids=ticket.node_ids,
            plugin_ids=ticket.plugin_ids,
            session_id=ticket.session_id,
            comments=[TicketCommentResponse.from_model(comment) for comment in ticket.comments] if include_comments else [],
            events=[TicketEventResponse.from_model(event) for event in ticket.events],
            estimated_minutes=ticket.estimated_minutes,
            spent_minutes=ticket.spent_minutes,
            sla_due_at=ticket.sla_due_at,
            first_response_at=ticket.first_response_at,
            resolved_at=ticket.resolved_at,
            reopen_count=ticket.reopen_count,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )


class ListTicketsResponse(BaseModel):
    tickets: List[TicketResponse]
