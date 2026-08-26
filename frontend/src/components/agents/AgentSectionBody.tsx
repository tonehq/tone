'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import AgentOverview from '@/components/agents/agent-overview/AgentOverview';
import AiStep from '@/components/agents/agent-form/steps/AiStep';
import BasicsStep from '@/components/agents/agent-form/steps/BasicsStep';
import KnowledgePhoneStep from '@/components/agents/agent-form/steps/KnowledgePhoneStep';
import ProfileStep from '@/components/agents/agent-form/steps/ProfileStep';
import PromptStep from '@/components/agents/agent-form/steps/PromptStep';
import ToolsMcpStep from '@/components/agents/agent-form/steps/ToolsMcpStep';
import VoiceStep from '@/components/agents/agent-form/steps/VoiceStep';
import ChannelsStep from '@/components/agents/agent-form/steps/ChannelsStep';
import ContactsStep from '@/components/agents/agent-form/steps/ContactsStep';
import ScheduleStep from '@/components/agents/agent-form/steps/ScheduleStep';
import CallHistoryStep from '@/components/agents/agent-form/steps/CallHistoryStep';
import LlmEvalsStep from '@/components/agents/agent-form/steps/LlmEvalsStep';

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
    section === 'setup' ||
    section === 'profile' || // available in both modes — create-mode uses local drafts
    section === 'prompt' ||
    section === 'voice' ||
    section === 'tools' ||
    section === 'knowledge' ||
    section === 'channels' ||
    // LLM Evals renders in both modes — an empty "save the agent first"
    // state in create mode, real UI once agent_id is persisted.
    section === 'llm-evals';
  // Call History, Contacts, and Schedule only exist for a saved agent
  // (edit mode) — they need a persisted agent_id to scope against.
  const known =
    isStep ||
    ((section === 'call-history' || section === 'contacts' || section === 'schedule') && !!agentId);

  // Legacy URLs (`/basics`, `/ai`, `/overview`) still land users on the merged
  // Setup page instead of 404-bouncing to the default.
  const legacySetupSection = section === 'basics' || section === 'ai' || section === 'overview';

  // Bad/unknown section in the URL → bounce to a sensible default; legacy
  // sections → redirect to `/setup` so bookmarks and in-app links keep working.
  useEffect(() => {
    if (legacySetupSection) {
      router.replace(`${basePath}/setup`);
      return;
    }
    if (!known) {
      router.replace(`${basePath}/setup`);
    }
  }, [known, legacySetupSection, router, basePath]);

  if (!known) return null;

  switch (section) {
    case 'setup':
      // Overview is a saved-agent read-only summary — only render it in edit
      // mode. Basics and AI are the write inputs and render in both modes.
      return (
        <div className="flex flex-col gap-6">
          {agentId && <AgentOverview />}
          <BasicsStep />
          <AiStep />
        </div>
      );
    case 'profile':
      return <ProfileStep agentId={agentId} />;
    case 'prompt':
      return <PromptStep />;
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
    case 'schedule':
      return <ScheduleStep agentId={agentId} />;
    case 'call-history':
      return <CallHistoryStep agentId={agentId} />;
    case 'llm-evals':
      return <LlmEvalsStep agentId={agentId} />;
    default:
      return null;
  }
}
