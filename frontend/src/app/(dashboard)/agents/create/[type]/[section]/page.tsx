'use client';

import { useParams } from 'next/navigation';

import AgentSectionBody from '@/components/agents/AgentSectionBody';

export default function CreateAgentSection() {
  const params = useParams();
  const type = params?.type as string;
  const section = (params?.section as string) ?? 'basics';

  return <AgentSectionBody section={section} agentId={null} basePath={`/agents/create/${type}`} />;
}
