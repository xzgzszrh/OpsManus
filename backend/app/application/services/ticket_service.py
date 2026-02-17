import asyncio
from datetime import UTC, datetime, timedelta
from typing import List, Optional

from app.application.errors.exceptions import BadRequestError, NotFoundError
from app.application.services.agent_service import AgentService
from app.domain.models.session import SessionType
from app.domain.models.ticket import (
    Ticket,
    TicketComment,
    TicketCommentRole,
    TicketEvent,
    TicketEventType,
    TicketPriority,
    TicketStatus,
    TicketUrgency,
)
from app.domain.models.user import User
from app.infrastructure.repositories.sqlite_ticket_repository import SQLiteTicketRepository


class TicketService:
    def __init__(self, repository: SQLiteTicketRepository, agent_service: AgentService):
        self._repository = repository
        self._agent_service = agent_service

    async def create_ticket(
        self,
        user: User,
        title: str,
        description: str,
        node_ids: Optional[List[str]] = None,
        plugin_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        priority: TicketPriority = TicketPriority.P2,
        urgency: TicketUrgency = TicketUrgency.MEDIUM,
        estimated_minutes: Optional[int] = None,
        sla_hours: Optional[int] = None,
    ) -> Ticket:
        title = title.strip()
        description = description.strip()
        if not title:
            raise BadRequestError("Ticket title is required")
        if not description:
            raise BadRequestError("Ticket description is required")

        session = await self._agent_service.create_session(user.id, session_type=SessionType.TICKET)
        now = datetime.now(UTC)
        ticket = Ticket(
            user_id=user.id,
            title=title,
            description=description,
            node_ids=node_ids or [],
            plugin_ids=plugin_ids or [],
            tags=[tag.strip() for tag in (tags or []) if tag.strip()],
            priority=priority,
            urgency=urgency,
            estimated_minutes=estimated_minutes,
            sla_due_at=(now + timedelta(hours=sla_hours)) if sla_hours else None,
            session_id=session.id,
            comments=[
                TicketComment(
                    role=TicketCommentRole.SYSTEM,
                    message="Ticket created and assigned to AI",
                )
            ],
            events=[
                TicketEvent(event_type=TicketEventType.CREATED, message="Ticket created"),
                TicketEvent(
                    event_type=TicketEventType.LINKED_SESSION,
                    message=f"Linked to backend session {session.id}",
                ),
            ],
        )
        await self._repository.save(ticket)

        asyncio.create_task(
            self._dispatch_to_ai(
                ticket=ticket,
                user_id=user.id,
                message=self._build_ticket_dispatch_prompt(ticket),
                next_status=TicketStatus.PROCESSING,
            )
        )

        return ticket

    async def list_tickets(self, user_id: str) -> List[Ticket]:
        return await self._repository.list_by_user_id(user_id)

    async def get_ticket(self, ticket_id: str, user_id: str) -> Ticket:
        ticket = await self._repository.find_by_id(ticket_id, user_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        return ticket

    async def get_ticket_for_tool(self, ticket_id: str) -> Ticket:
        ticket = await self._repository.find_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        return ticket

    async def get_ticket_by_session(self, session_id: str) -> Optional[Ticket]:
        return await self._repository.find_by_session_id(session_id)

    async def reply_ticket(self, ticket_id: str, user: User, message: str) -> Ticket:
        ticket = await self.get_ticket(ticket_id, user.id)
        clean_message = message.strip()
        if not clean_message:
            raise BadRequestError("Reply message is required")

        ticket.comments.append(TicketComment(role=TicketCommentRole.USER, message=clean_message))
        ticket.events.append(TicketEvent(event_type=TicketEventType.USER_REPLIED, message="User added a reply"))
        ticket.status = TicketStatus.PROCESSING
        ticket.updated_at = datetime.now(UTC)
        await self._repository.save(ticket)

        asyncio.create_task(
            self._dispatch_to_ai(
                ticket=ticket,
                user_id=user.id,
                message=(
                    f"Ticket {ticket.id} has an update from user. "
                    f"Please check and continue processing.\n\n"
                    f"User reply:\n{clean_message}"
                ),
                next_status=TicketStatus.PROCESSING,
            )
        )

        return ticket

    async def ai_reply_ticket(
        self,
        ticket_id: str,
        message: str,
        waiting_user: bool = False,
    ) -> Ticket:
        ticket = await self._repository.find_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        clean_message = message.strip()
        if not clean_message:
            raise BadRequestError("Reply message is required")

        ticket.comments.append(TicketComment(role=TicketCommentRole.AI, message=clean_message))
        ticket.events.append(TicketEvent(event_type=TicketEventType.AI_RESPONDED, message="AI posted an update"))
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.now(UTC)
        ticket.status = TicketStatus.WAITING_USER if waiting_user else TicketStatus.PROCESSING
        ticket.updated_at = datetime.now(UTC)
        await self._repository.save(ticket)
        return ticket

    async def update_ticket(
        self,
        ticket_id: str,
        user_id: str,
        *,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        urgency: Optional[TicketUrgency] = None,
        tags: Optional[List[str]] = None,
        estimated_minutes: Optional[int] = None,
        spent_minutes: Optional[int] = None,
        sla_due_at: Optional[datetime] = None,
    ) -> Ticket:
        ticket = await self.get_ticket(ticket_id, user_id)
        now = datetime.now(UTC)

        if status and status != ticket.status:
            if ticket.status == TicketStatus.RESOLVED and status != TicketStatus.RESOLVED:
                ticket.reopen_count += 1
            ticket.status = status
            ticket.events.append(TicketEvent(event_type=TicketEventType.STATUS_CHANGED, message=f"Status changed to {status.value}"))
            if status == TicketStatus.RESOLVED:
                ticket.resolved_at = now

        if priority:
            ticket.priority = priority
        if urgency:
            ticket.urgency = urgency
        if tags is not None:
            ticket.tags = [tag.strip() for tag in tags if tag.strip()]
        if estimated_minutes is not None:
            ticket.estimated_minutes = max(0, estimated_minutes)
        if spent_minutes is not None:
            ticket.spent_minutes = max(0, spent_minutes)
        if sla_due_at is not None:
            ticket.sla_due_at = sla_due_at

        ticket.updated_at = now
        await self._repository.save(ticket)
        return ticket

    async def update_ticket_status(self, ticket_id: str, status: TicketStatus) -> Ticket:
        ticket = await self._repository.find_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        ticket.status = status
        ticket.events.append(TicketEvent(event_type=TicketEventType.STATUS_CHANGED, message=f"Status changed to {status.value}"))
        if status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(UTC)
        ticket.updated_at = datetime.now(UTC)
        await self._repository.save(ticket)
        return ticket

    async def _dispatch_to_ai(
        self,
        ticket: Ticket,
        user_id: str,
        message: str,
        next_status: TicketStatus,
    ) -> None:
        latest = await self._repository.find_by_id(ticket.id)
        if not latest:
            return
        latest.status = next_status
        latest.events.append(TicketEvent(event_type=TicketEventType.AUTO_DISPATCHED, message="Dispatched to AI"))
        latest.updated_at = datetime.now(UTC)
        await self._repository.save(latest)

        try:
            async for _ in self._agent_service.chat(
                session_id=ticket.session_id,
                user_id=user_id,
                message=message,
                timestamp=datetime.now(UTC),
            ):
                continue
        except Exception as exc:
            latest = await self._repository.find_by_id(ticket.id)
            if latest:
                latest.status = TicketStatus.WAITING_USER
                latest.comments.append(
                    TicketComment(
                        role=TicketCommentRole.SYSTEM,
                        message=f"AI dispatch failed: {str(exc)}",
                    )
                )
                latest.events.append(TicketEvent(event_type=TicketEventType.AI_RESPONDED, message="AI dispatch failed"))
                latest.updated_at = datetime.now(UTC)
                await self._repository.save(latest)

    @staticmethod
    def _build_ticket_dispatch_prompt(ticket: Ticket) -> str:
        node_text = ", ".join(ticket.node_ids) if ticket.node_ids else "(none)"
        plugin_text = ", ".join(ticket.plugin_ids) if ticket.plugin_ids else "(none)"
        tags_text = ", ".join(ticket.tags) if ticket.tags else "(none)"
        return (
            f"Please check ticket [{ticket.id}] and solve it.\n\n"
            f"Title: {ticket.title}\n"
            f"Description: {ticket.description}\n"
            f"Priority: {ticket.priority.value}\n"
            f"Urgency: {ticket.urgency.value}\n"
            f"Tags: {tags_text}\n"
            f"Related nodes: {node_text}\n"
            f"Related plugins: {plugin_text}\n\n"
            f"You can use ticket tools to read/update/reply this ticket."
        )
