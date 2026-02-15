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
                    """
                )
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
