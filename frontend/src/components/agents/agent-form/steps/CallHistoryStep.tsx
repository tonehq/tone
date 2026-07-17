'use client';

import CallHistory from '@/components/call-history/CallHistory';

// Agent-scoped Call History tab inside the editor. Renders the exact same table,
// filters, and metrics as the global page, scoped to this agent via the
// `agentId` prop. Edit-only: a not-yet-created agent has no calls, so create
// mode passes `agentId === null` and this renders nothing (the section is also
// hidden in the rail and bounced by AgentSectionBody's `known` guard).
export default function CallHistoryStep({ agentId }: { agentId: string | null }) {
  if (!agentId) return null;
  return <CallHistory agentId={agentId} />;
}
