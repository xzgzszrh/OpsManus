import json
from datetime import UTC, datetime
from typing import List, Optional

from app.domain.models.event import BaseEvent
from app.domain.models.file import FileInfo
from app.domain.models.session import Session, SessionStatus
from app.domain.repositories.session_repository import SessionRepository
from app.infrastructure.storage.sqlite import get_sqlite


class SQLiteSessionRepository(SessionRepository):
    async def save(self, session: Session) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (
                    session_id, user_id, sandbox_id, agent_id, task_id, title,
                    unread_message_count, latest_message, latest_message_at,
                    created_at, updated_at, events_json, files_json, status, is_shared
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_id=excluded.user_id,
                    sandbox_id=excluded.sandbox_id,
                    agent_id=excluded.agent_id,
                    task_id=excluded.task_id,
                    title=excluded.title,
                    unread_message_count=excluded.unread_message_count,
                    latest_message=excluded.latest_message,
                    latest_message_at=excluded.latest_message_at,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    events_json=excluded.events_json,
                    files_json=excluded.files_json,
                    status=excluded.status,
                    is_shared=excluded.is_shared
                """,
                (
                    session.id,
                    session.user_id,
                    session.sandbox_id,
                    session.agent_id,
                    session.task_id,
                    session.title,
                    session.unread_message_count,
                    session.latest_message,
                    session.latest_message_at.isoformat() if session.latest_message_at else None,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    json.dumps([event.model_dump(mode="json") for event in session.events]),
                    json.dumps([file_info.model_dump(mode="json") for file_info in session.files]),
                    session.status.value,
                    int(session.is_shared),
                ),
            )
            await conn.commit()

    def _row_to_session(self, row) -> Session:
        return Session.model_validate(
            {
                "id": row["session_id"],
                "user_id": row["user_id"],
                "sandbox_id": row["sandbox_id"],
                "agent_id": row["agent_id"],
                "task_id": row["task_id"],
                "title": row["title"],
                "unread_message_count": row["unread_message_count"],
                "latest_message": row["latest_message"],
                "latest_message_at": row["latest_message_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "events": json.loads(row["events_json"]),
                "files": json.loads(row["files_json"]),
                "status": row["status"],
                "is_shared": bool(row["is_shared"]),
            }
        )

    async def find_by_id(self, session_id: str) -> Optional[Session]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_session(row) if row else None

    async def find_by_user_id(self, user_id: str) -> List[Session]:
        # Single-tenant mode: user_id is ignored, return all sessions.
        return await self.get_all()

    async def find_by_id_and_user_id(self, session_id: str, user_id: str) -> Optional[Session]:
        # Single-tenant mode: user_id is ignored.
        return await self.find_by_id(session_id)

    async def _load_or_raise(self, session_id: str) -> Session:
        session = await self.find_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session

    async def update_title(self, session_id: str, title: str) -> None:
        session = await self._load_or_raise(session_id)
        session.title = title
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def update_latest_message(self, session_id: str, message: str, timestamp: datetime) -> None:
        session = await self._load_or_raise(session_id)
        session.latest_message = message
        session.latest_message_at = timestamp
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def add_event(self, session_id: str, event: BaseEvent) -> None:
        session = await self._load_or_raise(session_id)
        session.events.append(event)
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def add_file(self, session_id: str, file_info: FileInfo) -> None:
        session = await self._load_or_raise(session_id)
        session.files.append(file_info)
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def remove_file(self, session_id: str, file_id: str) -> None:
        session = await self._load_or_raise(session_id)
        session.files = [file_info for file_info in session.files if file_info.file_id != file_id]
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def get_file_by_path(self, session_id: str, file_path: str) -> Optional[FileInfo]:
        session = await self._load_or_raise(session_id)
        for file_info in session.files:
            if file_info.file_path == file_path:
                return file_info
        return None

    async def delete(self, session_id: str) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await conn.commit()

    async def get_all(self) -> List[Session]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions ORDER BY latest_message_at DESC"
            )
            rows = await cursor.fetchall()
            return [self._row_to_session(row) for row in rows]

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        session = await self._load_or_raise(session_id)
        session.status = status
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def update_unread_message_count(self, session_id: str, count: int) -> None:
        session = await self._load_or_raise(session_id)
        session.unread_message_count = count
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def increment_unread_message_count(self, session_id: str) -> None:
        session = await self._load_or_raise(session_id)
        session.unread_message_count += 1
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def decrement_unread_message_count(self, session_id: str) -> None:
        session = await self._load_or_raise(session_id)
        session.unread_message_count -= 1
        session.updated_at = datetime.now(UTC)
        await self.save(session)

    async def update_shared_status(self, session_id: str, is_shared: bool) -> None:
        session = await self._load_or_raise(session_id)
        session.is_shared = is_shared
        session.updated_at = datetime.now(UTC)
        await self.save(session)
