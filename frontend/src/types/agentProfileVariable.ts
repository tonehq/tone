/**
 * Shape of one per-agent profile variable — the `{{profile.<key>}}` values a
 * user can insert into prompts / workflow nodes. Backend model lives at
 * `core/models/agent_profile_variable.py`; keep this in sync with `to_dict()`.
 */
/** A variable is either a literal `value` (static) or filled from the agent's
 * webhook response at `source_path` (webhook; `value` is the fallback). */
export type ProfileVariableSource = 'static' | 'webhook';

export interface AgentProfileVariable {
  id: string;
  organization_id: string;
  agent_id: string;
  key: string;
  value: string;
  description: string | null;
  source: ProfileVariableSource;
  source_path: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** Body for POST /agents/{id}/profile-variables. */
export interface ProfileVariableInput {
  key: string;
  value: string;
  description?: string | null;
  source?: ProfileVariableSource;
  source_path?: string | null;
}

/** PATCH-style body for PUT /agents/{id}/profile-variables/{variableId}. */
export interface ProfileVariablePatch {
  key?: string;
  value?: string;
  description?: string | null;
  source?: ProfileVariableSource;
  source_path?: string | null;
}

export interface ListProfileVariablesResponse {
  items: AgentProfileVariable[];
}
