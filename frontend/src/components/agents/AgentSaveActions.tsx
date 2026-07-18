'use client';

import {
  Beaker,
  GitBranchPlus,
  LayoutTemplate,
  Loader2,
  MoreVertical,
  Radio,
  Save,
  Trash2,
} from 'lucide-react';

import { CustomButton, CustomTooltip } from '@/components/shared';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export type AgentSaveAction =
  | 'save'
  | 'publish'
  | 'create-version'
  | 'save-as-template'
  | 'test'
  | 'delete';

interface AgentSaveActionsProps {
  /** `create` mode shows a single "Create agent" button. `edit` mode shows
   *  Save as the only top-level button and moves Test, Create version, Save as
   *  template, Publish, and Delete into a three-dot overflow menu. */
  mode: 'create' | 'edit';
  /** True when at least one draft (non-published) version exists. Drives
   *  whether the Publish menu item is enabled — clicking opens a picker
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
const MENU_ICON_CLASS = 'size-4';
const SPINNER = <Loader2 className={`${ICON_CLASS} animate-spin`} />;

/**
 * Primary action area for the agent editor toolbar.
 *
 * - **create** mode: one "Create agent" button.
 * - **edit** mode: **Save** stays as a visible button; **Test**, **Create
 *   version**, **Save as template**, **Publish**, and **Delete** live in a
 *   three-dot overflow menu anchored to the right corner. Publish is disabled
 *   when there are no drafts to promote.
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

  const menuTrigger = (
    <CustomButton
      type="default"
      size="sm"
      icon={<MoreVertical className={MENU_ICON_CLASS} />}
      aria-label="More agent actions"
      className="h-8 w-8 p-0"
    />
  );

  return (
    <div className="flex items-center gap-3">
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
      <DropdownMenu>
        <DropdownMenuTrigger asChild>{menuTrigger}</DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onSelect={() => onAction('test')}>
            <Beaker className={MENU_ICON_CLASS} />
            Test
          </DropdownMenuItem>
          <DropdownMenuItem disabled={busy} onSelect={() => onAction('create-version')}>
            {creatingVersion ? (
              <Loader2 className={`${MENU_ICON_CLASS} animate-spin`} />
            ) : (
              <GitBranchPlus className={MENU_ICON_CLASS} />
            )}
            Create version
          </DropdownMenuItem>
          <DropdownMenuItem disabled={busy} onSelect={() => onAction('save-as-template')}>
            <LayoutTemplate className={MENU_ICON_CLASS} />
            Save as template
          </DropdownMenuItem>
          <PublishMenuItem
            disabled={publishDisabled}
            publishing={publishing}
            tooltip={publishTooltip}
            onSelect={() => onAction('publish')}
          />
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onSelect={() => onAction('delete')}>
            <Trash2 className={MENU_ICON_CLASS} />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

interface PublishMenuItemProps {
  disabled: boolean;
  publishing: boolean;
  tooltip: string | null;
  onSelect: () => void;
}

/** Publish row extracted so the disabled-tooltip branch stays local. Radix
 *  disabled menu items ignore pointer events, so we wrap in a tooltip trigger
 *  span to still surface the "no drafts" hint on hover. */
function PublishMenuItem({ disabled, publishing, tooltip, onSelect }: PublishMenuItemProps) {
  const item = (
    <DropdownMenuItem disabled={disabled} onSelect={onSelect}>
      {publishing ? (
        <Loader2 className={`${MENU_ICON_CLASS} animate-spin`} />
      ) : (
        <Radio className={MENU_ICON_CLASS} />
      )}
      Publish
    </DropdownMenuItem>
  );
  if (!tooltip) return item;
  return (
    <CustomTooltip content={tooltip}>
      <span className="inline-flex w-full">{item}</span>
    </CustomTooltip>
  );
}
