'use client';

import { CheckCircle2, MinusCircle, XCircle } from 'lucide-react';

import type { EvalVerdict } from '@/types/eval';
import { cn } from '@/utils/cn';

import { VERDICT_COLOR, VERDICT_RING } from './verdictColors';

const verdictMeta: Record<EvalVerdict, { label: string; icon: React.ReactNode }> = {
  PASS: { label: 'Pass', icon: <CheckCircle2 className="size-3" /> },
  PARTIAL: { label: 'Partial', icon: <MinusCircle className="size-3" /> },
  FAIL: { label: 'Fail', icon: <XCircle className="size-3" /> },
};

export default function VerdictChip({ verdict }: { verdict: EvalVerdict }) {
  const meta = verdictMeta[verdict] ?? verdictMeta.FAIL;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        VERDICT_COLOR[verdict] ?? VERDICT_COLOR.FAIL,
        VERDICT_RING[verdict] ?? VERDICT_RING.FAIL,
      )}
    >
      {meta.icon}
      {meta.label}
    </span>
  );
}
