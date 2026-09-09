import axiosInstance from '@/utils/axios';

import type {
  AgentProfileWebhook,
  GetProfileWebhookResponse,
  ProfileWebhookUpsertInput,
  WebhookTestRequest,
  WebhookTestResponse,
} from '@/types/agentProfileWebhook';

/**
 * HTTP layer for the per-agent webhook data source. All calls go through here
 * so components never call axios directly. Mirrors the router paths under
 * `/agents/{agent_id}/profile-webhook`.
 */

const base = (agentId: string) => `/agents/${agentId}/profile-webhook`;

export const getAgentProfileWebhook = async (
  agentId: string,
): Promise<AgentProfileWebhook | null> => {
  const res = await axiosInstance.get<GetProfileWebhookResponse>(base(agentId));
  return res.data.webhook;
};

export const upsertAgentProfileWebhook = async (
  agentId: string,
  input: ProfileWebhookUpsertInput,
): Promise<AgentProfileWebhook> => {
  const res = await axiosInstance.put<AgentProfileWebhook>(base(agentId), input);
  return res.data;
};

export const deleteAgentProfileWebhook = async (agentId: string): Promise<{ deleted: boolean }> => {
  const res = await axiosInstance.delete<{ deleted: boolean }>(base(agentId));
  return res.data;
};

export const testAgentProfileWebhook = async (
  agentId: string,
  body: WebhookTestRequest,
): Promise<WebhookTestResponse> => {
  const res = await axiosInstance.post<WebhookTestResponse>(`${base(agentId)}/test`, body);
  return res.data;
};
