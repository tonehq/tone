'use client';

import { useState } from 'react';

import { CustomButton } from '@/components/shared';
import { cn } from '@/utils/cn';

import ReadinessCheckRow from './ReadinessCheckRow';
import { CATEGORY_LABEL } from './readinessConstants';
import { countLabel, type CategoryGroup } from './readinessHelpers';

interface CategorySectionProps {
  group: CategoryGroup;
}

/**
 * One category block in the readiness drawer: a header with a failure summary,
 * then the actionable (failing) rows, the passing rows, and a collapsed
 * disclosure for skipped checks so "everything is fine" doesn't drown out the
 * actionable rows.
 */
export default function CategorySection({ group }: CategorySectionProps) {
  const [showSkipped, setShowSkipped] = useState(false);

  const failCounts = group.actionable.reduce(
    (acc, c) => {
      acc[c.severity] = (acc[c.severity] ?? 0) + 1;
      return acc;
    },
    { blocker: 0, warning: 0, info: 0 } as Record<string, number>,
  );

  const summaryBits: string[] = [];
  if (failCounts.blocker) summaryBits.push(countLabel(failCounts.blocker, 'blocker', 'blockers'));
  if (failCounts.warning) summaryBits.push(countLabel(failCounts.warning, 'warning', 'warnings'));
  if (failCounts.info) summaryBits.push(countLabel(failCounts.info, 'suggestion', 'suggestions'));
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
