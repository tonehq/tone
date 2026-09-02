import type {
  AgentDetail,
  AgentDirection,
  AgentFormState,
  AgentPhoneNumberInput,
  CreateAgentPayload,
  UpdateAgentPayload,
} from '@/types/agent';

const DEFAULT_VOICE_SPEED = 1.0;
const DEFAULT_MAX_DURATION = 600;

export const defaultFormState = (agentType: AgentDirection): AgentFormState => ({
  name: agentType === 'outbound' ? 'My Outbound Assistant' : 'My Inbound Assistant',
  description: '',
  agent_type: agentType,
  is_active: true,
  config: {
    first_message: '',
    end_call_message: '',
    mode: 'prompt',
    workflow_id: null,
    system_prompt_template: '',
    language_id: null,
    llm_settings: {},
    voice_settings: {
      provider_id: null,
      voice_id: null,
      language: null,
      speed: DEFAULT_VOICE_SPEED,
    },
    stt_settings: {},
    conversation_settings: { max_duration_seconds: DEFAULT_MAX_DURATION },
  },
  tool_ids: [],
  mcp_server_ids: [],
  upload_ids: [],
  phone_numbers: [],
  web_channel_ids: [],
  tool_oauth_overrides: {},
  mcp_server_oauth_overrides: {},
  profile_variable_drafts: [],
});

/** Build the OAuth override map from AgentDetail refs. Only stores entries
 * where the version-level override actually differs from the entity default,
 * so hydrating and re-serializing an untouched form produces an empty diff. */
function refsToOAuthOverrides<T extends { id: string; oauth_connection_id?: string | null }>(
  refs: T[] | undefined,
): Record<string, string | null> {
  const out: Record<string, string | null> = {};
  for (const ref of refs ?? []) {
    if (ref.oauth_connection_id != null) {
      out[ref.id] = ref.oauth_connection_id;
    }
  }
  return out;
}

/** Hydrate a form state from the backend's AgentDetail. */
export function agentDetailToFormState(detail: AgentDetail): AgentFormState {
  const base = defaultFormState(detail.agent_type);
  const cfg = detail.config ?? base.config;
  return {
    name: detail.name,
    description: detail.description ?? '',
    agent_type: detail.agent_type,
    is_active: detail.is_active,
    config: {
      first_message: cfg.first_message ?? base.config.first_message,
      end_call_message: cfg.end_call_message ?? base.config.end_call_message,
      mode: cfg.mode === 'workflow' ? 'workflow' : 'prompt',
      workflow_id: cfg.workflow_id ?? null,
      system_prompt_template: cfg.system_prompt_template ?? base.config.system_prompt_template,
      language_id: cfg.language_id ?? null,
      llm_settings: cfg.llm_settings ?? {},
      voice_settings: cfg.voice_settings ?? base.config.voice_settings,
      stt_settings: cfg.stt_settings ?? {},
      conversation_settings: cfg.conversation_settings ?? base.config.conversation_settings,
    },
    tool_ids: (detail.tools ?? []).map((t) => t.id),
    mcp_server_ids: (detail.mcp_servers ?? []).map((m) => m.id),
    upload_ids: (detail.documents ?? []).map((d) => d.id),
    phone_numbers: (detail.phone_numbers ?? []).map((p) => ({
      number: p.number,
      channel_id: p.channel_id ?? '',
      label: p.label ?? null,
    })),
    web_channel_ids: (detail.web_channels ?? []).map((c) => c.channel_id),
    tool_oauth_overrides: refsToOAuthOverrides(detail.tools),
    mcp_server_oauth_overrides: refsToOAuthOverrides(detail.mcp_servers),
    // Drafts are a CREATE-only concept — hydrating an existing agent always
    // seeds an empty list; the Profile tab pulls its rows from the API.
    profile_variable_drafts: [],
  };
}

/** Pure value equality for the small JSON-ish shapes we ship in config. */
function valuesEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a == null || b == null) return a == null && b == null;
  if (typeof a !== typeof b) return false;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((v, i) => valuesEqual(v, b[i]));
  }
  if (typeof a === 'object' && typeof b === 'object') {
    const ak = Object.keys(a as Record<string, unknown>);
    const bk = Object.keys(b as Record<string, unknown>);
    if (ak.length !== bk.length) return false;
    return ak.every((k) =>
      valuesEqual((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k]),
    );
  }
  return false;
}

