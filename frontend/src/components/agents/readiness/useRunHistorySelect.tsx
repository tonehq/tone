'use client';

import { useCallback, useMemo } from 'react';

import type { SelectOption } from '@/components/shared';
import type { ReadinessReport, ReadinessRunListItem } from '@/types/readiness';
import { formatRelative } from '@/utils/date';

import ReadinessBadge from './ReadinessBadge';
import { RUN_HISTORY_LATEST_VALUE } from './readinessConstants';
import { triggerLabelFor } from './readinessHelpers';

interface UseRunHistorySelectArgs {
  runs: ReadinessRunListItem[];
  /** null = viewing the live/latest report. */
  selectedRunNumber: number | null;
  /** The live report — its run number labels the "Latest run" row. */
  liveReport: ReadinessReport | null;
  /** Config currently open, so cross-version runs can be flagged. */
  configId?: string | null;
  /** Fires with null for "Latest", or the picked run number. */
  onSelect: (id: string | number | null) => void;
}

/**
 * Builds the props the run-history {@link SelectInput} needs: options, the
 * selected value, the change handler, and the rich option/trigger renderers.
 * Extracted from the drawer so the component stays JSX-only.
 */
export function useRunHistorySelect({
  runs,
  selectedRunNumber,
  liveReport,
  configId,
  onSelect,
}: UseRunHistorySelectArgs) {
  const liveRunNumber = liveReport?.run_number ?? null;

  // Drop the live run from the history rows — it's already surfaced (editable)
  // as the "Latest run" option, so listing it again as a read-only "Run #N"
  // row would duplicate the same run.
  const historyRuns = useMemo(
    () => runs.filter((run) => run.run_number !== liveRunNumber),
    [runs, liveRunNumber],
  );

  // `label` stays a plain string (typeahead / accessibility); rich rows come
  // from `renderOption`.
  const options: SelectOption[] = useMemo(
    () => [
      { value: RUN_HISTORY_LATEST_VALUE, label: 'Latest run' },
      ...historyRuns.map((run) => ({
        value: String(run.run_number),
        label: `Run #${run.run_number}`,
      })),
    ],
    [historyRuns],
  );

  const runByValue = useMemo(
    () => new Map(historyRuns.map((run) => [String(run.run_number), run])),
    [historyRuns],
  );

  const value = selectedRunNumber != null ? String(selectedRunNumber) : RUN_HISTORY_LATEST_VALUE;

  const onValueChange = useCallback(
    (next: string) => onSelect(next === RUN_HISTORY_LATEST_VALUE ? null : next),
    [onSelect],
  );

  const renderOption = useCallback(
    (option: SelectOption) => {
      if (option.value === RUN_HISTORY_LATEST_VALUE) {
        return (
          <span className="flex min-w-0 flex-col">
            <span className="text-[12px] font-medium leading-tight">Latest run</span>
            {liveRunNumber != null && (
              <span className="mt-0.5 text-[11px] leading-tight text-muted-foreground">
                Run #{liveRunNumber}
              </span>
            )}
          </span>
        );
      }
      const run = runByValue.get(option.value);
      if (!run) return option.label;
      return (
        <span className="flex min-w-0 flex-col">
          <span className="text-[12px] font-medium leading-tight">
            {triggerLabelFor(run.trigger)} · {formatRelative(run.computed_at)}
          </span>
          <span className="mt-0.5 flex items-center gap-1.5 text-[11px] leading-tight text-muted-foreground">
            <ReadinessBadge status={run.overall_status} size="sm" iconOnly />
            Run #{run.run_number}
            {run.config_id && configId && run.config_id !== configId && (
              <span className="text-amber-600 dark:text-amber-400">· other version</span>
            )}
          </span>
        </span>
      );
    },
    [liveRunNumber, runByValue, configId],
  );

  const renderValue = useCallback(
    (v: string | undefined) => (!v || v === RUN_HISTORY_LATEST_VALUE ? 'Latest run' : `Run #${v}`),
    [],
  );

  return { options, value, onValueChange, renderOption, renderValue };
}
