import { apiClient, ApiResponse } from './client';

export type BigModelMCPServerId = 'bigmodel_vision' | 'bigmodel_search' | 'bigmodel_reader' | 'bigmodel_zread';

export interface MCPServerSetting {
  server_id: BigModelMCPServerId;
  title: string;
  description: string;
  transport: string;
  enabled: boolean;
  configured: boolean;
}

export interface BigModelMCPApiKeys {
  vision_api_key: string;
  search_api_key: string;
  reader_api_key: string;
  zread_api_key: string;
}

export interface MCPSettingsResponse {
  api_keys: BigModelMCPApiKeys;
  servers: Record<BigModelMCPServerId, MCPServerSetting>;
}

export interface UpdateMCPSettingsRequest {
  vision_api_key?: string;
  search_api_key?: string;
  reader_api_key?: string;
  zread_api_key?: string;
}

export async function getMCPSettings(): Promise<MCPSettingsResponse> {
  const response = await apiClient.get<ApiResponse<MCPSettingsResponse>>('/mcp/config');
  return response.data.data;
}

export async function updateMCPSettings(payload: UpdateMCPSettingsRequest): Promise<MCPSettingsResponse> {
  const response = await apiClient.put<ApiResponse<MCPSettingsResponse>>('/mcp/config', payload);
  return response.data.data;
}
