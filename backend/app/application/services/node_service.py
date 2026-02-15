from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import io
from typing import Any, Dict, List, Optional

from app.domain.models.node import SSHApprovalStatus, SSHCommandApproval, SSHNode, SSHOperationLog
from app.domain.models.event import MessageEvent
from app.domain.models.tool_result import ToolResult
from app.domain.repositories.session_repository import SessionRepository
from app.infrastructure.repositories.sqlite_node_repository import SQLiteNodeRepository
from app.application.errors.exceptions import BadRequestError, NotFoundError


class NodeService:
    MAX_NODES_PER_USER = 8

    def __init__(self, repository: SQLiteNodeRepository, session_repository: SessionRepository):
        self._repository = repository
        self._session_repository = session_repository

    async def list_nodes(self, user_id: str) -> List[SSHNode]:
        return await self._repository.list_nodes(user_id)

    async def create_node(self, user_id: str, payload: Dict[str, Any]) -> SSHNode:
        count = await self._repository.count_nodes(user_id)
        if count >= self.MAX_NODES_PER_USER:
            raise BadRequestError("You can add at most 8 server nodes")

        node = SSHNode(
            user_id=user_id,
            **payload,
            updated_at=datetime.now(UTC),
        )
        await self._repository.save_node(node)
        return node

    async def update_node(self, user_id: str, node_id: str, payload: Dict[str, Any]) -> SSHNode:
        node = await self._repository.get_node(node_id, user_id)
        if not node:
            raise NotFoundError("Node not found")

        updated = node.model_copy(update={**payload, "updated_at": datetime.now(UTC)})
        await self._repository.save_node(updated)
        return updated

    async def delete_node(self, user_id: str, node_id: str) -> None:
        await self._repository.delete_node(node_id, user_id)

    async def get_node(self, user_id: str, node_id: str) -> SSHNode:
        node = await self._repository.get_node(node_id, user_id)
        if not node:
            raise NotFoundError("Node not found")
        return node

    async def run_command(
        self,
        user_id: str,
        node_id: str,
        command: str,
        exec_dir: Optional[str] = None,
        actor_type: str = "user",
        actor_id: Optional[str] = None,
        source: str = "manual",
        session_id: Optional[str] = None,
    ) -> ToolResult[dict]:
        node = await self.get_node(user_id, node_id)
        if not node.ssh_enabled:
            raise BadRequestError("SSH is not enabled for this node")

        final_command = command.strip()
        if exec_dir:
            final_command = f"cd {exec_dir} && {final_command}"

        success, output = await self._exec_ssh(node, final_command)

        await self._repository.add_log(
            SSHOperationLog(
                session_id=session_id,
                node_id=node.id,
                actor_type=actor_type,
                actor_id=actor_id,
                source=source,
                command=final_command,
                output=output,
                success=success,
            )
        )

        return ToolResult(
            success=success,
            message="success" if success else "command failed",
            data={
                "command": final_command,
                "output": output,
                "node_id": node.id,
                "node_name": node.name,
                "success": success,
            },
        )

    async def get_monitor_info(self, user_id: str, node_id: str) -> str:
        monitor_cmd = "uname -a && echo '---' && uptime && echo '---' && free -h && echo '---' && df -h"
        result = await self.run_command(
            user_id=user_id,
            node_id=node_id,
            command=monitor_cmd,
            actor_type="system",
            source="monitor",
        )
        return (result.data or {}).get("output", "")

    async def list_logs(self, user_id: str, node_id: str, limit: int = 100) -> List[SSHOperationLog]:
        await self.get_node(user_id, node_id)
        return await self._repository.list_logs(node_id, limit=min(limit, 300))

    async def create_approval(
        self,
        user_id: str,
        session_id: str,
        node_id: str,
        command: str,
        tool_call_id: Optional[str] = None,
    ) -> SSHCommandApproval:
        node = await self.get_node(user_id, node_id)
        approval = SSHCommandApproval(
            session_id=session_id,
            node_id=node.id,
            command=command,
            requested_by_tool_call_id=tool_call_id,
        )
        await self._repository.create_approval(approval)
        return approval

    async def list_pending_approvals(self, session_id: str) -> List[SSHCommandApproval]:
        return await self._repository.list_pending_approvals(session_id)

    async def execute_ai_command(
        self,
        user_id: str,
        session_id: str,
        node_id: str,
        command: str,
        tool_call_id: Optional[str] = None,
    ) -> ToolResult[dict]:
        node = await self.get_node(user_id, node_id)
        if node.ssh_require_approval:
            approval = await self.create_approval(user_id, session_id, node_id, command, tool_call_id)
            return ToolResult(
                success=False,
                message="approval_required",
                data={
                    "approval_required": True,
                    "approval_id": approval.id,
                    "node_id": node.id,
                    "node_name": node.name,
                    "command": command,
                },
            )

        return await self.run_command(
            user_id=user_id,
            node_id=node_id,
            command=command,
            actor_type="assistant",
            actor_id="manus",
            source="ai",
            session_id=session_id,
        )

    async def decide_approval(
        self,
        user_id: str,
        approval_id: str,
        approve: bool,
        reject_reason: Optional[str] = None,
    ) -> ToolResult[dict]:
        approval = await self._repository.get_approval(approval_id)
        if not approval:
            raise NotFoundError("Approval record not found")

        node = await self.get_node(user_id, approval.node_id)

        if approval.status != SSHApprovalStatus.PENDING:
            return ToolResult(
                success=False,
                message=f"already_{approval.status.value}",
                data={"approval_id": approval_id, "status": approval.status.value},
            )

        if not approve:
            await self._repository.update_approval(
                approval_id,
                SSHApprovalStatus.REJECTED,
                reject_reason=reject_reason,
            )
            await self._session_repository.add_event(
                approval.session_id,
                MessageEvent(
                    role="user",
                    message=(
                        f"SSH command approval rejected for node [{node.name}]. "
                        f"Command: {approval.command}. "
                        f"Reason: {reject_reason or 'No reason provided'}"
                    ),
                ),
            )
            return ToolResult(
                success=True,
                message="rejected",
                data={"approval_id": approval_id, "status": SSHApprovalStatus.REJECTED.value},
            )

        await self._repository.update_approval(approval_id, SSHApprovalStatus.APPROVED)
        run_result = await self.run_command(
            user_id=user_id,
            node_id=approval.node_id,
            command=approval.command,
            actor_type="assistant",
            actor_id="manus",
            source="approval",
            session_id=approval.session_id,
        )

        await self._session_repository.add_event(
            approval.session_id,
            MessageEvent(
                role="user",
                message=(
                    f"SSH command approved and executed on node [{node.name}]. "
                    f"Command: {approval.command}. "
                    f"Output:\n{(run_result.data or {}).get('output', '')[:4000]}"
                ),
            ),
        )

        return ToolResult(
            success=run_result.success,
            message="approved",
            data={
                "approval_id": approval_id,
                "status": SSHApprovalStatus.APPROVED.value,
                "output": (run_result.data or {}).get("output", ""),
            },
        )

    async def append_takeover_message(self, session_id: str, node_id: str, command: str, output: str) -> None:
        node = await self._repository.get_node(node_id)
        node_name = node.name if node else node_id
        await self._session_repository.add_event(
            session_id,
            MessageEvent(
                role="user",
                message=(
                    f"User takeover executed command on node [{node_name}]. "
                    f"Command: {command}. "
                    f"Output:\n{output[:4000]}"
                ),
            ),
        )

    async def _exec_ssh(self, node: SSHNode, command: str) -> tuple[bool, str]:
        def _blocking_exec() -> tuple[bool, str]:
            try:
                import paramiko
            except Exception as exc:  # pragma: no cover
                return False, f"Paramiko is not installed: {exc}"

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                connect_kwargs = {
                    "hostname": node.ssh_host,
                    "port": node.ssh_port,
                    "username": node.ssh_username,
                    "timeout": 15,
                    "look_for_keys": False,
                    "allow_agent": False,
                }
                if node.ssh_auth_type.value == "password":
                    connect_kwargs["password"] = node.ssh_password
                else:
                    if not node.ssh_private_key:
                        return False, "Private key is empty"
                    key_file = io.StringIO(node.ssh_private_key)
                    pkey = None
                    for key_cls in (
                        paramiko.RSAKey,
                        paramiko.Ed25519Key,
                        paramiko.ECDSAKey,
                        paramiko.DSSKey,
                    ):
                        key_file.seek(0)
                        try:
                            pkey = key_cls.from_private_key(key_file, password=node.ssh_passphrase)
                            break
                        except Exception:
                            continue
                    if not pkey:
                        return False, "Unsupported private key format"
                    connect_kwargs["pkey"] = pkey

                client.connect(**connect_kwargs)
                stdin, stdout, stderr = client.exec_command(command, timeout=180)
                exit_code = stdout.channel.recv_exit_status()
                out_text = stdout.read().decode("utf-8", errors="replace")
                err_text = stderr.read().decode("utf-8", errors="replace")
                output = (out_text + ("\n" if out_text and err_text else "") + err_text).strip()
                if not output:
                    output = "(empty output)"
                return exit_code == 0, output
            except Exception as exc:
                return False, str(exc)
            finally:
                client.close()

        return await asyncio.to_thread(_blocking_exec)
