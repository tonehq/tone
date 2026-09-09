'use client';

import { Braces } from 'lucide-react';

import SectionCard from '@/components/agents/agent-form/SectionCard';
import ProfileVariablesPanel from '@/components/agents/profile-variables/ProfileVariablesPanel';

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
      description="Reusable values referenced anywhere as {{profile.<key>}} — prompt, workflow nodes, and more. Update once, applied everywhere on the next call."
    >
      <ProfileVariablesPanel agentId={agentId} />
    </SectionCard>
  );
}
