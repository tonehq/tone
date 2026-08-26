'use client';

import { Braces } from 'lucide-react';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import ProfileVariablesManager from '@/components/agents/profile-variables/ProfileVariablesManager';

/**
 * Profile Variables tab — sidebar entry point for per-agent
 * `{{profile.<key>}}` placeholders. Renders in BOTH create and edit modes:
 * `ProfileVariablesManager` internally routes API calls (edit mode) vs RHF
 * drafts (create mode) so there's one CRUD implementation for both flows.
 */
export default function ProfileStep({ agentId }: { agentId: string | null }) {
  return (
    <SectionCard
      icon={<Braces className="size-3.5" strokeWidth={2.25} />}
      iconClassName={ACCENTS.indigo}
      title="Profile variables"
      description="Reusable values referenced anywhere as {{profile.<key>}} — prompt, workflow nodes, and more. Update once, applied everywhere on the next call."
    >
      <ProfileVariablesManager agentId={agentId} />
    </SectionCard>
  );
}
