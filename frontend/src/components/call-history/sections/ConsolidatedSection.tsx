'use client';

import { IconChip } from '@/components/shared';
import ConsolidatedTurnItem from '@/components/call-history/consolidated/ConsolidatedTurnItem';
import { getCallLogById } from '@/services/callLogService';
import type { CallLogRow } from '@/types/callLog';
import { Layers, Loader2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';

interface ConsolidatedSectionProps {
  callLog: CallLogRow;
}

const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ATTEMPTS = 10;

/**
 * "Consolidated" tab — renders one card per turn from
 * `callLog.consolidated_transcript`, produced by `ConsolidatedMetricsService`
 * which joins transcript + tool_executions + turn_metrics into a flat list
 * of turn dicts.
 *
 * If the call has ended but the payload is still missing (the background
 * action races the API call for freshly-ended calls), we poll every 3s for up
 * to ~30s and swap in the enriched log as soon as it arrives. Stops polling
 * on success, timeout, or unmount.
 */
const ConsolidatedSection: React.FC<ConsolidatedSectionProps> = ({ callLog }) => {
  const [enriched, setEnriched] = useState<CallLogRow | null>(null);
  const [polling, setPolling] = useState(false);

  const active = enriched ?? callLog;
  const turns = active.consolidated_transcript ?? null;
  const hasTurns = !!turns && turns.length > 0;
  const callEnded = !!active.ended_at;
  // Only poll if the call is done AND the consolidated payload hasn't arrived
  // yet. Active/in-progress calls never populate this — showing "Preparing…"
  // for them would be misleading, so we surface an in-progress state instead.
  const shouldPoll = callEnded && turns === null;

  useEffect(() => {
    if (!shouldPoll) {
      setPolling(false);
      return;
    }

    let cancelled = false;
    let attempts = 0;
    setPolling(true);

    const tick = async () => {
      attempts += 1;
      try {
        const next = await getCallLogById(callLog.id);
        if (cancelled) return;
        if (next.consolidated_transcript) {
          setEnriched(next);
          setPolling(false);
          return;
        }
      } catch {
        // Swallow — polling is best-effort and a transient failure shouldn't
        // interrupt the "Preparing…" UI. If it never recovers, the user still
        // sees the fallback empty state after the attempt cap.
      }
      if (attempts >= POLL_MAX_ATTEMPTS) {
        if (!cancelled) setPolling(false);
        return;
      }
      timerId = window.setTimeout(tick, POLL_INTERVAL_MS);
    };

    let timerId = window.setTimeout(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [callLog.id, shouldPoll]);

  if (polling) return <PreparingState />;
  if (!callEnded && !hasTurns) return <InProgressState />;
  if (!hasTurns) return <EmptyState hasPayload={turns !== null} />;

  return (
    <div className="flex flex-col gap-4">
      <Header total={turns.length} />
      <div className="flex flex-col gap-3">
        {turns.map((turn, i) => (
          <ConsolidatedTurnItem key={turn.turn_number} turn={turn} showDivider={i > 0} />
        ))}
      </div>
    </div>
  );
};

function Header({ total }: { total: number }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-foreground">Consolidated turns</h3>
      <p className="mt-0.5 text-xs text-muted-foreground">
        {total} {total === 1 ? 'turn' : 'turns'} · user speech, tool calls, latency and reply for
        each turn.
      </p>
    </div>
  );
}

function PreparingState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <IconChip
        icon={<Loader2 className="animate-spin" strokeWidth={1.75} />}
        tone="muted"
        size="lg"
        className="rounded-full"
      />
      <div>
        <p className="text-sm font-medium text-foreground">Preparing consolidated view…</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Merging transcript, tool calls and latency for this call.
        </p>
      </div>
    </div>
  );
}

function InProgressState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <IconChip
        icon={<Layers strokeWidth={1.75} />}
        tone="muted"
        size="lg"
        className="rounded-full"
      />
      <p className="text-sm text-muted-foreground">
        Consolidated view is generated after the call ends.
      </p>
    </div>
  );
}

function EmptyState({ hasPayload }: { hasPayload: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <IconChip
        icon={<Layers strokeWidth={1.75} />}
        tone="muted"
        size="lg"
        className="rounded-full"
      />
      <p className="text-sm text-muted-foreground">
        {hasPayload
          ? 'No turns were recorded for this call.'
          : 'Consolidated view is unavailable for this call.'}
      </p>
    </div>
  );
}

export default ConsolidatedSection;
