'use client';

import { Braces } from 'lucide-react';
import { useState } from 'react';

import ProfileVariablesPanel from '@/components/agents/profile-variables/ProfileVariablesPanel';
import CustomButton from '@/components/shared/CustomButton';
import CustomDrawer from '@/components/shared/CustomDrawer';

/**
 * "Profile variables" trigger button + right-side drawer — a convenience entry
 * point on the **workflow builder** canvas so the `{{profile.<key>}}` values
 * can be managed without leaving the pathway being authored. The agent editor
 * hosts the same feature in its **Advanced** tab; both render the shared
 * `ProfileVariablesPanel`, so they never drift.
 *
 * Self-contained (owns its open state) so any authoring surface can drop it in
 * with just `agentId`.
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
        <ProfileVariablesPanel agentId={agentId} />
      </CustomDrawer>
    </>
  );
}
