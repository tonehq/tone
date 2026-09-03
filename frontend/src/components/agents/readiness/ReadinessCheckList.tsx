'use client';

import { useMemo } from 'react';

import type { ReadinessCheckResult } from '@/types/readiness';

import CategorySection from './CategorySection';
import { buildGroups } from './readinessHelpers';

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
