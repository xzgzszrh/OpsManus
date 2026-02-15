import io
import json
import os
import shutil
import uuid
import asyncio
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, BinaryIO, Dict, Optional, Tuple

from app.core.config import get_settings
from app.domain.external.file import FileStorage
from app.domain.models.file import FileInfo
from app.infrastructure.storage.sqlite import SQLiteStorage, get_sqlite


class LocalFileStorage(FileStorage):
    """Local filesystem + SQLite metadata file storage."""

    def __init__(self, sqlite: SQLiteStorage):
        self.sqlite = sqlite
        self.settings = get_settings()
        os.makedirs(self.settings.file_storage_path, exist_ok=True)

    def _storage_path(self, file_id: str) -> str:
        return os.path.join(self.settings.file_storage_path, file_id)

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        user_id: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FileInfo:
        file_id = uuid.uuid4().hex
        upload_date = datetime.now(UTC)
        storage_path = self._storage_path(file_id)
        file_metadata = metadata or {}

        def _write_file() -> int:
            try:
                file_data.seek(0)
            except Exception:
                pass
            with open(storage_path, "wb") as f:
                shutil.copyfileobj(file_data, f)
            return os.path.getsize(storage_path)

        size = await asyncio.to_thread(_write_file)

        async with await self.sqlite.connect() as conn:
            await conn.execute(
                """
                INSERT INTO files (
                    file_id, filename, content_type, size, upload_date, metadata_json, user_id, storage_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    filename,
                    content_type,
                    size,
                    upload_date.isoformat(),
                    json.dumps(file_metadata),
                    user_id,
                    storage_path,
                ),
            )
            await conn.commit()

        return FileInfo(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            size=size,
            upload_date=upload_date,
            metadata=file_metadata,
            user_id=user_id,
        )

    async def _get_file_row(self, file_id: str):
        async with await self.sqlite.connect() as conn:
            cursor = await conn.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
            return await cursor.fetchone()

    def _to_file_info(self, row) -> FileInfo:
        return FileInfo(
            file_id=row["file_id"],
            filename=row["filename"],
            content_type=row["content_type"],
            size=row["size"],
            upload_date=row["upload_date"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            user_id=row["user_id"],
        )

    async def download_file(self, file_id: str, user_id: Optional[str] = None) -> Tuple[BinaryIO, FileInfo]:
        row = await self._get_file_row(file_id)
        if not row:
            raise FileNotFoundError(f"File not found with ID: {file_id}")
        if not os.path.exists(row["storage_path"]):
            raise FileNotFoundError(f"File content not found with ID: {file_id}")

        def _read_file() -> bytes:
            with open(row["storage_path"], "rb") as f:
                return f.read()

        content = await asyncio.to_thread(_read_file)
        stream = io.BytesIO(content)
        stream.seek(0)
        return stream, self._to_file_info(row)

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        row = await self._get_file_row(file_id)
        if not row:
            return False

        if os.path.exists(row["storage_path"]):
            await asyncio.to_thread(os.remove, row["storage_path"])

        async with await self.sqlite.connect() as conn:
            await conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
            await conn.commit()
        return True

    async def get_file_info(self, file_id: str, user_id: Optional[str] = None) -> Optional[FileInfo]:
        row = await self._get_file_row(file_id)
        if not row:
            return None
        return self._to_file_info(row)


@lru_cache()
def get_file_storage() -> FileStorage:
    return LocalFileStorage(sqlite=get_sqlite())
