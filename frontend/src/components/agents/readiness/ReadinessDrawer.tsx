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
}

/**
 * Right-side drawer holding the full readiness report. Fetches a fresh
 * Shallow report on open; user can escalate to Deep via the "Test agent"
 * button. Deep-links inside failing rows navigate the user to the fix page.
 */
export default function ReadinessDrawer({
  open,
  onClose,
  agentId,
  configId,
  trigger = 'editor_load',
}: ReadinessDrawerProps) {
  const router = useRouter();
  const [, runReadiness] = useAtom(fetchAgentReadinessAtom);

  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [deepRunning, setDeepRunning] = useState(false);

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
        setReport(next);
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
    [agentId, configId, runReadiness, trigger],
  );

  // Load Shallow on open; clear on close so re-opening for another agent
  // doesn't flash a stale report.
  useEffect(() => {
    if (open && agentId) {
      void load('shallow');
      return;
    }
    if (!open) setReport(null);
  }, [open, agentId, configId, load]);

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
