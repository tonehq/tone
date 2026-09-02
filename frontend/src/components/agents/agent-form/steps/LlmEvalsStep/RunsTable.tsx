import { ChevronRight, Folder as FolderIcon, History } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import type { AgentLlmEvalRunSummary } from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';

import { RUN_TERMINAL_STATUSES } from './constants';
import RunStatusChip from './RunStatusChip';

// NOTE: kept as a hand-rolled ``<table>`` (not migrated to the shared
// ``CustomTable``). Row interactivity is conditional per-row — only
// terminal runs are clickable, and non-terminal rows get a distinct
// cursor + tooltip + muted background. ``CustomTable``'s uniform
// ``onRowClick`` can't express that without behavior risk.
export default function RunsTable({
  runs,
  isLoading,
  onOpen,
  onEmptyCTA,
  showEmptyState = true,
}: {
  runs: AgentLlmEvalRunSummary[];
  isLoading: boolean;
  onOpen: (runId: string) => void;
  onEmptyCTA?: () => void;
  // ``true`` when the ENTIRE dataset is empty (not just the current page).
  // Lets a paginated caller suppress the "no runs yet" welcome state when
  // the emptiness is just an out-of-range page rather than a fresh agent.
  showEmptyState?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading runs…
      </div>
    );
  }
  if (runs.length === 0) {
    if (!showEmptyState) return null;
    return (
      <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border/60 p-8 text-center">
        <History className="size-6 text-muted-foreground/60" />
        <p className="text-sm text-muted-foreground">
          No runs yet. Head to Folders and click{' '}
          <span className="font-medium text-foreground">Run Eval</span> to score this agent.
        </p>
        {onEmptyCTA && (
          <CustomButton
            type="default"
            onClick={onEmptyCTA}
            icon={<FolderIcon className="size-4" />}
          >
            Go to Folders
          </CustomButton>
        )}
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Run</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Started</th>
            <th className="px-3 py-2 text-left">Judge</th>
            <th className="px-3 py-2 text-left">Answer Model</th>
            <th className="px-3 py-2 text-left">Triggered</th>
            <th className="px-3 py-2 text-left">Result</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => {
            const summary = r.summary as Record<string, number> | Record<string, never>;
            const total = (summary.total as number) ?? 0;
            const pass = (summary.pass as number) ?? 0;
            const fail = (summary.fail as number) ?? 0;
            const partial = (summary.partial as number) ?? 0;
            const passRate = (summary.pass_rate as number) ?? 0;
            const isTerminal = RUN_TERMINAL_STATUSES.has(r.status);
            // Non-terminal rows: swap the pass/fail readout for a
            // "Scoring N of M" progress line. Also disables the drawer
            // (the drawer reads persisted rows; non-terminal runs may
            // have partial or zero rows persisted so the drawer would
            // read as empty / half-scored).
            return (
              <tr
                key={r.run_id}
                className={cn(
                  'border-t border-border/60',
                  isTerminal ? 'cursor-pointer hover:bg-muted/30' : 'cursor-default bg-muted/10',
                )}
                onClick={isTerminal ? () => onOpen(r.run_id) : undefined}
                title={isTerminal ? undefined : 'Run in progress — open once it completes'}
              >
                <td className="px-3 py-2 font-medium text-foreground">#{r.run_number}</td>
                <td className="px-3 py-2">
                  <RunStatusChip status={r.status} />
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {r.started_at ? formatDate(r.started_at) : '—'}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{r.judge_model ?? '—'}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {r.llm_model ?? '—'}
                  {r.llm_provider && (
                    <span className="ml-1 text-[11px] text-muted-foreground/70">
                      · {r.llm_provider}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{r.triggered_by}</td>
                <td className="px-3 py-2">
                  {isTerminal ? (
                    <div className="flex items-center gap-2">
                      <span className="tabular-nums text-foreground">
                        <span className="text-emerald-600">{pass}</span>
                        {partial > 0 && (
                          <>
                            {' / '}
                            <span className="text-amber-600">{partial}</span>
                          </>
                        )}
                        {fail > 0 && (
                          <>
                            {' / '}
                            <span className="text-destructive">{fail}</span>
                          </>
                        )}
                        <span className="text-muted-foreground"> of {total}</span>
                      </span>
                      <span className="text-[11px] tabular-nums text-muted-foreground">
                        {Math.round(passRate * 100)}%
                      </span>
                    </div>
                  ) : (
                    <span className="text-[12px] tabular-nums text-muted-foreground">
                      Scoring <span className="font-medium text-foreground">{r.scored_count}</span>
                      {' of '}
                      <span className="font-medium text-foreground">
                        {r.total_scenarios || '—'}
                      </span>
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-muted-foreground">
                  {isTerminal ? (
                    <ChevronRight className="ml-auto size-4" />
                  ) : (
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground/70">
                      In progress
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
