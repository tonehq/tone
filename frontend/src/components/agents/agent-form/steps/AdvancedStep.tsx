'use client';

import { Braces } from 'lucide-react';

import SectionCard from '@/components/agents/agent-form/SectionCard';
import ProfileVariablesPanel from '@/components/agents/profile-variables/ProfileVariablesPanel';
import { PROFILE_VARIABLES_DESCRIPTION } from '@/constants/profileWebhook';

/**
 * The agent editor's "Advanced" section. Currently hosts the profile-variables
 * feature — the `{{profile.<key>}}` values (CRUD) and their webhook data
 * source — moved here from the Prompt step's drawer. Renders the shared
 * `ProfileVariablesPanel` (same content the workflow-builder drawer uses).
 */
export default function AdvancedStep({ agentId }: { agentId: string | null }) {
  return (
    <SectionCard
      icon={<Braces className="size-3.5" strokeWidth={2.25} />}
      tone="violet"
      title="Profile variables"
      description={PROFILE_VARIABLES_DESCRIPTION}
    >
      <ProfileVariablesPanel agentId={agentId} />
    </SectionCard>
  );
}
