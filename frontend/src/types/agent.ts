import type { ReadinessOverallStatus } from '@/types/readiness';

export type AgentType = 'inbound' | 'outbound' | 'both';

export type AgentStatus = 'active' | 'inactive' | 'draft';

/** Hardcoded variant used by /agents/create/[type] routes. The list response
 * can also surface 'both' via the API; routes for editing handle it via the
 * type segment in the URL. */
export type AgentDirection = 'inbound' | 'outbound' | 'both';

// ─── domain primitives (mirror the new backend payload) ────────────────────

export interface AgentLlmSettings {
  temperature?: number;
  max_completion_tokens?: number;
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
  /** Conversation-flow driver: a single prompt, or an assigned workflow graph. */
  mode?: 'prompt' | 'workflow' | null;
  /** When `mode === 'workflow'`, the assigned (published) workflow. */
  workflow_id?: string | null;
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

/** Lightweight summary returned by the version-history endpoint and embedded
 * in {@link AgentDetail.versions}. The `is_live` flag mirrors whether
 * `agents.published_config_id` points at this row. */
export interface AgentVersionSummary {
  id: string;
  version: number;
  is_live: boolean;
  /** True for reusable template snapshots (is_template=true) — excluded from the
   *  version history and never promoted to live. */
  is_template?: boolean;
  /** Display label; set for templates, null for ordinary versions. */
  name?: string | null;
  created_at: string | null;
  updated_at: string | null;
  published_at: string | null;
  created_by_user_id: string | null;
}

export interface AgentPhoneNumberInput {
  number: string;
  channel_id: string;
  label?: string | null;
}

// ─── API payloads ──────────────────────────────────────────────────────────

/** Sparse map from tool_id / mcp_server_id → OAuth connection id (or `null`
 * to explicitly clear the version-level override). Omitted entries are left
 * untouched — the runtime falls back to the entity default from the Tools /
 * MCP page. */
export type OAuthOverrideMap = Record<string, string | null>;

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
  web_channel_ids?: string[];
  tool_oauth_overrides?: OAuthOverrideMap;
  mcp_server_oauth_overrides?: OAuthOverrideMap;
}

/** Partial — only present fields are touched. Arrays present (even []) =
 * full replacement. Arrays omitted = left untouched. */
export type UpdateAgentPayload = Partial<CreateAgentPayload>;

// ─── API responses ─────────────────────────────────────────────────────────

export interface AgentToolRef {
  id: string;
  name: string;
  /** Per-version OAuth override set on the agent config page (or `null` when
   * no override — runtime falls back to `default_oauth_connection_id`). */
  oauth_connection_id?: string | null;
  /** The tool's default OAuth from the Tools page, echoed so the UI can show
   * "Using default (label)" without a second lookup. */
  default_oauth_connection_id?: string | null;
}

export interface AgentMcpServerRef {
  id: string;
  name: string;
  oauth_connection_id?: string | null;
  default_oauth_connection_id?: string | null;
}

export interface AgentDocumentRef {
  id: string;
  file_path?: string | null;
  file_name?: string | null;
  // Present on the agent-detail response so the form can pre-fill the per-KB
  // active-run dropdown. `knowledge_base_id` is the internal KB row id used
  // by the `PUT .../active-run` endpoint (distinct from the upload id `id`).
  knowledge_base_id?: string | null;
  active_ingestion_pipeline_run_id?: string | null;
}

export interface AgentPhoneNumberRef {
  id: string;
  number: string;
  label?: string | null;
  channel_id?: string | null;
}

export interface AgentWebChannelRef {
  id: string;
  channel_id: string;
  channel_type: string;
  name: string;
  slug: string;
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
  web_channels: AgentWebChannelRef[];
  /** Version history, newest first. The row with `is_live: true` is the one
   * `agents.published_config_id` currently points at. */
  versions?: AgentVersionSummary[];
}

/** Last-known readiness attached to each list row by POST /agent/list. Read
 * from the stored snapshot (no recompute), so it can lag the editor until a
 * fresh check runs. Null when the agent has no stored run yet. */
export interface AgentListReadiness {
  overall_status: ReadinessOverallStatus;
  blocker_count: number;
  warning_count: number;
  info_count: number;
  run_number: number | null;
  computed_at: string | null;
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
  readiness: AgentListReadiness | null;
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

/** GET /agent/list_templates — an agent config flagged `is_template=true`,
 * offered as a starting point in the Create Agent dialog. */
export interface AgentTemplateSummary {
  source_config_id: string;
  name: string;
  agent_name: string;
  agent_type: AgentDirection;
  mode: 'prompt' | 'workflow';
}

/** GET /tool/get_agents_by_tool and /mcp-server/get_agents_by_mcp_server —
 * agents whose published version carries the entity. */
export interface AttachedAgentRef {
  id: string;
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

/** Profile-variable rows the user has staged while in CREATE mode, before the
 * agent exists. Buffered here in local form state and flushed via a batch of
 * `POST /agents/{new_id}/profile-variables` calls right after the agent is
 * created (see `AgentEditorShell.onSubmit`). In EDIT mode this list stays
 * empty — the tab talks directly to the API. `_draftId` is a client-only
 * key so we can update/remove one row without a persisted id. */
export interface ProfileVariableDraft {
  _draftId: string;
  key: string;
  value: string;
  description: string | null;
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
    mode: 'prompt' | 'workflow';
    workflow_id: string | null;
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
  web_channel_ids: string[];
  /** Per-attachment OAuth override maps ({@link OAuthOverrideMap}). Only
   * entries the user actually touched are sent to the backend — an entry
   * that mirrors the tool/MCP's default OAuth is treated as "no override". */
  tool_oauth_overrides: OAuthOverrideMap;
  mcp_server_oauth_overrides: OAuthOverrideMap;
  /** CREATE mode only — profile variables staged before the agent exists.
   * Flushed to `POST /agents/{new_id}/profile-variables` right after create.
   * Always `[]` in EDIT mode (the tab talks directly to the API). */
  profile_variable_drafts: ProfileVariableDraft[];
}

export interface CreateAgentModalOption {
  type: AgentType;
  title: string;
  description: string;
  icon: React.ReactNode;
}
