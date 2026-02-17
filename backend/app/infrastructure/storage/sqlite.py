import asyncio
import logging
import os
from functools import lru_cache
from typing import Optional

import aiosqlite

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class _ConnectionContext:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def __aenter__(self) -> aiosqlite.Connection:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> Optional[bool]:
        await self._conn.close()
        return None


class SQLiteStorage:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return

            db_path = self._settings.sqlite_path
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

            async with aiosqlite.connect(db_path) as conn:
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA foreign_keys=ON;")
                await conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        fullname TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT,
                        role TEXT NOT NULL,
                        is_active INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        last_login_at TEXT
                    );

                    CREATE TABLE IF NOT EXISTS agents (
                        agent_id TEXT PRIMARY KEY,
                        model_name TEXT NOT NULL,
                        temperature REAL NOT NULL,
                        max_tokens INTEGER NOT NULL,
                        memories_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        sandbox_id TEXT,
                        agent_id TEXT NOT NULL,
                        task_id TEXT,
                        title TEXT,
                        unread_message_count INTEGER NOT NULL DEFAULT 0,
                        latest_message TEXT,
                        latest_message_at TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        events_json TEXT NOT NULL,
                        files_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        session_type TEXT NOT NULL DEFAULT 'chat',
                        is_shared INTEGER NOT NULL DEFAULT 0
                    );

                    CREATE INDEX IF NOT EXISTS idx_sessions_latest_message_at
                    ON sessions(latest_message_at DESC);

                    CREATE TABLE IF NOT EXISTS files (
                        file_id TEXT PRIMARY KEY,
                        filename TEXT,
                        content_type TEXT,
                        size INTEGER NOT NULL DEFAULT 0,
                        upload_date TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        user_id TEXT,
                        storage_path TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS server_nodes (
                        node_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        remarks TEXT,
                        ssh_enabled INTEGER NOT NULL DEFAULT 0,
                        ssh_host TEXT,
                        ssh_port INTEGER NOT NULL DEFAULT 22,
                        ssh_username TEXT,
                        ssh_auth_type TEXT NOT NULL DEFAULT 'password',
                        ssh_password TEXT,
                        ssh_private_key TEXT,
                        ssh_passphrase TEXT,
                        ssh_require_approval INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_server_nodes_user
                    ON server_nodes(user_id, updated_at DESC);

                    CREATE TABLE IF NOT EXISTS ssh_operation_logs (
                        log_id TEXT PRIMARY KEY,
                        session_id TEXT,
                        node_id TEXT NOT NULL,
                        actor_type TEXT NOT NULL,
                        actor_id TEXT,
                        source TEXT NOT NULL,
                        command TEXT NOT NULL,
                        output TEXT,
                        success INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_ssh_logs_node_time
                    ON ssh_operation_logs(node_id, created_at DESC);

                    CREATE TABLE IF NOT EXISTS ssh_command_approvals (
                        approval_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        node_id TEXT NOT NULL,
                        command TEXT NOT NULL,
                        status TEXT NOT NULL,
                        reject_reason TEXT,
                        requested_by_tool_call_id TEXT,
                        created_at TEXT NOT NULL,
                        decided_at TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_ssh_approval_session
                    ON ssh_command_approvals(session_id, created_at DESC);

                    CREATE TABLE IF NOT EXISTS tickets (
                        ticket_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        status TEXT NOT NULL,
                        priority TEXT NOT NULL DEFAULT 'p2',
                        urgency TEXT NOT NULL DEFAULT 'medium',
                        tags_json TEXT NOT NULL DEFAULT '[]',
                        node_ids_json TEXT NOT NULL,
                        plugin_ids_json TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        comments_json TEXT NOT NULL,
                        events_json TEXT NOT NULL DEFAULT '[]',
                        estimated_minutes INTEGER,
                        spent_minutes INTEGER NOT NULL DEFAULT 0,
                        sla_due_at TEXT,
                        first_response_at TEXT,
                        resolved_at TEXT,
                        reopen_count INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_tickets_user_updated
                    ON tickets(user_id, updated_at DESC);

                    CREATE INDEX IF NOT EXISTS idx_tickets_session
                    ON tickets(session_id);
                    """
                )
                # Lightweight migrations for existing DBs.
                cursor = await conn.execute("PRAGMA table_info(sessions)")
                columns = [row[1] for row in await cursor.fetchall()]
                if "session_type" not in columns:
                    await conn.execute("ALTER TABLE sessions ADD COLUMN session_type TEXT NOT NULL DEFAULT 'chat'")

                ticket_cursor = await conn.execute("PRAGMA table_info(tickets)")
                ticket_columns = [row[1] for row in await ticket_cursor.fetchall()]
                ticket_migrations = [
                    ("priority", "ALTER TABLE tickets ADD COLUMN priority TEXT NOT NULL DEFAULT 'p2'"),
                    ("urgency", "ALTER TABLE tickets ADD COLUMN urgency TEXT NOT NULL DEFAULT 'medium'"),
                    ("tags_json", "ALTER TABLE tickets ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'"),
                    ("events_json", "ALTER TABLE tickets ADD COLUMN events_json TEXT NOT NULL DEFAULT '[]'"),
                    ("estimated_minutes", "ALTER TABLE tickets ADD COLUMN estimated_minutes INTEGER"),
                    ("spent_minutes", "ALTER TABLE tickets ADD COLUMN spent_minutes INTEGER NOT NULL DEFAULT 0"),
                    ("sla_due_at", "ALTER TABLE tickets ADD COLUMN sla_due_at TEXT"),
                    ("first_response_at", "ALTER TABLE tickets ADD COLUMN first_response_at TEXT"),
                    ("resolved_at", "ALTER TABLE tickets ADD COLUMN resolved_at TEXT"),
                    ("reopen_count", "ALTER TABLE tickets ADD COLUMN reopen_count INTEGER NOT NULL DEFAULT 0"),
                ]
                for column_name, ddl in ticket_migrations:
                    if column_name not in ticket_columns:
                        await conn.execute(ddl)
                await conn.commit()

            self._initialized = True
            logger.info("Successfully initialized SQLite at %s", db_path)

    async def shutdown(self) -> None:
        # Connections are opened per-operation; nothing persistent to close.
        self._initialized = False

    async def connect(self) -> _ConnectionContext:
        if not self._initialized:
            raise RuntimeError("SQLite not initialized. Call initialize() first.")

        conn = await aiosqlite.connect(self._settings.sqlite_path)
        conn.row_factory = aiosqlite.Row
        return _ConnectionContext(conn)


@lru_cache()
def get_sqlite() -> SQLiteStorage:
    return SQLiteStorage()
