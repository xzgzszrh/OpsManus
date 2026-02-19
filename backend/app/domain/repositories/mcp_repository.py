from typing import Protocol
from app.domain.models.mcp_config import MCPConfig

class MCPRepository(Protocol):
    """Repository interface for MCP aggregate"""
    
    async def get_mcp_config(self) -> MCPConfig:
        """Get the MCP config"""
        ...

    async def save_mcp_config(self, config: MCPConfig) -> None:
        """Persist MCP config"""
        ...
