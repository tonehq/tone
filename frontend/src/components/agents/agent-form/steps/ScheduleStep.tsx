'use client';

import ScheduledCallsPage from '@/components/scheduled-calls/ScheduledCallsPage';

// Agent-scoped Schedule tab inside the editor. Renders the same scheduled-calls table +
// create modal as the (removed) global page, but scoped to this agent via `agentId` — the
// list filters on it and the create modal locks the agent. Edit-only + outbound-gated: a
// not-yet-created or inbound-only agent renders nothing (also hidden in the rail).
export default function ScheduleStep({ agentId }: { agentId: string | null }) {
  if (!agentId) return null;
  return <ScheduledCallsPage agentId={agentId} />;
}
