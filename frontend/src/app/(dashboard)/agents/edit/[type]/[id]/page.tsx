'use client';

import AgentFormPage from '@/components/agents/AgentFormPage';
import { useParams } from 'next/navigation';

export default function EditAgentPage() {
  const params = useParams();
  const type = (params?.type as string)?.toLowerCase();
  const id = params?.id as string;
  const agentType = type === 'outbound' ? 'outbound' : 'inbound';

  return <AgentFormPage agentType={agentType} agentId={id} />;
}
