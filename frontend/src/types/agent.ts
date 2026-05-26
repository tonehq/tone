export type AgentType = 'inbound' | 'outbound' | 'both';

export type AgentStatus = 'active' | 'inactive' | 'draft';

/** Hardcoded variant used by /agents/create/[type] routes. The list response
 * can also surface 'both' via the API; routes for editing handle it via the
 * type segment in the URL. */
export type AgentDirection = 'inbound' | 'outbound' | 'both';

// ─── domain primitives (mirror the new backend payload) ────────────────────

export interface AgentLlmSettings {
  temperature?: number;
  max_tokens?: number;
  [key: string]: unknown;
}

export interface AgentVoiceSettings {
  provider_id?: string | null;
  voice_id?: string | null;
  language?: string | null;
  speed?: number | null;
  [key: string]: unknown;
}

export interface AgentSttSettings {
  model?: string | null;
  [key: string]: unknown;
}

export interface AgentConversationSettings {
  max_duration_seconds?: number | null;
  [key: string]: unknown;
}

export interface AgentConfig {
  first_message?: string | null;
  /** Optional closing line the agent reads before hanging up. Stored on
   * config; backend's AgentConfig accepts extra keys. */
  end_call_message?: string | null;
  system_prompt_template?: string | null;
  conversation_history_token_limit?: number | null;
  language_id?: string | null;
  knowledge_model_id?: string | null;
  llm_settings?: AgentLlmSettings | null;
  voice_settings?: AgentVoiceSettings | null;
  stt_settings?: AgentSttSettings | null;
  conversation_settings?: AgentConversationSettings | null;
}

export interface AgentConfigResponse extends AgentConfig {
  id: string;
  version: number;
}

export interface AgentPhoneNumberInput {
  number: string;
  channel_id: string;
  label?: string | null;
}

// ─── API payloads ──────────────────────────────────────────────────────────

export interface CreateAgentPayload {
  name: string;
  agent_type: AgentDirection;
  description?: string | null;
  is_active?: boolean;
  config?: AgentConfig;
  tool_ids?: string[];
  mcp_server_ids?: string[];
  upload_ids?: string[];
  phone_numbers?: AgentPhoneNumberInput[];
}

/** Partial — only present fields are touched. Arrays present (even []) =
 * full replacement. Arrays omitted = left untouched. */
export type UpdateAgentPayload = Partial<CreateAgentPayload>;

// ─── API responses ─────────────────────────────────────────────────────────

export interface AgentToolRef {
  id: string;
  name: string;
}

export interface AgentMcpServerRef {
  id: string;
  name: string;
}

export interface AgentDocumentRef {
  id: string;
  file_path?: string | null;
  file_name?: string | null;
}

export interface AgentPhoneNumberRef {
  id: string;
  number: string;
  label?: string | null;
  channel_id?: string | null;
}

/** Full detail (create/get/update response). */
export interface AgentDetail {
  id: string;
  name: string;
  description: string | null;
  agent_type: AgentDirection;
  llm_model?: string | null;
  is_active: boolean;
  created_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
  config: AgentConfigResponse;
  tools: AgentToolRef[];
  mcp_servers: AgentMcpServerRef[];
  documents: AgentDocumentRef[];
  phone_numbers: AgentPhoneNumberRef[];
}

/** Lightweight listing row (POST /agent/list). `phone_number` is the legacy
 * shape returned by the list endpoint — kept as-is for now. */
export interface AgentListItem {
  id: string;
  uuid: string;
  name: string;
  description: string | null;
  agent_type: AgentDirection;
  is_active: boolean;
  phone_number: { type: string; no: string }[];
  created_at: number;
  updated_at: number;
}

/** Alias retained so the listing page does not need to be renamed everywhere. */
export type ApiAgent = AgentListItem;

/** GET /agent/get_all_agents (dropdown helper). */
export interface AgentDropdownItem {
  id: string;
  uuid: string;
  name: string;
}

export interface ListAgentsParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  is_active?: boolean;
  agent_type?: AgentDirection;
}

export interface PaginatedAgents {
  items: AgentListItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── UI state ──────────────────────────────────────────────────────────────

export interface AgentsState {
  agentList: AgentDropdownItem[];
}

export interface PaginatedAgentsState {
  items: AgentListItem[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
}

/** Single source of truth for the agent create/edit form. Mirrors the
 * create/update payload — serialisers in agentFormUtils convert this into
 * a {@link CreateAgentPayload} or a diff-aware {@link UpdateAgentPayload}. */
export interface AgentFormState {
  name: string;
  description: string;
  agent_type: AgentDirection;
  is_active: boolean;
  config: {
    first_message: string;
    end_call_message: string;
    system_prompt_template: string;
    conversation_history_token_limit: number | null;
    language_id: string | null;
    knowledge_model_id: string | null;
    llm_settings: AgentLlmSettings;
    voice_settings: AgentVoiceSettings;
    stt_settings: AgentSttSettings;
    conversation_settings: AgentConversationSettings;
  };
  tool_ids: string[];
  mcp_server_ids: string[];
  upload_ids: string[];
  phone_numbers: AgentPhoneNumberInput[];
}

export interface CreateAgentModalOption {
  type: AgentType;
  title: string;
  description: string;
  icon: React.ReactNode;
}
