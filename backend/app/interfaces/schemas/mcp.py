from typing import Dict, Optional
from pydantic import BaseModel


class BigModelMCPApiKeys(BaseModel):
    vision_api_key: str = ""
    search_api_key: str = ""
    reader_api_key: str = ""
    zread_api_key: str = ""


class MCPServerSetting(BaseModel):
    server_id: str
    title: str
    description: str
    transport: str
    enabled: bool
    configured: bool


class MCPSettingsResponse(BaseModel):
    api_keys: BigModelMCPApiKeys
    servers: Dict[str, MCPServerSetting]


class UpdateMCPSettingsRequest(BaseModel):
    vision_api_key: Optional[str] = None
    search_api_key: Optional[str] = None
    reader_api_key: Optional[str] = None
    zread_api_key: Optional[str] = None
