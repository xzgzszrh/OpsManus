import json
from datetime import UTC, datetime
from typing import List, Optional

from app.domain.models.ticket import Ticket, TicketComment, TicketStatus
from app.infrastructure.storage.sqlite import get_sqlite


class SQLiteTicketRepository:
    def _row_to_ticket(self, row) -> Ticket:
        return Ticket.model_validate(
            {
                "id": row["ticket_id"],
                "user_id": row["user_id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "priority": row["priority"],
                "urgency": row["urgency"],
                "tags": json.loads(row["tags_json"]),
                "node_ids": json.loads(row["node_ids_json"]),
                "plugin_ids": json.loads(row["plugin_ids_json"]),
                "session_id": row["session_id"],
                "comments": json.loads(row["comments_json"]),
                "events": json.loads(row["events_json"]),
                "estimated_minutes": row["estimated_minutes"],
                "spent_minutes": row["spent_minutes"],
                "sla_due_at": row["sla_due_at"],
                "first_response_at": row["first_response_at"],
                "resolved_at": row["resolved_at"],
                "reopen_count": row["reopen_count"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    async def save(self, ticket: Ticket) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                INSERT INTO tickets (
                    ticket_id, user_id, title, description, status, priority, urgency, tags_json,
                    node_ids_json, plugin_ids_json, session_id,
                    comments_json, events_json, estimated_minutes, spent_minutes,
                    sla_due_at, first_response_at, resolved_at, reopen_count,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket_id) DO UPDATE SET
                    user_id=excluded.user_id,
                    title=excluded.title,
                    description=excluded.description,
                    status=excluded.status,
                    priority=excluded.priority,
                    urgency=excluded.urgency,
                    tags_json=excluded.tags_json,
                    node_ids_json=excluded.node_ids_json,
                    plugin_ids_json=excluded.plugin_ids_json,
                    session_id=excluded.session_id,
                    comments_json=excluded.comments_json,
                    events_json=excluded.events_json,
                    estimated_minutes=excluded.estimated_minutes,
                    spent_minutes=excluded.spent_minutes,
                    sla_due_at=excluded.sla_due_at,
                    first_response_at=excluded.first_response_at,
                    resolved_at=excluded.resolved_at,
                    reopen_count=excluded.reopen_count,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    ticket.id,
                    ticket.user_id,
                    ticket.title,
                    ticket.description,
                    ticket.status.value,
                    ticket.priority.value,
                    ticket.urgency.value,
                    json.dumps(ticket.tags),
                    json.dumps(ticket.node_ids),
                    json.dumps(ticket.plugin_ids),
                    ticket.session_id,
                    json.dumps([comment.model_dump(mode="json") for comment in ticket.comments]),
                    json.dumps([event.model_dump(mode="json") for event in ticket.events]),
                    ticket.estimated_minutes,
                    ticket.spent_minutes,
                    ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
                    ticket.first_response_at.isoformat() if ticket.first_response_at else None,
                    ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                    ticket.reopen_count,
                    ticket.created_at.isoformat(),
                    ticket.updated_at.isoformat(),
                ),
            )
            await conn.commit()

    async def find_by_id(self, ticket_id: str, user_id: Optional[str] = None) -> Optional[Ticket]:
        async with await get_sqlite().connect() as conn:
            if user_id:
                cursor = await conn.execute(
                    "SELECT * FROM tickets WHERE ticket_id = ? AND user_id = ?",
                    (ticket_id, user_id),
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM tickets WHERE ticket_id = ?",
                    (ticket_id,),
                )
            row = await cursor.fetchone()
            return self._row_to_ticket(row) if row else None

    async def find_by_session_id(self, session_id: str) -> Optional[Ticket]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM tickets WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_ticket(row) if row else None

    async def list_by_user_id(self, user_id: str) -> List[Ticket]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM tickets WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_ticket(row) for row in rows]

    async def append_comment(self, ticket_id: str, comment: TicketComment) -> Ticket:
        ticket = await self.find_by_id(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        ticket.comments.append(comment)
        ticket.updated_at = datetime.now(UTC)
        await self.save(ticket)
        return ticket

    async def update_status(self, ticket_id: str, status: TicketStatus) -> Ticket:
        ticket = await self.find_by_id(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        ticket.status = status
        ticket.updated_at = datetime.now(UTC)
        await self.save(ticket)
        return ticket
