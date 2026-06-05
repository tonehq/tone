'use client';

import { useParams } from 'next/navigation';

import AgentSectionBody from '@/components/agents/AgentSectionBody';

export default function EditAgentSection() {
  const params = useParams();
  const type = params?.type as string;
  const id = params?.id as string;
  const section = (params?.section as string) ?? 'overview';

  return (
    <AgentSectionBody section={section} agentId={id} basePath={`/agents/edit/${type}/${id}`} />
  );
}
