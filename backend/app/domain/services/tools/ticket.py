from datetime import UTC, datetime
from typing import Optional

from app.domain.models.ticket import (
    TicketComment,
    TicketCommentRole,
    TicketEvent,
    TicketEventType,
    TicketStatus,
)
from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseTool, tool
from app.infrastructure.repositories.sqlite_ticket_repository import SQLiteTicketRepository


class TicketTool(BaseTool):
    name: str = "ticket"

    def __init__(self, repository: SQLiteTicketRepository, session_id: str):
        super().__init__()
        self._repository = repository
        self._session_id = session_id

    async def _resolve_ticket_id(self, ticket_id: Optional[str]) -> str:
        if ticket_id:
            return ticket_id
        ticket = await self._repository.find_by_session_id(self._session_id)
        if not ticket:
            raise ValueError("No ticket bound to current session")
        return ticket.id

    @tool(
        name="ticket_get",
        description="Get current ticket details by ticket_id or current session ticket.",
        parameters={
            "ticket_id": {
                "type": "string",
                "description": "Optional ticket id. If not given, uses current session ticket.",
            }
        },
        required=[],
    )
    async def ticket_get(self, ticket_id: Optional[str] = None) -> ToolResult:
        resolved_id = await self._resolve_ticket_id(ticket_id)
        ticket = await self._repository.find_by_id(resolved_id)
        if not ticket:
            raise ValueError("Ticket not found")
        return ToolResult(
            success=True,
            data={
                "ticket_id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "urgency": ticket.urgency.value,
                "tags": ticket.tags,
                "node_ids": ticket.node_ids,
                "plugin_ids": ticket.plugin_ids,
                "session_id": ticket.session_id,
                "comments": [comment.model_dump(mode="json") for comment in ticket.comments[-20:]],
                "events": [event.model_dump(mode="json") for event in ticket.events[-20:]],
            },
        )

    @tool(
        name="ticket_update_status",
        description="Update ticket status when progress changes.",
        parameters={
            "status": {
                "type": "string",
                "enum": [
                    TicketStatus.OPEN.value,
                    TicketStatus.PROCESSING.value,
                    TicketStatus.WAITING_USER.value,
                    TicketStatus.RESOLVED.value,
                ],
                "description": "New ticket status",
            },
            "ticket_id": {
                "type": "string",
                "description": "Optional ticket id. If not provided, update current session ticket.",
            },
        },
        required=["status"],
    )
    async def ticket_update_status(self, status: str, ticket_id: Optional[str] = None) -> ToolResult:
        resolved_id = await self._resolve_ticket_id(ticket_id)
        ticket = await self._repository.find_by_id(resolved_id)
        if not ticket:
            raise ValueError("Ticket not found")
        new_status = TicketStatus(status)
        if ticket.status == TicketStatus.RESOLVED and new_status != TicketStatus.RESOLVED:
            ticket.reopen_count += 1
        ticket.status = new_status
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(UTC)
        ticket.events.append(TicketEvent(event_type=TicketEventType.STATUS_CHANGED, message=f"Status changed to {new_status.value}"))
        ticket.updated_at = datetime.now(UTC)
        await self._repository.save(ticket)
        return ToolResult(success=True, data={"ticket_id": ticket.id, "status": ticket.status.value})

    @tool(
        name="ticket_reply",
        description="Reply to ticket with progress, result, or request for user input.",
        parameters={
            "message": {
                "type": "string",
                "description": "Reply content to post into the ticket.",
            },
            "waiting_user": {
                "type": "boolean",
                "description": "Set true if user needs to provide more information.",
            },
            "ticket_id": {
                "type": "string",
                "description": "Optional ticket id. If not given, use current session ticket.",
            },
        },
        required=["message"],
    )
    async def ticket_reply(
        self,
        message: str,
        waiting_user: bool = False,
        ticket_id: Optional[str] = None,
    ) -> ToolResult:
        resolved_id = await self._resolve_ticket_id(ticket_id)
        ticket = await self._repository.find_by_id(resolved_id)
        if not ticket:
            raise ValueError("Ticket not found")
        ticket.comments.append(
            TicketComment(
                role=TicketCommentRole.AI,
                message=message.strip(),
            )
        )
        ticket.events.append(TicketEvent(event_type=TicketEventType.AI_RESPONDED, message="AI posted a ticket reply"))
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.now(UTC)
        ticket.status = TicketStatus.WAITING_USER if waiting_user else TicketStatus.PROCESSING
        ticket.updated_at = datetime.now(UTC)
        await self._repository.save(ticket)
        return ToolResult(success=True, data={"ticket_id": ticket.id, "status": ticket.status.value})
