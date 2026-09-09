'use client';

import ProfileVariablesManager from '@/components/agents/profile-variables/ProfileVariablesManager';
import WebhookConfigSection from '@/components/agents/profile-variables/webhook/WebhookConfigSection';
import CollapsibleSection from '@/components/shared/CollapsibleSection';

/**
 * The profile-variables management content: the variables CRUD table (dual-mode
 * — API in edit, RHF drafts in create) plus the webhook data source. Shared by
 * the agent editor's **Advanced** tab (rendered inline) and the workflow-builder
 * drawer, so both surfaces stay in lockstep — the single source of truth for
 * this feature's UI.
 */
export default function ProfileVariablesPanel({ agentId }: { agentId: string | null }) {
  return (
    <>
      <ProfileVariablesManager agentId={agentId} />

      {agentId ? (
        <div className="mt-6">
          <CollapsibleSection
            title="Webhook data source"
            description="Call your endpoint at call start and fill webhook-sourced variables from the response."
            defaultExpanded={false}
          >
            <WebhookConfigSection agentId={agentId} />
          </CollapsibleSection>
        </div>
      ) : (
        <p className="mt-6 text-xs text-muted-foreground">
          Save the agent first to configure a webhook data source.
        </p>
      )}
    </>
  );
}
