import { BarChart3, Layers, MessageSquareText, Settings2, Wrench } from 'lucide-react';

import type { SidebarNavGroup } from '@/components/layout/SidebarShell';

// Single source of truth for the call-detail sidebar sections. The detail shell
// (CallDetailShell) and the routed section page both derive from this so the
// two can never drift. Each section is its own URL segment under the call
// base path, e.g. /call-history/<id>/transcription.

export interface CallDetailSection {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

export const CALL_DETAIL_SECTIONS: CallDetailSection[] = [
  { key: 'transcription', label: 'Transcription & Recordings', icon: MessageSquareText },
  { key: 'consolidated', label: 'Consolidated', icon: Layers },
  { key: 'metrics', label: 'Metrics', icon: BarChart3 },
  { key: 'tools-mcp', label: 'Tool and MCP Executions', icon: Wrench },
  { key: 'configurations', label: 'Call Configurations', icon: Settings2 },
];

export const CALL_DETAIL_SECTION_KEYS = CALL_DETAIL_SECTIONS.map((s) => s.key);

export const DEFAULT_CALL_DETAIL_SECTION = 'transcription';

// `search` (e.g. "?from=%2Fagents%2F…") is appended to every section href so
// the origin the user came from survives tab switches inside the detail view —
// otherwise clicking Metrics would drop the `from` param and the back link
// would revert to the global call history.
export function buildCallDetailNav(basePath: string, search = ''): SidebarNavGroup[] {
  return [
    {
      heading: null,
      items: CALL_DETAIL_SECTIONS.map((s) => ({
        label: s.label,
        href: `${basePath}/${s.key}${search}`,
        icon: s.icon,
      })),
    },
  ];
}
