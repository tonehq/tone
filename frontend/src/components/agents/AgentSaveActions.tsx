'use client';

import { ChevronDown, GitBranchPlus, Loader2, Radio, Save } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export type AgentSaveAction = 'save_in_place' | 'save_as_new_version' | 'make_live';

interface AgentSaveActionsProps {
  /** Mode = 'create' shows a single "Create agent" button. */
  mode: 'create' | 'edit';
  /** True when the form is on the currently-live version (split button). */
  viewingLive: boolean;
  /** Number shown on the in-place save label ("Save to v3"). */
  liveVersionNumber: number | null;
  /** Number shown on the "Make v2 live" button when viewing a non-live row. */
  viewedVersionNumber: number | null;
  saving: boolean;
  switchingLive: boolean;
  onAction: (action: AgentSaveAction) => void;
}

/**
 * Single source of truth for the editor's primary action area. Renders one of
 * three layouts depending on context:
 *
 *  - **create** mode: one big "Create agent" button.
 *  - **edit + viewing live**: split "Save to v{N}" button with a "Save as new
 *    version" item in its dropdown.
 *  - **edit + viewing non-live**: a "Make v{N} live" button + a "Save as new
 *    version" button. In-place save is disabled here because writing the form
 *    to a non-live row would either silently mutate history or silently flip
 *    the live pointer — both surprising.
 */
export default function AgentSaveActions({
  mode,
  viewingLive,
  liveVersionNumber,
  viewedVersionNumber,
  saving,
  switchingLive,
  onAction,
}: AgentSaveActionsProps) {
  if (mode === 'create') {
    return (
      <CustomButton
        type="primary"
        size="sm"
        icon={
          saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />
        }
        onClick={() => onAction('save_in_place')}
        loading={saving}
        className="h-8"
      >
        Create agent
      </CustomButton>
    );
  }

  if (!viewingLive) {
    // Either action mutates the same agent — disable both while one runs so
    // a user can't fire "Make live" while a new-version save is mid-flight.
    const busy = saving || switchingLive;
    return (
      <div className="flex items-center gap-1.5">
        <CustomButton
          type="default"
          size="sm"
          icon={
            switchingLive ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Radio className="size-3.5" />
            )
          }
          onClick={() => onAction('make_live')}
          loading={switchingLive}
          disabled={busy}
          className="h-8"
        >
          {viewedVersionNumber != null ? `Make v${viewedVersionNumber} live` : 'Make this live'}
        </CustomButton>
        <CustomButton
          type="primary"
          size="sm"
          icon={
            saving ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <GitBranchPlus className="size-3.5" />
            )
          }
          onClick={() => onAction('save_as_new_version')}
          loading={saving}
          disabled={busy}
          className="h-8"
        >
          Save as new version
        </CustomButton>
      </div>
    );
  }

  // Editing the live version → split Save button.
  const primaryLabel = liveVersionNumber != null ? `Save to v${liveVersionNumber}` : 'Save changes';
  return (
    <div className="flex items-stretch">
      <CustomButton
        type="primary"
        size="sm"
        icon={
          saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />
        }
        onClick={() => onAction('save_in_place')}
        loading={saving}
        className="h-8 rounded-r-none"
      >
        {primaryLabel}
      </CustomButton>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <CustomButton
            type="primary"
            size="sm"
            aria-label="More save options"
            disabled={saving}
            className="h-8 rounded-l-none border-l border-primary-foreground/20 px-2"
          >
            <ChevronDown className="size-3.5" />
          </CustomButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[200px]">
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              onAction('save_as_new_version');
            }}
            className="gap-2 text-[13px]"
          >
            <GitBranchPlus className="size-3.5" />
            Save as new version
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
