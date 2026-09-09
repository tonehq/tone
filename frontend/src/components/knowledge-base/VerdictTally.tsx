'use client';

import type { EvalVerdict } from '@/types/eval';

import { VERDICT_COLOR } from './verdictColors';

// Compact pass / partial / fail count pills, using the shared verdict colour
// map (same language as VerdictChip). Used in the compare column headers so the
// verdict spread reads at a glance instead of as a run-on
// "8 pass · 2 partial · 0 fail" line.
interface VerdictTallyProps {
  verdicts: Record<string, number>;
}

const TALLY: { key: EvalVerdict; label: string }[] = [
  { key: 'PASS', label: 'pass' },
  { key: 'PARTIAL', label: 'partial' },
  { key: 'FAIL', label: 'fail' },
];

export default function VerdictTally({ verdicts }: VerdictTallyProps) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-1">
      {TALLY.map((t) => (
        <span
          key={t.key}
          className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] font-medium ${VERDICT_COLOR[t.key]}`}
        >
          {verdicts[t.key] ?? 0} {t.label}
        </span>
      ))}
    </div>
  );
}