function phoneListEqual(a: AgentPhoneNumberInput[], b: AgentPhoneNumberInput[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((row, i) => {
    const other = b[i];
    return (
      row.number === other.number &&
      row.channel_id === other.channel_id &&
      (row.label ?? null) === (other.label ?? null)
    );
  });
}

/** Strip override entries whose tool/mcp is no longer selected — a UI-only
 * cleanup so we never send an override for something the agent isn't using.
 * Also drops entries with a ``null`` value that never existed on the server
 * baseline, since sending ``{id: null}`` in that case is a no-op. */
function pruneOverrides(
  overrides: Record<string, string | null>,
  selectedIds: string[],
): Record<string, string | null> {
  const selected = new Set(selectedIds);
  const out: Record<string, string | null> = {};
  for (const [id, val] of Object.entries(overrides)) {
    if (selected.has(id)) out[id] = val;
  }
  return out;
}

/**
 * Normalise config for persistence. Prompt mode must never save a workflow
 * assignment: the call-time runtime ignores it (it gates on ``mode``), and a
 * lingering ``workflow_id`` makes version-creation wrongly clone a workflow.
 * The UI intentionally keeps the selection in-session so toggling Prompt↔Workflow
 * doesn't lose it — the assignment is stripped here, only at save time.
 */
function configForSave(config: AgentFormState['config']): AgentFormState['config'] {
  return config.mode === 'workflow' ? config : { ...config, workflow_id: null };
}

export function formStateToCreatePayload(state: AgentFormState): CreateAgentPayload {
  const toolOverrides = pruneOverrides(state.tool_oauth_overrides, state.tool_ids);
  const mcpOverrides = pruneOverrides(state.mcp_server_oauth_overrides, state.mcp_server_ids);
  return {
    name: state.name.trim(),
    agent_type: state.agent_type,
    description: state.description.trim() || undefined,
    is_active: state.is_active,
    config: configForSave(state.config),
    tool_ids: state.tool_ids,
    mcp_server_ids: state.mcp_server_ids,
    upload_ids: state.upload_ids,
    phone_numbers: state.phone_numbers,
    web_channel_ids: state.web_channel_ids,
    ...(Object.keys(toolOverrides).length > 0 && { tool_oauth_overrides: toolOverrides }),
    ...(Object.keys(mcpOverrides).length > 0 && { mcp_server_oauth_overrides: mcpOverrides }),
  };
}

/** Diff-aware: only sends fields that actually changed. Arrays are full
 * replacements when included, so we only include them when the user touched
 * them — otherwise the backend would treat an unchanged array as an explicit
 * replacement. */
export function formStateToUpdatePayload(
  next: AgentFormState,
  prev: AgentFormState,
): UpdateAgentPayload {
  const payload: UpdateAgentPayload = {};

  if (next.name.trim() !== prev.name.trim()) payload.name = next.name.trim();
  if ((next.description ?? '').trim() !== (prev.description ?? '').trim()) {
    payload.description = next.description.trim() || null;
  }
  if (next.agent_type !== prev.agent_type) payload.agent_type = next.agent_type;
  if (next.is_active !== prev.is_active) payload.is_active = next.is_active;

  // Config: diff per-field; only include the fields that changed. Normalise both
  // sides so a prompt-mode workflow_id is stripped before diffing (see configForSave).
  const nextCfg = configForSave(next.config);
  const prevCfg = configForSave(prev.config);
  const cfgDiff: Record<string, unknown> = {};
  (Object.keys(nextCfg) as (keyof AgentFormState['config'])[]).forEach((key) => {
    if (!valuesEqual(nextCfg[key], prevCfg[key])) {
      cfgDiff[key] = nextCfg[key];
    }
  });
  if (Object.keys(cfgDiff).length > 0) {
    payload.config = cfgDiff as CreateAgentPayload['config'];
  }

  if (!valuesEqual(next.tool_ids, prev.tool_ids)) payload.tool_ids = next.tool_ids;
  if (!valuesEqual(next.mcp_server_ids, prev.mcp_server_ids)) {
    payload.mcp_server_ids = next.mcp_server_ids;
  }

  // OAuth overrides — send when the user changed a per-attachment override,
  // OR when the selection changed (backend needs to see cleared entries for
  // newly-removed tools/MCPs). Prunes stale entries for detached items so the
  // payload never carries an override for something no longer selected.
  const nextToolOv = pruneOverrides(next.tool_oauth_overrides, next.tool_ids);
  const prevToolOv = pruneOverrides(prev.tool_oauth_overrides, prev.tool_ids);
  if (!valuesEqual(nextToolOv, prevToolOv)) payload.tool_oauth_overrides = nextToolOv;
  const nextMcpOv = pruneOverrides(next.mcp_server_oauth_overrides, next.mcp_server_ids);
  const prevMcpOv = pruneOverrides(prev.mcp_server_oauth_overrides, prev.mcp_server_ids);
  if (!valuesEqual(nextMcpOv, prevMcpOv)) payload.mcp_server_oauth_overrides = nextMcpOv;

  if (!valuesEqual(next.upload_ids, prev.upload_ids)) payload.upload_ids = next.upload_ids;
  if (!phoneListEqual(next.phone_numbers, prev.phone_numbers)) {
    payload.phone_numbers = next.phone_numbers;
  }
  if (!valuesEqual(next.web_channel_ids, prev.web_channel_ids)) {
    payload.web_channel_ids = next.web_channel_ids;
  }

  return payload;
}
