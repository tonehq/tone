'use client';

import { ThumbsDown, ThumbsUp } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import type { HumanVerdict } from '@/types/eval';
import { cn } from '@/utils/cn';

import { HUMAN_VERDICT_COLOR } from './verdictColors';

interface HumanVerdictControlProps {
  value: HumanVerdict | null;
  disabled?: boolean;
  // Called with the new mark; passing the current mark again clears it (null).
  onSet: (verdict: HumanVerdict | null) => void;
}

// Two toggles for the human Accept/Reject ground-truth mark on one scored
// answer. Clicking the active mark again clears it. Reuses the shared verdict
// colour language (accept = emerald / PASS, reject = destructive / FAIL).
export default function HumanVerdictControl({ value, disabled, onSet }: HumanVerdictControlProps) {
  const handleAccept = () => onSet(value === 'accept' ? null : 'accept');
  const handleReject = () => onSet(value === 'reject' ? null : 'reject');

  return (
    <div className="flex items-center justify-center gap-1">
      <CustomButton
        type="text"
        size="icon-xs"
        aria-label="Accept"
        aria-pressed={value === 'accept'}
        disabled={disabled}
        onClick={handleAccept}
        className={cn(value === 'accept' && HUMAN_VERDICT_COLOR.accept)}
        icon={<ThumbsUp className="size-3.5" />}
      />
      <CustomButton
        type="text"
        size="icon-xs"
        aria-label="Reject"
        aria-pressed={value === 'reject'}
        disabled={disabled}
        onClick={handleReject}
        className={cn(value === 'reject' && HUMAN_VERDICT_COLOR.reject)}
        icon={<ThumbsDown className="size-3.5" />}
      />
    </div>
  );
}
