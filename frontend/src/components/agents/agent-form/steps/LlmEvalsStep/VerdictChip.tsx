import type { AgentLlmEvalVerdict } from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';

import { VERDICT_STYLES } from './constants';

export default function VerdictChip({
  verdict,
}: {
  verdict: AgentLlmEvalVerdict | null | undefined;
}) {
  const key = (verdict as AgentLlmEvalVerdict) ?? 'FAIL';
  const s = VERDICT_STYLES[key] ?? VERDICT_STYLES.FAIL;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        s.className,
      )}
    >
      {s.icon}
      {verdict ? s.label : '—'}
    </span>
  );
}
