'use client';

import { Eye } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import { formatRatioPercent } from '@/utils/evalFormat';

import VerdictTally from './VerdictTally';

interface CompareColumnHeaderProps {
  name: string;
  runNumber: number;
  judgeModel: string | null;
  verdicts: Record<string, number>;
  isBaseline: boolean;
  // How often this judge agreed with the human labels (0..1), and how many
  // answers carry a mark. labeledCount === 0 ⇒ "no labels yet".
  humanAgreement: number | null;
  labeledCount: number;
  onViewPrompt: () => void;
}

// One compare column's header: config name + run, an optional baseline badge, the
// judge model as a mono chip, a verdict tally, and a subtle "View prompt" action.
// Replaces the cramped stacked-text header so the hierarchy is legible.
export default function CompareColumnHeader({
  name,
  runNumber,
  judgeModel,
  verdicts,
  isBaseline,
  humanAgreement,
  labeledCount,
  onViewPrompt,
}: CompareColumnHeaderProps) {
  return (
    <div className="flex flex-col items-center gap-1.5 py-1">
      <div className="flex items-center gap-1.5">
        <span className="text-sm font-semibold text-foreground">{name}</span>
        <span className="text-xs font-normal text-muted-foreground">#{runNumber}</span>
        {isBaseline && (
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
            Baseline
          </span>
        )}
      </div>
      <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] font-normal text-muted-foreground">
        {judgeModel ?? '—'}
      </span>
      <VerdictTally verdicts={verdicts} />
      <span className="text-[11px] text-muted-foreground">
        {labeledCount === 0
          ? 'no labels yet'
          : `agrees with you: ${formatRatioPercent(humanAgreement)}`}
      </span>
      <CustomButton
        type="text"
        size="xs"
        icon={<Eye className="size-3.5" />}
        onClick={onViewPrompt}
      >
        View prompt
      </CustomButton>
    </div>
  );
}
