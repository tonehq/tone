import axiosInstance from '@/utils/axios';
import type {
  AgentDetail,
  AgentDropdownItem,
  AgentTemplateSummary,
  AgentVersionSummary,
  CreateAgentPayload,
  ListAgentsParams,
  PaginatedAgents,
  UpdateAgentPayload,
} from '@/types/agent';

export const listAgents = async (params: ListAgentsParams = {}): Promise<PaginatedAgents> => {
  const res = await axiosInstance.post<PaginatedAgents>('/agent/list', params);
  return res.data;
};

export const getAllAgents = async (): Promise<AgentDropdownItem[]> => {
  const res = await axiosInstance.get<AgentDropdownItem[]>('/agent/get_all_agents');
  return Array.isArray(res.data) ? res.data : [];
};

/** Fetch an agent. When `configId` is passed, the agent is rendered against
 * that specific version; alternatively `version` resolves that version number
 * server-side (so a deep-linked ?version=<n> loads in one request). */
export const getAgent = async (
  agentId: string,
  configId?: string,
  version?: number,
): Promise<AgentDetail> => {
  const res = await axiosInstance.get<AgentDetail>('/agent/get_agent', {
    params: {
      agent_id: agentId,
      ...(configId ? { config_id: configId } : {}),
      ...(!configId && version != null ? { version } : {}),
    },
  });
  return res.data;
};

export const createAgent = async (payload: CreateAgentPayload): Promise<AgentDetail> => {
  const res = await axiosInstance.post<AgentDetail>('/agent/create_agent', payload);
  return res.data;
};

export const updateAgent = async (
  agentId: string,
  payload: UpdateAgentPayload,
): Promise<AgentDetail> => {
  const res = await axiosInstance.put<AgentDetail>('/agent/update_agent', payload, {
    params: { agent_id: agentId },
  });
  return res.data;
};

export const deleteAgent = async (agentId: string): Promise<void> => {
  await axiosInstance.delete('/agent/delete_agent', { params: { agent_id: agentId } });
};

/** Deep-clone an entire agent into a new, independent one. The clone carries a
 *  copy of the source's live config plus its tool / MCP / knowledge-base
 *  attachments and workflow graph; phone numbers and web channels are not
 *  copied. `name` sets the new agent's name; when omitted it is auto-named
 *  "<name> (copy)" server-side. */
export const cloneAgent = async (agentId: string, name?: string): Promise<AgentDetail> => {
  const trimmed = name?.trim();
  const res = await axiosInstance.post<AgentDetail>(
    '/agent/clone_agent',
    trimmed ? { name: trimmed } : {},
    { params: { agent_id: agentId } },
  );
  return res.data;
};

/** List agent configs flagged as templates (is_template=true) for the Create
 *  Agent picker. */
export const listAgentTemplates = async (): Promise<AgentTemplateSummary[]> => {
  const res = await axiosInstance.get<AgentTemplateSummary[]>('/agent/list_templates');
  return Array.isArray(res.data) ? res.data : [];
};

/** Create a new agent by deep-copying a template config. `name` sets the new
 *  agent's name; when omitted it takes the template's name. */
export const createAgentFromTemplate = async (
  sourceConfigId: string,
  name?: string,
): Promise<AgentDetail> => {
  const trimmed = name?.trim();
  const res = await axiosInstance.post<AgentDetail>('/agent/create_from_template', {
    source_config_id: sourceConfigId,
    ...(trimmed ? { name: trimmed } : {}),
  });
  return res.data;
};

// ─── versioning ────────────────────────────────────────────────────────────

export const listAgentVersions = async (agentId: string): Promise<AgentVersionSummary[]> => {
  const res = await axiosInstance.get<AgentVersionSummary[]>('/agent/list_versions', {
    params: { agent_id: agentId },
  });
  return Array.isArray(res.data) ? res.data : [];
};

/** Body shared by both the "create new version" and "update version" endpoints —
 *  same shape minus the top-level agent attributes (name/description/
 *  agent_type/is_active). Keeping it as one type means the editor builds the
 *  payload once and routes it to whichever endpoint the user picked. */
type VersionPayload = Pick<
  UpdateAgentPayload,
  | 'config'
  | 'tool_ids'
  | 'mcp_server_ids'
  | 'upload_ids'
  | 'phone_numbers'
  | 'web_channel_ids'
  | 'tool_oauth_overrides'
  | 'mcp_server_oauth_overrides'
> & { source_config_id?: string | null };

/** Spawn a new draft version of the agent.
 *
 *  - `from_scratch: false` (default) — clone the version identified by
 *    `source_config_id` (or the live one when omitted). Fields + tool / MCP /
 *    KB attachments come from the source; any non-null fields in `payload`
 *    overlay it.
 *  - `from_scratch: true` — no source is read. The draft starts from the
 *    payload (or null fields if absent) with no attachments. Used by the
 *    "Start fresh" option in the create-version dialog.
 *
 *  Drafts are never auto-promoted. The user clicks Publish to make a draft
 *  serve calls. */
export const createAgentVersion = async (
  agentId: string,
  payload: VersionPayload & { from_scratch?: boolean },
): Promise<AgentDetail> => {
  const res = await axiosInstance.post<AgentDetail>('/agent/save_as_new_version', payload, {
    params: { agent_id: agentId },
  });
  return res.data;
};

/** In-place update of the version identified by `source_config_id` — no new
 *  row is created. When `source_config_id` is omitted, the live config is
 *  updated. Used by the Save button so editing doesn't pad version history. */
export const updateAgentVersion = async (
  agentId: string,
  payload: VersionPayload,
): Promise<AgentDetail> => {
  const res = await axiosInstance.put<AgentDetail>('/agent/update_version', payload, {
    params: { agent_id: agentId },
  });
  return res.data;
};

export const switchActiveAgentVersion = async (
  agentId: string,
  configId: string,
): Promise<AgentDetail> => {
  const res = await axiosInstance.post<AgentDetail>(
    '/agent/switch_active_version',
    { config_id: configId },
    { params: { agent_id: agentId } },
  );
  return res.data;
};

export const deleteAgentVersion = async (agentId: string, configId: string): Promise<void> => {
  await axiosInstance.delete('/agent/delete_version', {
    params: { agent_id: agentId, config_id: configId },
  });
};
