'use client';

import { Braces } from 'lucide-react';
import { useState } from 'react';

import ProfileVariablesManager from '@/components/agents/profile-variables/ProfileVariablesManager';
import CustomButton from '@/components/shared/CustomButton';
import CustomDrawer from '@/components/shared/CustomDrawer';

/**
 * "Profile variables" trigger button + right-side drawer.
 *
 * Replaces the old Profile editor tab: the same dual-mode
 * `ProfileVariablesManager` (API in edit mode, RHF drafts in create mode) now
 * opens inline from the Prompt / Workflow authoring surface, so the
 * `{{profile.<key>}}` values can be managed without leaving the page the user
 * is writing on.
 *
 * Self-contained (owns its open state) so any authoring surface can drop it in
 * with just `agentId` — the Prompt step and the workflow builder toolbar both
 * reuse this one component instead of re-wiring a drawer each.
 */
export default function ProfileVariablesDrawer({ agentId }: { agentId: string | null }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <CustomButton
        type="default"
        size="sm"
        onClick={() => setOpen(true)}
        icon={<Braces className="size-3.5" />}
      >
        Profile variables
      </CustomButton>

      <CustomDrawer
        open={open}
        onClose={() => setOpen(false)}
        side="right"
        width="w-full sm:max-w-2xl"
        title="Profile variables"
        description="Reusable values referenced anywhere as {{profile.<key>}} — prompt, workflow nodes, and more. Update once, applied everywhere on the next call."
      >
        <ProfileVariablesManager agentId={agentId} />
      </CustomDrawer>
    </>
  );
}
