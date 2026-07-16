'use client';

import { useAtom } from 'jotai';
import { useEffect, useState } from 'react';

import { fetchAgentReadinessSummaryAtom } from '@/atoms/ReadinessAtom';
import type { ReadinessSummary } from '@/types/readiness';

import ReadinessBadge from './ReadinessBadge';

interface AgentReadinessCellProps {
  agentId: string;
  /** Click handler — receives the summary in case the parent wants to open a
   * drawer scoped to this agent. */
  onOpen?: (agentId: string, summary: ReadinessSummary | null) => void;
}

/**
 * One row in the agent list table. Fetches its own Shallow summary lazily so
 * the table can render immediately and populate rows as their responses come
 * in — avoiding a blocking bulk fetch. Non-critical UI: any failure just
 * shows an "unavailable" pill, never a toast.
 */
export default function AgentReadinessCell({ agentId, onOpen }: AgentReadinessCellProps) {
  const [, fetchSummary] = useAtom(fetchAgentReadinessSummaryAtom);
  const [summary, setSummary] = useState<ReadinessSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    (async () => {
      try {
        const next = await fetchSummary({ agentId, trigger: 'list_page' });
        if (!cancelled) setSummary(next);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [agentId, fetchSummary]);

  const status = loading && !summary ? 'loading' : error ? 'error' : summary?.overall_status;

  return (
    <ReadinessBadge
      status={status ?? 'error'}
      blockerCount={summary?.blocker_count ?? 0}
      warningCount={summary?.warning_count ?? 0}
      size="sm"
      onClick={
        onOpen
          ? (e) => {
              // Stop propagation so the surrounding row-click (which opens
              // the editor) doesn't fire in addition to the drawer.
              e.stopPropagation();
              onOpen(agentId, summary);
            }
          : undefined
      }
    />
  );
}
