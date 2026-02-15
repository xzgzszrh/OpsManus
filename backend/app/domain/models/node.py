from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class SSHAuthType(str, Enum):
    PASSWORD = "password"
    PRIVATE_KEY = "private_key"


class SSHNode(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    user_id: str
    name: str
    description: Optional[str] = None
    remarks: Optional[str] = None

    ssh_enabled: bool = False
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_username: Optional[str] = None
    ssh_auth_type: SSHAuthType = SSHAuthType.PASSWORD
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    ssh_passphrase: Optional[str] = None
    ssh_require_approval: bool = False

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SSHOperationLog(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    session_id: Optional[str] = None
    node_id: str
    actor_type: str
    actor_id: Optional[str] = None
    source: str
    command: str
    output: str = ""
    success: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SSHApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SSHCommandApproval(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    session_id: str
    node_id: str
    command: str
    status: SSHApprovalStatus = SSHApprovalStatus.PENDING
    reject_reason: Optional[str] = None
    requested_by_tool_call_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: Optional[datetime] = None
