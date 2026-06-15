'use client';

import { Loader2, Radio, Save } from 'lucide-react';

import { CustomButton, CustomTooltip } from '@/components/shared';

export type AgentSaveAction = 'save' | 'publish';

interface AgentSaveActionsProps {
  /** `create` mode shows a single "Create agent" button. `edit` mode shows
   *  Save + Publish as two distinct top-level buttons. */
  mode: 'create' | 'edit';
  /** True when at least one draft (non-published) version exists. Drives
   *  whether the Publish toolbar button is enabled — clicking opens a picker
   *  the user uses to choose which draft to promote. */
  canPublish: boolean;
  saving: boolean;
  publishing: boolean;
  onAction: (action: AgentSaveAction) => void;
}

const ICON_CLASS = 'size-3.5';
const SPINNER = <Loader2 className={`${ICON_CLASS} animate-spin`} />;

/**
 * Primary action area for the agent editor toolbar.
 *
 * - **create** mode: one "Create agent" button.
 * - **edit** mode: two clearly-separated buttons — **Save** (always creates a
 *   new draft version) and **Publish** (opens the version picker modal; the
 *   parent renders the modal). Publish is disabled when there are no drafts
 *   to promote.
 */
export default function AgentSaveActions({
  mode,
  canPublish,
  saving,
  publishing,
  onAction,
}: AgentSaveActionsProps) {
  if (mode === 'create') {
    return (
      <CustomButton
        type="primary"
        size="sm"
        icon={saving ? SPINNER : <Save className={ICON_CLASS} />}
        onClick={() => onAction('save')}
        loading={saving}
        className="h-8"
      >
        Create agent
      </CustomButton>
    );
  }

  // Disable both while either is in-flight — the form mutates the same agent
  // and a Save + Publish race would surface confusing intermediate state.
  const busy = saving || publishing;
  const publishDisabled = busy || !canPublish;
  const publishTooltip = !canPublish ? 'No drafts to publish — click Save to create one.' : null;

  return (
    <div className="flex items-center gap-1.5">
      <CustomButton
        type="default"
        size="sm"
        icon={saving ? SPINNER : <Save className={ICON_CLASS} />}
        onClick={() => onAction('save')}
        loading={saving}
        disabled={busy}
        className="h-8"
      >
        Save
      </CustomButton>
      <PublishButton
        publishing={publishing}
        disabled={publishDisabled}
        tooltip={publishTooltip}
        onClick={() => onAction('publish')}
      />
    </div>
  );
}

interface PublishButtonProps {
  publishing: boolean;
  disabled: boolean;
  tooltip: string | null;
  onClick: () => void;
}

/** Publish button extracted so the tooltip-vs-bare-button branch stays local
 *  to the one place that needs it. */
function PublishButton({ publishing, disabled, tooltip, onClick }: PublishButtonProps) {
  const button = (
    <CustomButton
      type="primary"
      size="sm"
      icon={publishing ? SPINNER : <Radio className={ICON_CLASS} />}
      onClick={onClick}
      loading={publishing}
      disabled={disabled}
      className="h-8"
    >
      Publish
    </CustomButton>
  );

  // Radix tooltips don't surface for disabled buttons because pointer events
  // are off — wrap in a span so the trigger still receives hover.
  if (!tooltip) return button;
  return (
    <CustomTooltip content={tooltip}>
      <span className="inline-flex">{button}</span>
    </CustomTooltip>
  );
}
