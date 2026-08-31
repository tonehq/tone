'use client';

import { useAtom } from 'jotai';
import { Beaker, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  fetchAgentReadinessAtom,
  fetchAgentReadinessRunAtom,
  fetchAgentReadinessRunsAtom,
} from '@/atoms/ReadinessAtom';
import { CustomButton, CustomDrawer, SelectInput } from '@/components/shared';
import type { ReadinessReport, ReadinessRunListItem, ReadinessTrigger } from '@/types/readiness';
import { cn } from '@/utils/cn';
import { formatDate, formatRelative } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ReadinessBadge from './ReadinessBadge';
import ReadinessCheckList from './ReadinessCheckList';
import { countLabel } from './readinessHelpers';
import { useRunHistorySelect } from './useRunHistorySelect';

interface ReadinessDrawerProps {
  open: boolean;
  onClose: () => void;
  agentId: string | null;
  /** When set, the drawer fetches the report for this exact config. When null,
   * the backend resolves the "active" config (published or default). */
  configId?: string | null;
  /** Optional label describing where the drawer was opened from; forwarded as
   * the readiness `trigger` string for analytics. */
  trigger?: ReadinessTrigger | string;
  /** Report supplied by the parent (typically the freshest targeted-deep
   * result from a save). When present, the drawer renders it on open instead
   * of firing its own shallow fetch — keeps the drawer and the header badge
   * in agreement. */
  initialReport?: ReadinessReport | null;
  /** Lets the drawer inform the parent when the LIVE report changes (Refresh /
   * Run deep test) so the badge and the drawer stay in sync afterwards.
   * Deliberately NOT called when viewing a historical run — the parent badge
   * must keep reflecting the live report. */
  onReportChange?: (report: ReadinessReport | null) => void;
}

/**
 * Right-side drawer holding the full readiness report. Adopts a parent-provided
 * `initialReport` on open (else fetches Shallow), escalates to Deep via "Run
 * deep test", and browses past deep runs (read-only) via the run-history select.
 */
