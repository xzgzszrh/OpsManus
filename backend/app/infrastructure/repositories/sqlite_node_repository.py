from datetime import UTC, datetime
from typing import List, Optional

from app.domain.models.node import SSHCommandApproval, SSHNode, SSHOperationLog, SSHApprovalStatus
from app.infrastructure.storage.sqlite import get_sqlite


class SQLiteNodeRepository:
    async def save_node(self, node: SSHNode) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                INSERT INTO server_nodes (
                    node_id, user_id, name, description, remarks,
                    ssh_enabled, ssh_host, ssh_port, ssh_username,
                    ssh_auth_type, ssh_password, ssh_private_key, ssh_passphrase,
                    ssh_require_approval, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    user_id=excluded.user_id,
                    name=excluded.name,
                    description=excluded.description,
                    remarks=excluded.remarks,
                    ssh_enabled=excluded.ssh_enabled,
                    ssh_host=excluded.ssh_host,
                    ssh_port=excluded.ssh_port,
                    ssh_username=excluded.ssh_username,
                    ssh_auth_type=excluded.ssh_auth_type,
                    ssh_password=excluded.ssh_password,
                    ssh_private_key=excluded.ssh_private_key,
                    ssh_passphrase=excluded.ssh_passphrase,
                    ssh_require_approval=excluded.ssh_require_approval,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    node.id,
                    node.user_id,
                    node.name,
                    node.description,
                    node.remarks,
                    int(node.ssh_enabled),
                    node.ssh_host,
                    node.ssh_port,
                    node.ssh_username,
                    node.ssh_auth_type.value,
                    node.ssh_password,
                    node.ssh_private_key,
                    node.ssh_passphrase,
                    int(node.ssh_require_approval),
                    node.created_at.isoformat(),
                    node.updated_at.isoformat(),
                ),
            )
            await conn.commit()

    def _row_to_node(self, row) -> SSHNode:
        return SSHNode.model_validate(
            {
                "id": row["node_id"],
                "user_id": row["user_id"],
                "name": row["name"],
                "description": row["description"],
                "remarks": row["remarks"],
                "ssh_enabled": bool(row["ssh_enabled"]),
                "ssh_host": row["ssh_host"],
                "ssh_port": row["ssh_port"],
                "ssh_username": row["ssh_username"],
                "ssh_auth_type": row["ssh_auth_type"],
                "ssh_password": row["ssh_password"],
                "ssh_private_key": row["ssh_private_key"],
                "ssh_passphrase": row["ssh_passphrase"],
                "ssh_require_approval": bool(row["ssh_require_approval"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    async def list_nodes(self, user_id: str) -> List[SSHNode]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM server_nodes WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_node(row) for row in rows]

    async def count_nodes(self, user_id: str) -> int:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(1) AS c FROM server_nodes WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            return int(row["c"] if row else 0)

    async def get_node(self, node_id: str, user_id: Optional[str] = None) -> Optional[SSHNode]:
        async with await get_sqlite().connect() as conn:
            if user_id:
                cursor = await conn.execute(
                    "SELECT * FROM server_nodes WHERE node_id = ? AND user_id = ?",
                    (node_id, user_id),
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM server_nodes WHERE node_id = ?",
                    (node_id,),
                )
            row = await cursor.fetchone()
            return self._row_to_node(row) if row else None

    async def delete_node(self, node_id: str, user_id: str) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                "DELETE FROM server_nodes WHERE node_id = ? AND user_id = ?",
                (node_id, user_id),
            )
            await conn.commit()

    async def add_log(self, log: SSHOperationLog) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                INSERT INTO ssh_operation_logs (
                    log_id, session_id, node_id, actor_type, actor_id, source, command,
                    output, success, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.id,
                    log.session_id,
                    log.node_id,
                    log.actor_type,
                    log.actor_id,
                    log.source,
                    log.command,
                    log.output,
                    int(log.success),
                    log.created_at.isoformat(),
                ),
            )
            await conn.commit()

    async def list_logs(self, node_id: str, limit: int = 100) -> List[SSHOperationLog]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM ssh_operation_logs
                WHERE node_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (node_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                SSHOperationLog.model_validate(
                    {
                        "id": row["log_id"],
                        "session_id": row["session_id"],
                        "node_id": row["node_id"],
                        "actor_type": row["actor_type"],
                        "actor_id": row["actor_id"],
                        "source": row["source"],
                        "command": row["command"],
                        "output": row["output"] or "",
                        "success": bool(row["success"]),
                        "created_at": row["created_at"],
                    }
                )
                for row in rows
            ]

    async def create_approval(self, approval: SSHCommandApproval) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                INSERT INTO ssh_command_approvals (
                    approval_id, session_id, node_id, command, status, reject_reason,
                    requested_by_tool_call_id, created_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.id,
                    approval.session_id,
                    approval.node_id,
                    approval.command,
                    approval.status.value,
                    approval.reject_reason,
                    approval.requested_by_tool_call_id,
                    approval.created_at.isoformat(),
                    approval.decided_at.isoformat() if approval.decided_at else None,
                ),
            )
            await conn.commit()

    async def get_approval(self, approval_id: str) -> Optional[SSHCommandApproval]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM ssh_command_approvals WHERE approval_id = ?",
                (approval_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return SSHCommandApproval.model_validate(
                {
                    "id": row["approval_id"],
                    "session_id": row["session_id"],
                    "node_id": row["node_id"],
                    "command": row["command"],
                    "status": row["status"],
                    "reject_reason": row["reject_reason"],
                    "requested_by_tool_call_id": row["requested_by_tool_call_id"],
                    "created_at": row["created_at"],
                    "decided_at": row["decided_at"],
                }
            )

    async def update_approval(
        self,
        approval_id: str,
        status: SSHApprovalStatus,
        reject_reason: Optional[str] = None,
    ) -> None:
        async with await get_sqlite().connect() as conn:
            await conn.execute(
                """
                UPDATE ssh_command_approvals
                SET status = ?, reject_reason = ?, decided_at = ?
                WHERE approval_id = ?
                """,
                (
                    status.value,
                    reject_reason,
                    datetime.now(UTC).isoformat(),
                    approval_id,
                ),
            )
            await conn.commit()

    async def list_pending_approvals(self, session_id: str) -> List[SSHCommandApproval]:
        async with await get_sqlite().connect() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM ssh_command_approvals
                WHERE session_id = ? AND status = ?
                ORDER BY created_at DESC
                """,
                (session_id, SSHApprovalStatus.PENDING.value),
            )
            rows = await cursor.fetchall()
            return [
                SSHCommandApproval.model_validate(
                    {
                        "id": row["approval_id"],
                        "session_id": row["session_id"],
                        "node_id": row["node_id"],
                        "command": row["command"],
                        "status": row["status"],
                        "reject_reason": row["reject_reason"],
                        "requested_by_tool_call_id": row["requested_by_tool_call_id"],
                        "created_at": row["created_at"],
                        "decided_at": row["decided_at"],
                    }
                )
                for row in rows
            ]
