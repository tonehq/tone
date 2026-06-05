import AgentEditorShell from '@/components/agents/AgentEditorShell';
import type { AgentDirection } from '@/types/agent';

export default async function EditAgentLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ type: string; id: string }>;
}) {
  const { type, id } = await params;
  const t = type?.toLowerCase();
  const agentType: AgentDirection =
    t === 'outbound' ? 'outbound' : t === 'both' ? 'both' : 'inbound';

  return (
    <AgentEditorShell agentType={agentType} agentId={id}>
      {children}
    </AgentEditorShell>
  );
}
