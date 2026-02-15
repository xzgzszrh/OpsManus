from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import io
import re
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

    async def get_node_overview(self, user_id: str, node_id: str) -> Dict[str, Any]:
        node = await self.get_node(user_id, node_id)
        command = (
            "printf 'HOSTNAME=%s\\n' \"$(hostname)\"; "
            "printf 'OS_NAME=%s\\n' \"$(. /etc/os-release 2>/dev/null; echo ${PRETTY_NAME:-unknown})\"; "
            "printf 'KERNEL=%s\\n' \"$(uname -r)\"; "
            "printf 'UPTIME=%s\\n' \"$(uptime -p 2>/dev/null || uptime)\"; "
            "printf 'LOAD_AVG=%s\\n' \"$(cat /proc/loadavg 2>/dev/null | awk '{print $1\" \"$2\" \"$3}')\"; "
            "printf 'MEM_TOTAL_KB=%s\\n' \"$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}')\"; "
            "printf 'MEM_AVAILABLE_KB=%s\\n' \"$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}')\"; "
            "printf 'ROOT_DISK=%s\\n' \"$(df -Pk / 2>/dev/null | tail -1 | awk '{print $2\" \"$3\" \"$5}')\""
        )
        result = await self.run_command(
            user_id=user_id,
            node_id=node_id,
            command=command,
            actor_type="system",
            source="monitor",
        )
        raw_output = (result.data or {}).get("output", "")
        parsed = self._parse_overview_output(raw_output)
        metrics = self._build_overview_metrics(parsed)
        status = "healthy"
        if any(metric["level"] == "critical" for metric in metrics):
            status = "critical"
        elif any(metric["level"] == "warn" for metric in metrics):
            status = "warning"

        summary_map = {
            "healthy": "系统运行状态良好，关键指标处于安全区间。",
            "warning": "系统存在需要关注的资源压力，建议继续观察或优化。",
            "critical": "系统资源压力较高，建议尽快排查并处理。",
        }

        return {
            "node_id": node.id,
            "node_name": node.name,
            "checked_at": datetime.now(UTC),
            "status": status,
            "summary": summary_map[status],
            "hostname": parsed.get("HOSTNAME"),
            "os_name": parsed.get("OS_NAME"),
            "kernel": parsed.get("KERNEL"),
            "uptime": parsed.get("UPTIME"),
            "load_average": parsed.get("LOAD_AVG"),
            "memory_total": self._format_kb_to_human(parsed.get("MEM_TOTAL_KB")),
            "memory_used": self._format_kb_to_human(self._memory_used_kb(parsed)),
            "memory_free": self._format_kb_to_human(parsed.get("MEM_AVAILABLE_KB")),
            "disk_total": self._format_kb_to_human(self._disk_total_kb(parsed)),
            "disk_used": self._format_kb_to_human(self._disk_used_kb(parsed)),
            "disk_use_percent": self._disk_percent(parsed),
            "metrics": metrics,
            "raw_output": raw_output,
        }

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

    @staticmethod
    def _parse_overview_output(raw_output: str) -> Dict[str, str]:
        parsed: Dict[str, str] = {}
        for line in raw_output.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key:
                parsed[key] = value
        return parsed

    @staticmethod
    def _to_int(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        match = re.search(r"\d+", value)
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None

    def _disk_total_kb(self, parsed: Dict[str, str]) -> Optional[int]:
        root_disk = parsed.get("ROOT_DISK", "")
        parts = root_disk.split()
        if len(parts) < 2:
            return None
        return self._to_int(parts[0])

    def _disk_used_kb(self, parsed: Dict[str, str]) -> Optional[int]:
        root_disk = parsed.get("ROOT_DISK", "")
        parts = root_disk.split()
        if len(parts) < 2:
            return None
        return self._to_int(parts[1])

    def _disk_percent(self, parsed: Dict[str, str]) -> Optional[int]:
        root_disk = parsed.get("ROOT_DISK", "")
        parts = root_disk.split()
        if len(parts) < 3:
            return None
        return self._to_int(parts[2])

    def _memory_used_kb(self, parsed: Dict[str, str]) -> Optional[int]:
        total = self._to_int(parsed.get("MEM_TOTAL_KB"))
        available = self._to_int(parsed.get("MEM_AVAILABLE_KB"))
        if total is None or available is None:
            return None
        used = total - available
        return used if used >= 0 else None

    @staticmethod
    def _format_kb_to_human(value: Optional[int]) -> Optional[str]:
        if value is None:
            return None
        size = float(value) * 1024.0
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        if unit_index == 0:
            return f"{int(size)}{units[unit_index]}"
        return f"{size:.1f}{units[unit_index]}"

    def _build_overview_metrics(self, parsed: Dict[str, str]) -> List[Dict[str, str]]:
        metrics: List[Dict[str, str]] = []

        load_avg = parsed.get("LOAD_AVG") or "-"
        load_level = "ok"
        try:
            first_load = float(load_avg.split()[0])
            if first_load >= 4:
                load_level = "critical"
            elif first_load >= 2:
                load_level = "warn"
        except Exception:
            load_level = "warn"
        metrics.append({
            "label": "CPU 负载",
            "value": load_avg,
            "hint": "1m / 5m / 15m",
            "level": load_level,
        })

        total_mem = self._to_int(parsed.get("MEM_TOTAL_KB"))
        used_mem = self._memory_used_kb(parsed)
        mem_percent = None
        if total_mem and used_mem is not None and total_mem > 0:
            mem_percent = int((used_mem / total_mem) * 100)
        mem_level = "ok"
        if mem_percent is not None:
            if mem_percent >= 90:
                mem_level = "critical"
            elif mem_percent >= 75:
                mem_level = "warn"
        metrics.append({
            "label": "内存使用",
            "value": f"{mem_percent}%" if mem_percent is not None else "-",
            "hint": f"{self._format_kb_to_human(used_mem) or '-'} / {self._format_kb_to_human(total_mem) or '-'}",
            "level": mem_level,
        })

        disk_percent = self._disk_percent(parsed)
        disk_level = "ok"
        if disk_percent is not None:
            if disk_percent >= 90:
                disk_level = "critical"
            elif disk_percent >= 75:
                disk_level = "warn"
        metrics.append({
            "label": "磁盘使用(/)",
            "value": f"{disk_percent}%" if disk_percent is not None else "-",
            "hint": f"{self._format_kb_to_human(self._disk_used_kb(parsed)) or '-'} / {self._format_kb_to_human(self._disk_total_kb(parsed)) or '-'}",
            "level": disk_level,
        })

        metrics.append({
            "label": "在线时长",
            "value": parsed.get("UPTIME", "-"),
            "hint": "从系统最近一次启动到当前",
            "level": "ok",
        })
        return metrics
