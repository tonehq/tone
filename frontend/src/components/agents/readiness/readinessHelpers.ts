/**
 * Pure presentation helpers for the readiness UI. Kept out of the components so
 * the drawer/list stay JSX-only and this logic is reusable and unit-testable.
 */

import type { ReadinessCategory, ReadinessCheckResult } from '@/types/readiness';

import { CATEGORY_ORDER, SEVERITY_RANK } from './readinessConstants';

/** One category block: failures first (always visible), then passing checks,
 * then skipped (collapsed by default in the UI). */
export interface CategoryGroup {
  category: ReadinessCategory;
  actionable: ReadinessCheckResult[];
  passed: ReadinessCheckResult[];
  skipped: ReadinessCheckResult[];
}

/** Group checks by category (fixed order from readinessConstants) and, within a
 * group, order failures by severity (BLOCKER → WARNING → INFO). Pure. */
export function buildGroups(checks: ReadinessCheckResult[]): CategoryGroup[] {
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

/** Human label for a run's trigger string, shown in the run-history select. */
export function triggerLabelFor(trigger: string): string {
  switch (trigger) {
    case 'test_button':
      return 'Deep test';
    case 'publish_gate':
      return 'Publish check';
    default:
      return 'Readiness check';
  }
}

/** Pluralised "N thing" label, e.g. `countLabel(1, 'blocker', 'blockers')`. */
export function countLabel(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}
