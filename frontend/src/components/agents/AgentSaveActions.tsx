'use client';

import { GitBranchPlus, LayoutTemplate, Loader2, Radio, Save } from 'lucide-react';

import { CustomButton, CustomTooltip } from '@/components/shared';

export type AgentSaveAction = 'save' | 'publish' | 'create-version' | 'save-as-template';

interface AgentSaveActionsProps {
  /** `create` mode shows a single "Create agent" button. `edit` mode shows
   *  Save + Create version + Save as template + Publish as distinct top-level
   *  buttons. */
  mode: 'create' | 'edit';
  /** True when at least one draft (non-published) version exists. Drives
   *  whether the Publish toolbar button is enabled — clicking opens a picker
   *  the user uses to choose which draft to promote. */
  canPublish: boolean;
  saving: boolean;
  publishing: boolean;
  /** True while the create-version dialog is mid-call. Disables every action
   *  so the form can't be raced against the in-flight write. */
  creatingVersion: boolean;
  onAction: (action: AgentSaveAction) => void;
}

const ICON_CLASS = 'size-3.5';
const SPINNER = <Loader2 className={`${ICON_CLASS} animate-spin`} />;

/**
 * Primary action area for the agent editor toolbar.
 *
 * - **create** mode: one "Create agent" button.
 * - **edit** mode: four buttons — **Save** (mutates the loaded version in
 *   place), **Create version** (opens a dialog to copy from or start fresh),
 *   **Save as template** (opens a dialog to snapshot the live config as a
 *   reusable template), and **Publish** (opens the version picker modal).
 *   Publish is disabled when there are no drafts to promote.
 */
export default function AgentSaveActions({
  mode,
  canPublish,
  saving,
  publishing,
  creatingVersion,
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

  // Disable every action while any of them is in-flight — the form mutates
  // the same agent and racing them would surface confusing intermediate state.
  const busy = saving || publishing || creatingVersion;
  const publishDisabled = busy || !canPublish;
  const publishTooltip = !canPublish ? 'No drafts to publish — create a version first.' : null;

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
      <CustomButton
        type="default"
        size="sm"
        icon={creatingVersion ? SPINNER : <GitBranchPlus className={ICON_CLASS} />}
        onClick={() => onAction('create-version')}
        loading={creatingVersion}
        disabled={busy}
        className="h-8"
      >
        Create version
      </CustomButton>
      <CustomButton
        type="default"
        size="sm"
        icon={<LayoutTemplate className={ICON_CLASS} />}
        onClick={() => onAction('save-as-template')}
        disabled={busy}
        className="h-8"
      >
        Save as template
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
