'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import AgentOverview from '@/components/agents/agent-overview/AgentOverview';
import AiStep from '@/components/agents/agent-form/steps/AiStep';
import BasicsStep from '@/components/agents/agent-form/steps/BasicsStep';
import KnowledgePhoneStep from '@/components/agents/agent-form/steps/KnowledgePhoneStep';
import PromptStep from '@/components/agents/agent-form/steps/PromptStep';
import ToolsMcpStep from '@/components/agents/agent-form/steps/ToolsMcpStep';
import VoiceStep from '@/components/agents/agent-form/steps/VoiceStep';

// Maps a URL section segment to its body. Shared by the edit and create
// section routes; the editor's form state + chrome live in the layout
// (AgentEditorShell), so these are just the inner panels.
export default function AgentSectionBody({
  section,
  agentId,
  basePath,
}: {
  section: string;
  agentId: string | null;
  basePath: string;
}) {
  const router = useRouter();

  const isStep =
    section === 'basics' ||
    section === 'prompt' ||
    section === 'ai' ||
    section === 'voice' ||
    section === 'tools' ||
    section === 'knowledge';
  // Overview only exists for a saved agent (edit mode).
  const known = isStep || (section === 'overview' && !!agentId);

  // Bad/unknown section in the URL → bounce to a sensible default.
  useEffect(() => {
    if (!known) {
      router.replace(`${basePath}/${agentId ? 'overview' : 'basics'}`);
    }
  }, [known, router, basePath, agentId]);

  if (!known) return null;

  switch (section) {
    case 'overview':
      return <AgentOverview />;
    case 'basics':
      return <BasicsStep />;
    case 'prompt':
      return <PromptStep />;
    case 'ai':
      return <AiStep />;
    case 'voice':
      return <VoiceStep />;
    case 'tools':
      return <ToolsMcpStep />;
    case 'knowledge':
      return <KnowledgePhoneStep agentId={agentId} />;
    default:
      return null;
  }
}
