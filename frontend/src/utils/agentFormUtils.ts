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
    system_prompt_template: '',
    language_id: null,
    knowledge_model_id: null,
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
});

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
      system_prompt_template: cfg.system_prompt_template ?? base.config.system_prompt_template,
      language_id: cfg.language_id ?? null,
      knowledge_model_id: cfg.knowledge_model_id ?? null,
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

export function formStateToCreatePayload(state: AgentFormState): CreateAgentPayload {
  return {
    name: state.name.trim(),
    agent_type: state.agent_type,
    description: state.description.trim() || undefined,
    is_active: state.is_active,
    config: state.config,
    tool_ids: state.tool_ids,
    mcp_server_ids: state.mcp_server_ids,
    upload_ids: state.upload_ids,
    phone_numbers: state.phone_numbers,
    web_channel_ids: state.web_channel_ids,
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

  // Config: diff per-field; only include the fields that changed.
  const cfgDiff: Record<string, unknown> = {};
  (Object.keys(next.config) as (keyof AgentFormState['config'])[]).forEach((key) => {
    if (!valuesEqual(next.config[key], prev.config[key])) {
      cfgDiff[key] = next.config[key];
    }
  });
  if (Object.keys(cfgDiff).length > 0) {
    payload.config = cfgDiff as CreateAgentPayload['config'];
  }

  if (!valuesEqual(next.tool_ids, prev.tool_ids)) payload.tool_ids = next.tool_ids;
  if (!valuesEqual(next.mcp_server_ids, prev.mcp_server_ids)) {
    payload.mcp_server_ids = next.mcp_server_ids;
  }
  if (!valuesEqual(next.upload_ids, prev.upload_ids)) payload.upload_ids = next.upload_ids;
  if (!phoneListEqual(next.phone_numbers, prev.phone_numbers)) {
    payload.phone_numbers = next.phone_numbers;
  }
  if (!valuesEqual(next.web_channel_ids, prev.web_channel_ids)) {
    payload.web_channel_ids = next.web_channel_ids;
  }

  return payload;
}
