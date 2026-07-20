/**
 * Pure presentation helpers for the readiness UI. Kept out of the components so
 * the drawer/list stay JSX-only and this logic is reusable and unit-testable.
 */

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
