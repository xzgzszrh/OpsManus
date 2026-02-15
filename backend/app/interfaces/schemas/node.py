from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field

from app.domain.models.node import SSHNode, SSHOperationLog, SSHCommandApproval, SSHApprovalStatus


class ServerNodeBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)
    remarks: Optional[str] = Field(default=None, max_length=1000)

    ssh_enabled: bool = False
    ssh_host: Optional[str] = Field(default=None, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_username: Optional[str] = Field(default=None, max_length=128)
    ssh_auth_type: Literal["password", "private_key"] = "password"
    ssh_password: Optional[str] = Field(default=None, max_length=2048)
    ssh_private_key: Optional[str] = Field(default=None, max_length=20000)
    ssh_passphrase: Optional[str] = Field(default=None, max_length=2048)
    ssh_require_approval: bool = False


class CreateServerNodeRequest(ServerNodeBase):
    pass


class UpdateServerNodeRequest(ServerNodeBase):
    pass


class ServerNodeResponse(BaseModel):
    node_id: str
    name: str
    description: Optional[str] = None
    remarks: Optional[str] = None

    ssh_enabled: bool
    ssh_host: Optional[str] = None
    ssh_port: int
    ssh_username: Optional[str] = None
    ssh_auth_type: Literal["password", "private_key"]
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    ssh_passphrase: Optional[str] = None
    ssh_require_approval: bool

    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, node: SSHNode) -> "ServerNodeResponse":
        return cls(
            node_id=node.id,
            name=node.name,
            description=node.description,
            remarks=node.remarks,
            ssh_enabled=node.ssh_enabled,
            ssh_host=node.ssh_host,
            ssh_port=node.ssh_port,
            ssh_username=node.ssh_username,
            ssh_auth_type=node.ssh_auth_type.value,
            ssh_password=node.ssh_password,
            ssh_private_key=node.ssh_private_key,
            ssh_passphrase=node.ssh_passphrase,
            ssh_require_approval=node.ssh_require_approval,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )


class ListServerNodesResponse(BaseModel):
    nodes: List[ServerNodeResponse]


class SSHExecRequest(BaseModel):
    command: str = Field(min_length=1, max_length=8000)
    exec_dir: Optional[str] = None
    sync_to_ai: bool = False
    session_id: Optional[str] = None


class SSHExecResponse(BaseModel):
    success: bool
    output: str
    command: str
    node_id: str
    node_name: str


class SSHMonitorResponse(BaseModel):
    node_id: str
    node_name: str
    system_info: str


class SSHLogItem(BaseModel):
    log_id: str
    session_id: Optional[str]
    actor_type: str
    actor_id: Optional[str] = None
    source: str
    command: str
    output: str
    success: bool
    created_at: datetime

    @classmethod
    def from_model(cls, log: SSHOperationLog) -> "SSHLogItem":
        return cls(
            log_id=log.id,
            session_id=log.session_id,
            actor_type=log.actor_type,
            actor_id=log.actor_id,
            source=log.source,
            command=log.command,
            output=log.output,
            success=log.success,
            created_at=log.created_at,
        )


class SSHLogsResponse(BaseModel):
    logs: List[SSHLogItem]


class PendingApprovalItem(BaseModel):
    approval_id: str
    session_id: str
    node_id: str
    command: str
    status: SSHApprovalStatus
    reject_reason: Optional[str]
    created_at: datetime

    @classmethod
    def from_model(cls, model: SSHCommandApproval) -> "PendingApprovalItem":
        return cls(
            approval_id=model.id,
            session_id=model.session_id,
            node_id=model.node_id,
            command=model.command,
            status=model.status,
            reject_reason=model.reject_reason,
            created_at=model.created_at,
        )


class PendingApprovalListResponse(BaseModel):
    approvals: List[PendingApprovalItem]


class DecideApprovalRequest(BaseModel):
    approve: bool
    reject_reason: Optional[str] = None


class DecideApprovalResponse(BaseModel):
    approval_id: str
    status: SSHApprovalStatus
    output: Optional[str] = None
