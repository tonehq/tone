import type { AgentLlmEvalVerdict } from '@/types/agentLlmEval';

import { VERDICT_STYLES } from './constants';
import StatusPill from './StatusPill';

export default function VerdictChip({
  verdict,
}: {
  verdict: AgentLlmEvalVerdict | null | undefined;
}) {
  const key = (verdict as AgentLlmEvalVerdict) ?? 'FAIL';
  const s = VERDICT_STYLES[key] ?? VERDICT_STYLES.FAIL;
  return <StatusPill icon={s.icon} label={verdict ? s.label : '—'} className={s.className} />;
}
