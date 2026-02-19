from typing import Dict

from fastapi import APIRouter, Depends

from app.application.errors.exceptions import ServerError
from app.domain.models.mcp_config import MCPConfig, MCPServerConfig, MCPTransport
from app.domain.models.user import User
from app.domain.repositories.mcp_repository import MCPRepository
from app.interfaces.dependencies import get_current_user, get_mcp_repository
from app.interfaces.schemas.base import APIResponse
from app.interfaces.schemas.mcp import (
    BigModelMCPApiKeys,
    MCPServerSetting,
    MCPSettingsResponse,
    UpdateMCPSettingsRequest,
)


router = APIRouter(prefix="/mcp", tags=["mcp"])

BIGMODEL_VISION_SERVER = "bigmodel_vision"
BIGMODEL_SEARCH_SERVER = "bigmodel_search"
BIGMODEL_READER_SERVER = "bigmodel_reader"
BIGMODEL_ZREAD_SERVER = "bigmodel_zread"

BUILTIN_SERVER_META = {
    BIGMODEL_VISION_SERVER: {
        "title": "BigModel Vision",
        "description": "Send images and requirements, return concrete visual understanding content (suitable for batch image analysis or weak multimodal models)",
        "transport": MCPTransport.STDIO,
    },
    BIGMODEL_SEARCH_SERVER: {
        "title": "BigModel Search",
        "description": "Web search MCP that returns searchable links and snippets",
        "transport": MCPTransport.STREAMABLE_HTTP,
    },
    BIGMODEL_READER_SERVER: {
        "title": "BigModel Reader",
        "description": "Send URL for page interpretation and text extraction",
        "transport": MCPTransport.STREAMABLE_HTTP,
    },
    BIGMODEL_ZREAD_SERVER: {
        "title": "BigModel ZRead",
        "description": "Analyze GitHub repositories, code files, and repository structures",
        "transport": MCPTransport.STREAMABLE_HTTP,
    },
}


def _extract_bearer_key(server: MCPServerConfig) -> str:
    headers = server.headers or {}
    auth = headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _extract_vision_key(server: MCPServerConfig) -> str:
    env = server.env or {}
    return env.get("Z_AI_API_KEY", "").strip()


def _build_builtin_servers(keys: BigModelMCPApiKeys) -> Dict[str, MCPServerConfig]:
    return {
        BIGMODEL_VISION_SERVER: MCPServerConfig(
            command="npx",
            args=["-y", "@z_ai/mcp-server"],
            transport=MCPTransport.STDIO,
            enabled=False,
            description=BUILTIN_SERVER_META[BIGMODEL_VISION_SERVER]["description"],
            env={
                "Z_AI_API_KEY": keys.vision_api_key,
                "Z_AI_MODE": "ZHIPU",
            },
        ),
        BIGMODEL_SEARCH_SERVER: MCPServerConfig(
            url="https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
            transport=MCPTransport.STREAMABLE_HTTP,
            enabled=bool(keys.search_api_key),
            description=BUILTIN_SERVER_META[BIGMODEL_SEARCH_SERVER]["description"],
            headers={"Authorization": f"Bearer {keys.search_api_key}"} if keys.search_api_key else {},
        ),
        BIGMODEL_READER_SERVER: MCPServerConfig(
            url="https://open.bigmodel.cn/api/mcp/web_reader/mcp",
            transport=MCPTransport.STREAMABLE_HTTP,
            enabled=bool(keys.reader_api_key),
            description=BUILTIN_SERVER_META[BIGMODEL_READER_SERVER]["description"],
            headers={"Authorization": f"Bearer {keys.reader_api_key}"} if keys.reader_api_key else {},
        ),
        BIGMODEL_ZREAD_SERVER: MCPServerConfig(
            url="https://open.bigmodel.cn/api/mcp/zread/mcp",
            transport=MCPTransport.STREAMABLE_HTTP,
            enabled=bool(keys.zread_api_key),
            description=BUILTIN_SERVER_META[BIGMODEL_ZREAD_SERVER]["description"],
            headers={"Authorization": f"Bearer {keys.zread_api_key}"} if keys.zread_api_key else {},
        ),
    }


def _extract_current_keys(config: MCPConfig) -> BigModelMCPApiKeys:
    servers = config.mcpServers or {}
    return BigModelMCPApiKeys(
        vision_api_key=_extract_vision_key(servers[BIGMODEL_VISION_SERVER]) if BIGMODEL_VISION_SERVER in servers else "",
        search_api_key=_extract_bearer_key(servers[BIGMODEL_SEARCH_SERVER]) if BIGMODEL_SEARCH_SERVER in servers else "",
        reader_api_key=_extract_bearer_key(servers[BIGMODEL_READER_SERVER]) if BIGMODEL_READER_SERVER in servers else "",
        zread_api_key=_extract_bearer_key(servers[BIGMODEL_ZREAD_SERVER]) if BIGMODEL_ZREAD_SERVER in servers else "",
    )


def _to_settings_response(keys: BigModelMCPApiKeys) -> MCPSettingsResponse:
    servers = _build_builtin_servers(keys)
    server_settings = {
        server_id: MCPServerSetting(
            server_id=server_id,
            title=meta["title"],
            description=meta["description"],
            transport=meta["transport"].value,
            enabled=servers[server_id].enabled,
            configured=bool(getattr(keys, f"{server_id.split('_')[-1]}_api_key", "")),
        )
        for server_id, meta in BUILTIN_SERVER_META.items()
    }
    return MCPSettingsResponse(api_keys=keys, servers=server_settings)


@router.get("/config", response_model=APIResponse[MCPSettingsResponse])
async def get_mcp_config(
    _current_user: User = Depends(get_current_user),
    mcp_repository: MCPRepository = Depends(get_mcp_repository),
) -> APIResponse[MCPSettingsResponse]:
    config = await mcp_repository.get_mcp_config()
    keys = _extract_current_keys(config)
    return APIResponse.success(_to_settings_response(keys))


@router.put("/config", response_model=APIResponse[MCPSettingsResponse])
async def update_mcp_config(
    request: UpdateMCPSettingsRequest,
    _current_user: User = Depends(get_current_user),
    mcp_repository: MCPRepository = Depends(get_mcp_repository),
) -> APIResponse[MCPSettingsResponse]:
    config = await mcp_repository.get_mcp_config()
    current_keys = _extract_current_keys(config)

    next_keys = BigModelMCPApiKeys(
        vision_api_key=(request.vision_api_key if request.vision_api_key is not None else current_keys.vision_api_key).strip(),
        search_api_key=(request.search_api_key if request.search_api_key is not None else current_keys.search_api_key).strip(),
        reader_api_key=(request.reader_api_key if request.reader_api_key is not None else current_keys.reader_api_key).strip(),
        zread_api_key=(request.zread_api_key if request.zread_api_key is not None else current_keys.zread_api_key).strip(),
    )

    merged_servers = dict(config.mcpServers)
    merged_servers.update(_build_builtin_servers(next_keys))

    try:
        await mcp_repository.save_mcp_config(MCPConfig(mcpServers=merged_servers))
    except Exception as e:
        raise ServerError(f"Failed to save MCP config: {str(e)}")

    return APIResponse.success(_to_settings_response(next_keys))
