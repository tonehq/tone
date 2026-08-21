import {
  Book,
  CalendarClock,
  Clock,
  Gauge,
  MessageSquare,
  Radio,
  Settings2,
  Users,
  Volume2,
  Wrench,
} from 'lucide-react';

import type { SidebarNavGroup } from '@/components/layout/SidebarShell';
import type { AgentDirection } from '@/types/agent';

// Single source of truth for the agent editor's configuration sections. The
// editor rail (AgentEditorShell) and the routed section pages both derive from
// this so the two can never drift. Each section is its own URL route under the
// editor base path, e.g. /agents/edit/inbound/<id>/voice.

export interface AgentSection {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

// Order matters — this is the order shown in the rail and the order the routed
// section pages follow. The "Prompt" section hosts both the system prompt and
// the agent's workflows behind a Prompt/Workflow toggle (they're two ways to
// drive the same conversation), so there is no separate Workflow entry.
//
// "Setup" bundles the read-only Overview (edit mode only), Basics, and AI
// sections into a single page — they're all the "who is this agent + which
// brain drives it" concerns and read cleanly stacked.
export const AGENT_SECTIONS: AgentSection[] = [
  { key: 'setup', label: 'Setup', icon: Settings2 },
  { key: 'prompt', label: 'Prompt', icon: MessageSquare },
  { key: 'voice', label: 'Voice', icon: Volume2 },
  { key: 'tools', label: 'Tools & MCP', icon: Wrench },
  { key: 'knowledge', label: 'Knowledge', icon: Book },
  // LLM Evals sits after Knowledge — Level-2 sits below Level-1 in the UX
  // as it does in the mental model (RAG evals score retrieval; LLM evals
  // score the agent's actual answer + system-prompt behavior).
  { key: 'llm-evals', label: 'LLM Evals', icon: Gauge },
  { key: 'channels', label: 'Channels', icon: Radio },
  { key: 'contacts', label: 'Contacts', icon: Users },
  { key: 'schedule', label: 'Schedule', icon: CalendarClock },
  { key: 'call-history', label: 'Call History', icon: Clock },
];

/**
 * Sections shown only for a saved agent (edit mode) — omitted while creating.
 * `contacts`/`schedule` (C-5): they need a persisted `agent_id`, which only exists
 * after the agent is saved, so the tabs must not render in create mode.
 */
const EDIT_ONLY_SECTION_KEYS = new Set<string>(['call-history', 'contacts', 'schedule']);

/**
 * Sections gated on the agent's call mode. `contacts`/`schedule` only make sense for
 * agents that place outbound calls (`outbound` or `both`) — an inbound-only agent never
 * dials a contact, so the tabs are hidden for it.
 */
const OUTBOUND_ONLY_SECTION_KEYS = new Set<string>(['contacts', 'schedule']);

/** True when the agent handles outbound calls (`outbound` or `both`). */
function handlesOutbound(callMode: AgentDirection): boolean {
  return callMode === 'outbound' || callMode === 'both';
}

export const AGENT_SECTION_KEYS = AGENT_SECTIONS.map((s) => s.key);

/** Default landing section for each editor mode. */
export const DEFAULT_SECTION = { edit: 'setup', create: 'setup' } as const;

/**
 * Build the rail nav for the agent editor. `callMode` is the agent's current
 * call direction (live form value in the editor); sections in
 * `OUTBOUND_ONLY_SECTION_KEYS` (e.g. `contacts`) are shown only when the agent
 * handles outbound calls (`outbound`/`both`).
 */
export function buildAgentNav(
  basePath: string,
  mode: 'edit' | 'create',
  callMode: AgentDirection,
): SidebarNavGroup[] {
  const items = [];
  for (const s of AGENT_SECTIONS) {
    if (mode === 'create' && EDIT_ONLY_SECTION_KEYS.has(s.key)) continue;
    if (OUTBOUND_ONLY_SECTION_KEYS.has(s.key) && !handlesOutbound(callMode)) continue;
    items.push({ label: s.label, href: `${basePath}/${s.key}`, icon: s.icon });
  }
  return [{ heading: null, items }];
}
