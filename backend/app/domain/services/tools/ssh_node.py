from typing import Optional

from app.application.services.node_service import NodeService
from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseTool, tool


class SSHNodeTool(BaseTool):
    name: str = "ssh"

    def __init__(self, node_service: NodeService, user_id: str, session_id: str):
        super().__init__()
        self._node_service = node_service
        self._user_id = user_id
        self._session_id = session_id

    @tool(
        name="ssh_node_list",
        description="List configured server nodes available for remote SSH operations.",
        parameters={},
        required=[],
    )
    async def ssh_node_list(self) -> ToolResult:
        nodes = await self._node_service.list_nodes(self._user_id)
        return ToolResult(
            success=True,
            data={
                "nodes": [
                    {
                        "node_id": node.id,
                        "name": node.name,
                        "description": node.description,
                        "remarks": node.remarks,
                        "ssh_enabled": node.ssh_enabled,
                        "ssh_require_approval": node.ssh_require_approval,
                    }
                    for node in nodes
                ]
            },
        )

    @tool(
        name="ssh_node_exec",
        description=(
            "Execute one command on a remote server node over SSH. "
            "Use this only for remote node operations, not for local sandbox commands."
        ),
        parameters={
            "node_id": {"type": "string", "description": "Target server node id"},
            "command": {"type": "string", "description": "SSH command to execute"},
        },
        required=["node_id", "command"],
    )
    async def ssh_node_exec(self, node_id: str, command: str) -> ToolResult:
        return await self._node_service.execute_ai_command(
            user_id=self._user_id,
            session_id=self._session_id,
            node_id=node_id,
            command=command,
        )

    @tool(
        name="ssh_node_monitor",
        description="Read remote node runtime information: uname, uptime, memory and disk.",
        parameters={
            "node_id": {"type": "string", "description": "Target server node id"},
        },
        required=["node_id"],
    )
    async def ssh_node_monitor(self, node_id: str) -> ToolResult:
        info = await self._node_service.get_monitor_info(self._user_id, node_id)
        return ToolResult(success=True, data={"node_id": node_id, "monitor": info})
