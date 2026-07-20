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
import ChannelsStep from '@/components/agents/agent-form/steps/ChannelsStep';
import ContactsStep from '@/components/agents/agent-form/steps/ContactsStep';
import CallHistoryStep from '@/components/agents/agent-form/steps/CallHistoryStep';

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
    section === 'knowledge' ||
    section === 'channels';
  // Overview, Call History, and Contacts only exist for a saved agent (edit
  // mode) — Contacts (C-5) needs a persisted agent_id to assign against.
  const known =
    isStep ||
    ((section === 'overview' || section === 'call-history' || section === 'contacts') && !!agentId);

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
    case 'channels':
      return <ChannelsStep />;
    case 'contacts':
      return <ContactsStep agentId={agentId} />;
    case 'call-history':
      return <CallHistoryStep agentId={agentId} />;
    default:
      return null;
  }
}
