import type { AgentLlmEvalBatchStatus } from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';

import { RUN_STATUS_STYLES } from './constants';

export default function RunStatusChip({ status }: { status: AgentLlmEvalBatchStatus }) {
  const s = RUN_STATUS_STYLES[status] ?? RUN_STATUS_STYLES.pending;
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
