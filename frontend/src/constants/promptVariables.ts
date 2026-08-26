/**
 * Canonical list of runtime template variables a user can insert into an agent's
 * system prompt via the prompt editor. Each is stored in the prompt text as a
 * `{{key}}` placeholder and substituted with live call data at runtime.
 *
 * KEEP THIS IN SYNC with the backend registry:
 *   core/services/pipeline/prompt_variables.py (PROMPT_VARIABLE_KEYS + build_call_context)
 *
 * Per-agent Profile variables (group `Profile`) are loaded via API at editor
 * mount time — they are NOT hard-coded here. Use `buildProfileVariableItems`
 * below to shape API rows into `PromptVariable`s the picker consumes.
 */

import type { AgentProfileVariable } from '@/types/agentProfileVariable';

export interface PromptVariable {
  /** Stable identifier used in the `{{key}}` placeholder. */
  key: string;
  /** Human label shown in the chip and suggestion menu. */
  label: string;
  /** One-line explanation shown in the suggestion menu. */
  description: string;
  /** Grouping bucket for the menu. */
  group: 'Caller' | 'Agent' | 'Call' | 'Profile';
}

/** Prefix every profile variable placeholder carries — kept in ONE place. */
export const PROFILE_VARIABLE_PREFIX = 'profile.';

export const PROMPT_VARIABLES: readonly PromptVariable[] = [
  {
    key: 'caller_number',
    label: 'Caller number',
    description: "The caller's phone number (E.164).",
    group: 'Caller',
  },
  {
    key: 'callee_number',
    label: 'Callee number',
    description: 'The number that was dialed.',
    group: 'Call',
  },
  {
    key: 'agent_name',
    label: 'Agent name',
    description: "This agent's name.",
    group: 'Agent',
  },
  {
    key: 'current_date',
    label: 'Current date',
    description: "Today's date (YYYY-MM-DD) at call time.",
    group: 'Call',
  },
  {
    key: 'current_time',
    label: 'Current time',
    description: 'The time (HH:MM) at call time.',
    group: 'Call',
  },
  {
    key: 'call_direction',
    label: 'Call direction',
    description: 'Inbound, outbound, or both.',
    group: 'Call',
  },
] as const;

/** Fast lookup of a variable definition by its key. */
export const PROMPT_VARIABLE_BY_KEY: Readonly<Record<string, PromptVariable>> = Object.fromEntries(
  PROMPT_VARIABLES.map((v) => [v.key, v]),
);

/** Display label for a key, falling back to the key itself for unknown variables. */
export function promptVariableLabel(key: string): string {
  return PROMPT_VARIABLE_BY_KEY[key]?.label ?? key;
}

/** Whether a key corresponds to a known, substitutable variable.
 * System variables are matched against the hard-coded registry; profile
 * variables are matched by the `profile.` namespace prefix — the actual
 * variable set is per-agent and loaded at runtime, so the parser only needs
 * to know it's SHAPED like a profile placeholder to render it as a chip
 * instead of literal text. */
export function isKnownPromptVariable(key: string): boolean {
  if (key in PROMPT_VARIABLE_BY_KEY) return true;
  return key.startsWith(PROFILE_VARIABLE_PREFIX) && key.length > PROFILE_VARIABLE_PREFIX.length;
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

/** Shape API rows into `PromptVariable`s the picker consumes. The prefix is
 * baked in here so no call site emits the wrong placeholder shape. */
export function buildProfileVariableItems(vars: AgentProfileVariable[]): PromptVariable[] {
  return vars.map((v) => ({
    key: `${PROFILE_VARIABLE_PREFIX}${v.key}`,
    label: v.key,
    description:
      v.description?.trim() || (v.value ? `= ${truncate(v.value, 80)}` : 'Profile variable'),
    group: 'Profile',
  }));
}
