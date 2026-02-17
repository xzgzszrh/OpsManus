import { apiClient, ApiResponse } from './client';

export type TicketStatus = 'open' | 'processing' | 'waiting_user' | 'resolved';
export type TicketCommentRole = 'user' | 'ai' | 'system';
export type TicketPriority = 'p0' | 'p1' | 'p2' | 'p3';
export type TicketUrgency = 'low' | 'medium' | 'high' | 'critical';

export interface TicketComment {
  comment_id: string;
  role: TicketCommentRole;
  message: string;
  created_at: string;
}

export interface TicketEvent {
  event_id: string;
  event_type: string;
  message: string;
  created_at: string;
}

export interface TicketItem {
  ticket_id: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  urgency: TicketUrgency;
  tags: string[];
  node_ids: string[];
  plugin_ids: string[];
  session_id: string;
  comments: TicketComment[];
  events: TicketEvent[];
  estimated_minutes?: number;
  spent_minutes: number;
  sla_due_at?: string;
  first_response_at?: string;
  resolved_at?: string;
  reopen_count: number;
  created_at: string;
  updated_at: string;
}

interface ListTicketsResponse {
  tickets: TicketItem[];
}

export interface CreateTicketRequest {
  title: string;
  description: string;
  node_ids: string[];
  plugin_ids: string[];
  tags: string[];
  priority: TicketPriority;
  urgency: TicketUrgency;
  estimated_minutes?: number;
  sla_hours?: number;
}

export interface UpdateTicketRequest {
  status?: TicketStatus;
  priority?: TicketPriority;
  urgency?: TicketUrgency;
  tags?: string[];
  estimated_minutes?: number;
  spent_minutes?: number;
  sla_due_at?: string;
}

export async function listTickets(): Promise<TicketItem[]> {
  const response = await apiClient.get<ApiResponse<ListTicketsResponse>>('/tickets');
  return response.data.data.tickets;
}

export async function createTicket(payload: CreateTicketRequest): Promise<TicketItem> {
  const response = await apiClient.post<ApiResponse<TicketItem>>('/tickets', payload);
  return response.data.data;
}

export async function getTicket(ticketId: string): Promise<TicketItem> {
  const response = await apiClient.get<ApiResponse<TicketItem>>(`/tickets/${ticketId}`);
  return response.data.data;
}

export async function replyTicket(ticketId: string, message: string): Promise<TicketItem> {
  const response = await apiClient.post<ApiResponse<TicketItem>>(`/tickets/${ticketId}/reply`, {
    message,
  });
  return response.data.data;
}

export async function updateTicket(ticketId: string, payload: UpdateTicketRequest): Promise<TicketItem> {
  const response = await apiClient.put<ApiResponse<TicketItem>>(`/tickets/${ticketId}`, payload);
  return response.data.data;
}
