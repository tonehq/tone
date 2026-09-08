import type { AgentLlmEvalVersionStatus } from '@/types/agentLlmEval';

import { VERSION_STATUS_STYLES } from './constants';
import StatusPill from './StatusPill';

// Chip surfaced next to the version selector while a background generation
// runs (spinner + "Generating…") or after it fails. Steady states (draft /
// finalized) have no entry in ``VERSION_STATUS_STYLES`` and render nothing,
// so the bar stays uncluttered once a version is settled.
export default function VersionStatusChip({ status }: { status: AgentLlmEvalVersionStatus }) {
  const s = VERSION_STATUS_STYLES[status];
  if (!s) return null;
  return <StatusPill icon={s.icon} label={s.label} className={s.className} />;
}