export default function ReadinessDrawer({
  open,
  onClose,
  agentId,
  configId,
  trigger = 'editor_load',
  initialReport = null,
  onReportChange,
}: ReadinessDrawerProps) {
  const [, runReadiness] = useAtom(fetchAgentReadinessAtom);
  const [, fetchRuns] = useAtom(fetchAgentReadinessRunsAtom);
  const [, fetchRun] = useAtom(fetchAgentReadinessRunAtom);

  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [deepRunning, setDeepRunning] = useState(false);

  // ── run-history state ──────────────────────────────────────────────────
  const [runs, setRuns] = useState<ReadinessRunListItem[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  // Run-number + its report held as one unit so they can't drift (no stale
  // report under a mismatched selection). null = live/latest report.
  const [history, setHistory] = useState<{
    runNumber: number;
    report: ReadinessReport | null;
  } | null>(null);
  // Monotonic id so a slower, superseded history fetch can't land late.
  const historyReqIdRef = useRef(0);

  const viewingHistory = history !== null;
  const selectedRunNumber = history?.runNumber ?? null;

  // Sole entry point for LIVE report changes → keeps the parent badge in sync.
  // Historical selection bypasses this so it never leaks into the parent badge.
  const applyReport = useCallback(
    (next: ReadinessReport | null) => {
      setReport(next);
      onReportChange?.(next);
    },
    [onReportChange],
  );

  const loadRuns = useCallback(async () => {
    if (!agentId) return;
    setRunsLoading(true);
    try {
      const res = await fetchRuns({ agentId, limit: 20 });
      setRuns(res.items);
    } catch (err) {
      // Keep any already-loaded runs visible on a transient refresh failure
      // (don't blank the dropdown), and surface the error per repo convention
      // rather than swallowing it.
      handleApiError(err);
    } finally {
      setRunsLoading(false);
    }
  }, [agentId, fetchRuns]);

  const load = useCallback(
    async (depth: 'shallow' | 'deep', why: ReadinessTrigger | string = trigger, force = false) => {
      if (!agentId) return;
      const isDeep = depth === 'deep';
      if (isDeep) setDeepRunning(true);
      else setLoading(true);
      try {
        const next = await runReadiness({
          agentId,
          depth,
          configId: configId ?? undefined,
          trigger: why,
          force,
        });
        applyReport(next);
        // A fresh deep run just landed a new event row — refresh the history
        // list so it shows up in the dropdown.
        if (isDeep) void loadRuns();
      } catch (err) {
        // 429 = deep rate-limit → soft toast, don't wipe the drawer.
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (isDeep && status === 429) {
          showToast.error(
            'Test rate-limited',
            'Please wait about a minute before running the test again.',
          );
        } else {
          handleApiError(err);
        }
      } finally {
        if (isDeep) setDeepRunning(false);
        else setLoading(false);
      }
    },
    [agentId, applyReport, configId, loadRuns, runReadiness, trigger],
  );

  // Open: adopt the parent report (matches the badge) or fetch Shallow. Close:
  // clear only local state so the parent keeps its report for the next open.
  useEffect(() => {
    if (open && agentId) {
      if (initialReport) {
        setReport(initialReport);
      } else {
        void load('shallow');
      }
      return;
    }
    if (!open) setReport(null);
  }, [open, agentId, configId, load, initialReport]);

  // Load the history list + reset selection on open/close. NOT scoped to
  // configId — history spans all versions, so a version switch mustn't refetch
  // the list or eject the user from the run they're viewing.
  useEffect(() => {
    if (open && agentId) {
      historyReqIdRef.current += 1; // invalidate any in-flight history fetch
      setHistory(null);
      void loadRuns();
      return;
    }
    if (!open) {
      historyReqIdRef.current += 1;
      setRuns([]);
      setHistory(null);
    }
  }, [open, agentId, loadRuns]);

  const handleSelectRun = useCallback(
    (id: string | number | null) => {
      // Every selection (including the "Latest" sentinel) bumps the request id
      // so a slower fetch from a previous pick can't land late and clobber it.
      const reqId = (historyReqIdRef.current += 1);
      // Sentinel → back to the live report.
      if (id === null) {
        setHistory(null);
        return;
      }
      if (!agentId) return;
      const runNumber = Number(id);
      // Clear the prior report immediately (report: null) so the drawer shows a
      // loader — never the previous run's checks under the new run's label.
      setHistory({ runNumber, report: null });
      void (async () => {
        try {
          const r = await fetchRun({ agentId, runNumber });
          if (historyReqIdRef.current !== reqId) return; // superseded by a newer pick
          setHistory({ runNumber, report: r });
        } catch (err) {
          if (historyReqIdRef.current !== reqId) return;
          handleApiError(err);
          setHistory(null);
        }
      })();
    },
    [agentId, fetchRun],
  );

  // The report actually rendered: the selected past run, or the live report.
  const shown = viewingHistory ? (history?.report ?? null) : report;
  const overallStatus = shown?.overall_status;
  // In history view the report is null until the fetch resolves → show the loader.
  const showingLoader = viewingHistory ? !history?.report : loading && !report;

  // Run-history select props (options + rich renderers) live in a hook so this
  // component stays JSX-only.
  const runSelect = useRunHistorySelect({
    runs,
    selectedRunNumber,
    liveReport: report,
    configId,
    onSelect: handleSelectRun,
  });

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title="Agent readiness"
      description="A pre-flight check across every part of this agent — providers, prompt, tools, phone routing, and more."
      width="sm:max-w-[520px]"
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          {showingLoader ? (
            <ReadinessBadge status="loading" size="md" />
          ) : shown && overallStatus ? (
            <ReadinessBadge
              status={overallStatus}
              blockerCount={shown.summary.blockers}
              warningCount={shown.summary.warnings}
              size="md"
            />
          ) : (
            <ReadinessBadge status="error" size="md" />
          )}

          <div className="flex items-center gap-1.5">
            {(runsLoading || runs.length > 0) && (
              <SelectInput
                name="readiness-run-history"
                loading={runsLoading}
                size="sm"
                className="w-32"
                // `!h-7` beats SelectTrigger's `data-[size=sm]:h-8`; the rest
                // matches the adjacent toolbar buttons (h-7 · px-2 · 11px).
                triggerClassName="!h-7 gap-1 px-2 text-[11px]"
                // popper (not the default item-aligned) so the menu anchors
                // below the trigger and isn't mis-positioned inside the drawer's
                // scroll container.
                position="popper"
                {...runSelect}
              />
            )}
            <CustomButton
              type="text"
              size="xs"
              icon={<RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />}
              // Not forced: re-reads the newest snapshot (the deep one, via the
              // shallow-accepts-deep fast-path) and only re-runs when the
              // dependency stamp changed. Forcing here would persist a shallow
              // event that never shows in the deep-only history and would
              // supersede a fresh deep result, resetting the badge to "ready".
              onClick={() => void load('shallow', 'editor_load')}
              disabled={loading || deepRunning || viewingHistory || !agentId}
              className="h-7 px-2 text-[11px]"
            >
              Refresh
            </CustomButton>
            <CustomButton
              type="default"
              size="xs"
              icon={<Beaker className="size-3.5" />}
              onClick={() => void load('deep', 'test_button', true)}
              loading={deepRunning}
              disabled={loading || viewingHistory || !agentId}
              className="h-7 px-2 text-[11px]"
            >
              Run deep test
            </CustomButton>
          </div>
        </div>

        {viewingHistory && (
          <div className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/30 px-2.5 py-1.5 text-[11px] text-muted-foreground">
            <span>Viewing run #{selectedRunNumber} (read-only)</span>
            <CustomButton
              type="text"
              size="xs"
              onClick={() => handleSelectRun(null)}
              className="h-6 px-2 text-[11px]"
            >
              Back to latest
            </CustomButton>
          </div>
        )}

        {shown && (
          <div className="flex gap-3 text-[11px] text-muted-foreground">
            <span>
              {countLabel(shown.summary.blockers, 'blocker', 'blockers')} ·{' '}
              {countLabel(shown.summary.warnings, 'warning', 'warnings')} ·{' '}
              {countLabel(shown.summary.passed, 'pass', 'passing')}
              {shown.summary.skipped > 0 && ` · ${shown.summary.skipped} skipped`}
            </span>
            <span aria-hidden>·</span>
            <span title={shown.generated_at ? formatDate(shown.generated_at) : undefined}>
              {viewingHistory
                ? `Checked ${formatRelative(shown.generated_at)}`
                : 'Checked just now'}
            </span>
          </div>
        )}

        {showingLoader ? (
          <p className="py-8 text-center text-[13px] text-muted-foreground">Checking…</p>
        ) : shown ? (
          <ReadinessCheckList checks={shown.checks} />
        ) : (
          <div className="space-y-3 py-4 text-center">
            <p className="text-[13px] text-muted-foreground">Readiness unavailable.</p>
            <CustomButton type="default" size="sm" onClick={() => void load('shallow')}>
              Retry
            </CustomButton>
          </div>
        )}
      </div>
    </CustomDrawer>
  );
}
