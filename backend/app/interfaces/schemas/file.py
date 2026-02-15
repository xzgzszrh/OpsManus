from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.domain.models.file import FileInfo


class FileViewRequest(BaseModel):
    """File view request schema"""
    file: str


class FileViewResponse(BaseModel):
    """File view response schema"""
    content: str
    file: str


class FileInfoResponse(BaseModel):
    """File info response schema"""
    file_id: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str]
    size: int = 0
    upload_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]]
    file_url: Optional[str]

    @staticmethod
    async def from_file_info(file_info: FileInfo) -> "FileInfoResponse":
        from app.interfaces.dependencies import get_file_service
        file_service = get_file_service()
        file_url = None
        if file_info.file_id:
            try:
                file_url = await file_service.create_signed_url(file_info.file_id)
            except FileNotFoundError:
                # Keep session/event readable even if historical attachment file is missing.
                file_url = None
            except Exception:
                file_url = None
        return FileInfoResponse(
            file_id=file_info.file_id,
            filename=file_info.filename,
            content_type=file_info.content_type,
            size=file_info.size or 0,
            upload_date=file_info.upload_date,
            metadata=file_info.metadata,
            file_url=file_url
        )
