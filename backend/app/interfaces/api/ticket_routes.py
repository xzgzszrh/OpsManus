from fastapi import APIRouter, Depends

from app.application.services.ticket_service import TicketService
from app.domain.models.user import User
from app.interfaces.dependencies import get_current_user, get_ticket_service
from app.interfaces.schemas.base import APIResponse
from app.interfaces.schemas.ticket import (
    CreateTicketRequest,
    ListTicketsResponse,
    TicketReplyRequest,
    TicketResponse,
    UpdateTicketRequest,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=APIResponse[ListTicketsResponse])
async def list_tickets(
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> APIResponse[ListTicketsResponse]:
    tickets = await ticket_service.list_tickets(current_user.id)
    return APIResponse.success(
        ListTicketsResponse(
            tickets=[TicketResponse.from_model(ticket, include_comments=False, include_events=False) for ticket in tickets]
        )
    )


@router.post("", response_model=APIResponse[TicketResponse])
async def create_ticket(
    request: CreateTicketRequest,
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> APIResponse[TicketResponse]:
    ticket = await ticket_service.create_ticket(
        user=current_user,
        title=request.title,
        description=request.description,
        node_ids=request.node_ids,
        plugin_ids=request.plugin_ids,
        tags=request.tags,
        priority=request.priority,
        urgency=request.urgency,
        estimated_minutes=request.estimated_minutes,
        sla_hours=request.sla_hours,
    )
    return APIResponse.success(TicketResponse.from_model(ticket))


@router.get("/{ticket_id}", response_model=APIResponse[TicketResponse])
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> APIResponse[TicketResponse]:
    ticket = await ticket_service.get_ticket(ticket_id, current_user.id)
    return APIResponse.success(TicketResponse.from_model(ticket))


@router.post("/{ticket_id}/reply", response_model=APIResponse[TicketResponse])
async def reply_ticket(
    ticket_id: str,
    request: TicketReplyRequest,
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> APIResponse[TicketResponse]:
    ticket = await ticket_service.reply_ticket(ticket_id, current_user, request.message)
    return APIResponse.success(TicketResponse.from_model(ticket))


@router.put("/{ticket_id}", response_model=APIResponse[TicketResponse])
async def update_ticket(
    ticket_id: str,
    request: UpdateTicketRequest,
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> APIResponse[TicketResponse]:
    ticket = await ticket_service.update_ticket(
        ticket_id,
        current_user.id,
        status=request.status,
        priority=request.priority,
        urgency=request.urgency,
        tags=request.tags,
        estimated_minutes=request.estimated_minutes,
        spent_minutes=request.spent_minutes,
        sla_due_at=request.sla_due_at,
    )
    return APIResponse.success(TicketResponse.from_model(ticket))
