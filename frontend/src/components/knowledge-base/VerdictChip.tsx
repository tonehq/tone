'use client';

import { CheckCircle2, MinusCircle, XCircle } from 'lucide-react';

import type { EvalVerdict } from '@/types/eval';
import { cn } from '@/utils/cn';

const verdictStyle: Record<
  EvalVerdict,
  { label: string; className: string; icon: React.ReactNode }
> = {
  PASS: {
    label: 'Pass',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  PARTIAL: {
    label: 'Partial',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <MinusCircle className="size-3" />,
  },
  FAIL: {
    label: 'Fail',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

export default function VerdictChip({ verdict }: { verdict: EvalVerdict }) {
  const s = verdictStyle[verdict] ?? verdictStyle.FAIL;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        s.className,
      )}
    >
      {s.icon}
      {s.label}
    </span>
  );
}
