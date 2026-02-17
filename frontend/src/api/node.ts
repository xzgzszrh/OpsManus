import { apiClient, ApiResponse } from './client';

export interface ServerNode {
  node_id: string;
  name: string;
  description?: string;
  remarks?: string;
  ssh_enabled: boolean;
  ssh_host?: string;
  ssh_port: number;
  ssh_username?: string;
  ssh_auth_type: 'password' | 'private_key';
  ssh_password?: string;
  ssh_private_key?: string;
  ssh_passphrase?: string;
  ssh_require_approval: boolean;
  created_at: string;
  updated_at: string;
}

export interface ListServerNodesResponse {
  nodes: ServerNode[];
}

export interface SSHExecResponse {
  success: boolean;
  output: string;
  command: string;
  node_id: string;
  node_name: string;
}

export interface SSHMonitorResponse {
  node_id: string;
  node_name: string;
  system_info: string;
}

export interface NodeOverviewMetric {
  label: string;
  value: string;
  hint?: string;
  level: 'ok' | 'warn' | 'critical';
}

export interface NodeOverviewResponse {
  node_id: string;
  node_name: string;
  checked_at: string;
  status: 'healthy' | 'warning' | 'critical';
  summary: string;
  hostname?: string;
  os_name?: string;
  kernel?: string;
  uptime?: string;
  load_average?: string;
  memory_total?: string;
  memory_used?: string;
  memory_free?: string;
  disk_total?: string;
  disk_used?: string;
  disk_use_percent?: number;
  metrics: NodeOverviewMetric[];
  raw_output: string;
}

export interface SSHLogItem {
  log_id: string;
  session_id?: string;
  actor_type: string;
  actor_id?: string;
  source: string;
  command: string;
  output: string;
  success: boolean;
  created_at: string;
}

export interface SSHLogsResponse {
  logs: SSHLogItem[];
}

export interface PendingApprovalItem {
  approval_id: string;
  session_id: string;
  node_id: string;
  command: string;
  status: 'pending' | 'approved' | 'rejected';
  reject_reason?: string;
  created_at: string;
}

export interface PendingApprovalListResponse {
  approvals: PendingApprovalItem[];
}

export interface DecideApprovalResponse {
  approval_id: string;
  status: 'pending' | 'approved' | 'rejected';
  output?: string;
}

export async function listServerNodes(): Promise<ServerNode[]> {
  const response = await apiClient.get<ApiResponse<ListServerNodesResponse>>('/nodes');
  return response.data.data.nodes;
}

export async function createServerNode(payload: Omit<ServerNode, 'node_id' | 'created_at' | 'updated_at'>): Promise<ServerNode> {
  const response = await apiClient.post<ApiResponse<ServerNode>>('/nodes', payload);
  return response.data.data;
}

export async function updateServerNode(nodeId: string, payload: Omit<ServerNode, 'node_id' | 'created_at' | 'updated_at'>): Promise<ServerNode> {
  const response = await apiClient.put<ApiResponse<ServerNode>>(`/nodes/${nodeId}`, payload);
  return response.data.data;
}

export async function deleteServerNode(nodeId: string): Promise<void> {
  await apiClient.delete<ApiResponse<void>>(`/nodes/${nodeId}`);
}

export async function execNodeSSH(nodeId: string, command: string, execDir?: string, syncToAi?: boolean, sessionId?: string): Promise<SSHExecResponse> {
  const response = await apiClient.post<ApiResponse<SSHExecResponse>>(`/nodes/${nodeId}/ssh/exec`, {
    command,
    exec_dir: execDir,
    sync_to_ai: !!syncToAi,
    session_id: sessionId,
  });
  return response.data.data;
}

export async function monitorNode(nodeId: string): Promise<SSHMonitorResponse> {
  const response = await apiClient.get<ApiResponse<SSHMonitorResponse>>(`/nodes/${nodeId}/monitor`);
  return response.data.data;
}

export async function getNodeOverview(nodeId: string): Promise<NodeOverviewResponse> {
  const response = await apiClient.get<ApiResponse<NodeOverviewResponse>>(`/nodes/${nodeId}/overview`);
  return response.data.data;
}

export async function listNodeLogs(nodeId: string, limit: number = 100, includeSystem: boolean = false): Promise<SSHLogItem[]> {
  const response = await apiClient.get<ApiResponse<SSHLogsResponse>>(`/nodes/${nodeId}/logs`, {
    params: { limit, include_system: includeSystem },
  });
  return response.data.data.logs;
}

export async function listSessionApprovals(sessionId: string): Promise<PendingApprovalItem[]> {
  const response = await apiClient.get<ApiResponse<PendingApprovalListResponse>>(`/nodes/sessions/${sessionId}/approvals`);
  return response.data.data.approvals;
}

export async function decideApproval(approvalId: string, approve: boolean, rejectReason?: string): Promise<DecideApprovalResponse> {
  const response = await apiClient.post<ApiResponse<DecideApprovalResponse>>(`/nodes/approvals/${approvalId}/decision`, {
    approve,
    reject_reason: rejectReason,
  });
  return response.data.data;
}
