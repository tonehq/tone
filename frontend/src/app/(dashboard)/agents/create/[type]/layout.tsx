import { redirect } from 'next/navigation';

import AgentEditorShell from '@/components/agents/AgentEditorShell';
import type { AgentDirection } from '@/types/agent';

export default async function CreateAgentLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ type: string }>;
}) {
  const { type } = await params;
  const t = type?.toLowerCase();
  if (t !== 'inbound' && t !== 'outbound') {
    redirect('/agents');
  }

  return <AgentEditorShell agentType={t as AgentDirection}>{children}</AgentEditorShell>;
}
