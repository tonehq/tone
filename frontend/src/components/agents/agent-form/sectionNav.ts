import {
  Book,
  Bot,
  Clock,
  Cpu,
  LayoutGrid,
  MessageSquare,
  Radio,
  Volume2,
  Wrench,
} from 'lucide-react';

import type { SidebarNavGroup } from '@/components/layout/SidebarShell';

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
export const AGENT_SECTIONS: AgentSection[] = [
  { key: 'basics', label: 'Basics', icon: Bot },
  { key: 'prompt', label: 'Prompt', icon: MessageSquare },
  { key: 'ai', label: 'AI', icon: Cpu },
  { key: 'voice', label: 'Voice', icon: Volume2 },
  { key: 'tools', label: 'Tools & MCP', icon: Wrench },
  { key: 'knowledge', label: 'Knowledge', icon: Book },
  { key: 'channels', label: 'Channels', icon: Radio },
  { key: 'call-history', label: 'Call History', icon: Clock },
];

/** Sections shown only for a saved agent (edit mode) — omitted while creating. */
const EDIT_ONLY_SECTION_KEYS = new Set<string>(['call-history']);

export const AGENT_SECTION_KEYS = AGENT_SECTIONS.map((s) => s.key);

/** Default landing section for each editor mode. */
export const DEFAULT_SECTION = { edit: 'overview', create: 'basics' } as const;

/**
 * Build the rail nav for the agent editor. `edit` mode prepends an "Overview"
 * entry (a saved agent has something to summarise); `create` mode omits it.
 */
export function buildAgentNav(basePath: string, mode: 'edit' | 'create'): SidebarNavGroup[] {
  const items = [];
  if (mode === 'edit') {
    items.push({ label: 'Overview', href: `${basePath}/overview`, icon: LayoutGrid });
  }
  for (const s of AGENT_SECTIONS) {
    if (mode === 'create' && EDIT_ONLY_SECTION_KEYS.has(s.key)) continue;
    items.push({ label: s.label, href: `${basePath}/${s.key}`, icon: s.icon });
  }
  return [{ heading: null, items }];
}
