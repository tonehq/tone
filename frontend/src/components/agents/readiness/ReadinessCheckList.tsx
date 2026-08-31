'use client';

import { useMemo, useState } from 'react';

import { CustomButton } from '@/components/shared';
import type { ReadinessCategory, ReadinessCheckResult } from '@/types/readiness';
import { cn } from '@/utils/cn';

import ReadinessCheckRow from './ReadinessCheckRow';
import { CATEGORY_LABEL, CATEGORY_ORDER, SEVERITY_RANK } from './readinessConstants';

interface ReadinessCheckListProps {
  checks: ReadinessCheckResult[];
}

/**
 * Groups checks by category (fixed order from readinessConstants) and, within
 * a group, surfaces failures first (BLOCKER → WARNING → INFO) then passing
 * checks, then skipped. Skipped checks live inside a collapsed disclosure so
 * "everything is fine" doesn't drown out the actionable rows.
 */
export default function ReadinessCheckList({ checks }: ReadinessCheckListProps) {
  const groups = useMemo(() => buildGroups(checks), [checks]);

  if (checks.length === 0) {
    return (
      <p className="py-8 text-center text-[13px] text-muted-foreground">
        No checks ran — try refreshing.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <CategorySection key={group.category} group={group} />
      ))}
    </div>
  );
}

// ── one category block ──────────────────────────────────────────────────────

interface CategoryGroup {
  category: ReadinessCategory;
  actionable: ReadinessCheckResult[]; // failures — always visible
  passed: ReadinessCheckResult[]; // dimmed, always visible
  skipped: ReadinessCheckResult[]; // collapsed by default
}

function CategorySection({ group }: { group: CategoryGroup }) {
  const [showSkipped, setShowSkipped] = useState(false);

  const failCounts = group.actionable.reduce(
    (acc, c) => {
      acc[c.severity] = (acc[c.severity] ?? 0) + 1;
      return acc;
    },
    { blocker: 0, warning: 0, info: 0 } as Record<string, number>,
  );

  const summaryBits: string[] = [];
  if (failCounts.blocker)
    summaryBits.push(`${failCounts.blocker} blocker${plural(failCounts.blocker)}`);
  if (failCounts.warning)
    summaryBits.push(`${failCounts.warning} warning${plural(failCounts.warning)}`);
  if (failCounts.info) summaryBits.push(`${failCounts.info} suggestion${plural(failCounts.info)}`);
  if (summaryBits.length === 0 && group.passed.length > 0) {
    summaryBits.push('All checks passed');
  }

  return (
    <section>
      <header className="mb-2 flex items-baseline justify-between">
        <h3 className="text-[12px] font-semibold uppercase tracking-wide text-muted-foreground">
          {CATEGORY_LABEL[group.category]}
        </h3>
        {summaryBits.length > 0 && (
          <span
            className={cn(
              'text-[11px]',
              failCounts.blocker
                ? 'text-destructive'
                : failCounts.warning
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-muted-foreground',
            )}
          >
            {summaryBits.join(' · ')}
          </span>
        )}
      </header>

      <div className="space-y-1.5">
        {group.actionable.map((c) => (
          <ReadinessCheckRow key={c.check_id} check={c} />
        ))}
        {group.passed.map((c) => (
          <ReadinessCheckRow key={c.check_id} check={c} />
        ))}

        {group.skipped.length > 0 && (
          <div>
            <CustomButton
              type="text"
              size="xs"
              onClick={() => setShowSkipped((v) => !v)}
              className="h-6 px-2 text-[11px] text-muted-foreground"
            >
              {showSkipped ? 'Hide' : 'Show'} skipped ({group.skipped.length})
            </CustomButton>
            {showSkipped && (
              <div className="mt-1.5 space-y-1.5">
                {group.skipped.map((c) => (
                  <ReadinessCheckRow key={c.check_id} check={c} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

// ── grouping / sorting ──────────────────────────────────────────────────────

function buildGroups(checks: ReadinessCheckResult[]): CategoryGroup[] {
  const byCategory = new Map<ReadinessCategory, ReadinessCheckResult[]>();
  for (const check of checks) {
    const bucket = byCategory.get(check.category) ?? [];
    bucket.push(check);
    byCategory.set(check.category, bucket);
  }

  return CATEGORY_ORDER.filter((cat) => byCategory.has(cat)).map((category) => {
    const rows = byCategory.get(category) ?? [];
    return {
      category,
      actionable: rows
        .filter((c) => c.status === 'fail')
        .sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]),
      passed: rows.filter((c) => c.status === 'pass'),
      skipped: rows.filter((c) => c.status === 'skipped'),
    };
  });
}

function plural(n: number): string {
  return n === 1 ? '' : 's';
}
