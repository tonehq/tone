'use client';

import type { AgentListReadiness } from '@/types/agent';

import ReadinessBadge from './ReadinessBadge';

interface AgentReadinessCellProps {
  agentId: string;
  /** Last-known readiness for this row, supplied by the list API. Null when the
   * agent has no stored run yet — the badge then shows "unavailable" until the
   * user opens the drawer (which computes a fresh check). */
  readiness: AgentListReadiness | null;
  /** Click handler — receives the row's readiness so the parent can open a
   * drawer scoped to this agent. */
  onOpen?: (agentId: string, readiness: AgentListReadiness | null) => void;
}

/**
 * One row in the agent list table. Renders the readiness badge straight from
 * the list-API payload — no per-row fetch. This replaces the old N+1 where
 * every row fired its own `/readiness/summary` request. The value is
 * last-known state (read from the stored snapshot, not recomputed); the editor
 * drawer refreshes it live when opened.
 */
export default function AgentReadinessCell({
  agentId,
  readiness,
  onOpen,
}: AgentReadinessCellProps) {
  return (
    <ReadinessBadge
      status={readiness?.overall_status ?? 'error'}
      blockerCount={readiness?.blocker_count ?? 0}
      warningCount={readiness?.warning_count ?? 0}
      size="sm"
      onClick={
        onOpen
          ? (e) => {
              // Stop propagation so the surrounding row-click (which opens the
              // editor) doesn't fire in addition to the drawer.
              e.stopPropagation();
              onOpen(agentId, readiness);
            }
          : undefined
      }
    />
  );
}
