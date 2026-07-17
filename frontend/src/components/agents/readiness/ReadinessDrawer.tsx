'use client';

import { useAtom } from 'jotai';
import { Beaker, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { fetchAgentReadinessAtom } from '@/atoms/ReadinessAtom';
import { CustomButton, CustomDrawer } from '@/components/shared';
import type { ReadinessCheckResult, ReadinessReport, ReadinessTrigger } from '@/types/readiness';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ReadinessBadge from './ReadinessBadge';
import ReadinessCheckList from './ReadinessCheckList';

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
  /** Lets the drawer inform the parent when the report changes (Refresh /
   * Run deep test) so the badge and the drawer stay in sync afterwards. */
  onReportChange?: (report: ReadinessReport | null) => void;
}

/**
 * Right-side drawer holding the full readiness report. Renders any
 * ``initialReport`` supplied by the parent on open (so the badge and the
 * drawer never disagree); falls back to a fresh Shallow fetch when the
 * parent has nothing to hand off. User can escalate to Deep via the "Run
 * deep test" button. Deep-links inside failing rows navigate the user to
 * the fix page.
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
  const router = useRouter();
  const [, runReadiness] = useAtom(fetchAgentReadinessAtom);

  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [deepRunning, setDeepRunning] = useState(false);

  /** Single point where local report state changes, so parent notification
   * stays consistent across all update paths (initial-adopt / refresh /
   * deep-test / close-clear). */
  const applyReport = useCallback(
    (next: ReadinessReport | null) => {
      setReport(next);
      onReportChange?.(next);
    },
    [onReportChange],
  );

  const load = useCallback(
    async (depth: 'shallow' | 'deep', why: ReadinessTrigger | string = trigger) => {
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
        });
        applyReport(next);
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
    [agentId, applyReport, configId, runReadiness, trigger],
  );

  // Open: adopt the parent-provided report when present (matches the badge);
  // else fetch a fresh Shallow report. Close: clear ONLY local state so the
  // parent keeps its report for the next open; if we nulled the parent too,
  // close-and-reopen would lose the deep report from a preceding save and
  // fall back to a shallow refetch that disagrees with the badge again.
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

  const handleFix = useCallback(
    (check: ReadinessCheckResult) => {
      if (!check.deep_link) return;
      onClose();
      router.push(check.deep_link);
    },
    [onClose, router],
  );

  const overallStatus = report?.overall_status;

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
          {loading && !report ? (
            <ReadinessBadge status="loading" size="md" />
          ) : report && overallStatus ? (
            <ReadinessBadge
              status={overallStatus}
              blockerCount={report.summary.blockers}
              warningCount={report.summary.warnings}
              size="md"
            />
          ) : (
            <ReadinessBadge status="error" size="md" />
          )}

          <div className="flex items-center gap-1.5">
            <CustomButton
              type="text"
              size="xs"
              icon={<RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />}
              onClick={() => void load('shallow', 'editor_load')}
              disabled={loading || deepRunning || !agentId}
              className="h-7 px-2 text-[11px]"
            >
              Refresh
            </CustomButton>
            <CustomButton
              type="default"
              size="xs"
              icon={<Beaker className="size-3.5" />}
              onClick={() => void load('deep', 'test_button')}
              loading={deepRunning}
              disabled={loading || !agentId}
              className="h-7 px-2 text-[11px]"
            >
              Run deep test
            </CustomButton>
          </div>
        </div>

        {report && (
          <div className="flex gap-3 text-[11px] text-muted-foreground">
            <span>
              {countLabel(report.summary.blockers, 'blocker', 'blockers')} ·{' '}
              {countLabel(report.summary.warnings, 'warning', 'warnings')} ·{' '}
              {countLabel(report.summary.passed, 'pass', 'passing')}
            </span>
            <span aria-hidden>·</span>
            <span title={report.generated_at}>Checked just now</span>
          </div>
        )}

        {loading && !report ? (
          <p className="py-8 text-center text-[13px] text-muted-foreground">Checking…</p>
        ) : report ? (
          <ReadinessCheckList checks={report.checks} onFix={handleFix} />
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

function countLabel(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}
