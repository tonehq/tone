import { ArrowLeft, ChevronRight, Folder as FolderIcon, Pencil, Trash2 } from 'lucide-react';

import { cn } from '@/utils/cn';

import InlineFolderNameEditor from './InlineFolderNameEditor';

/** Compact breadcrumb shown when the user has drilled into a folder — just
 * enough to say "you're inside this folder": ``← All folders / <name> · N
 * scenarios``. Rename stays available as a small icon-only affordance next
 * to the name. Per-folder run is triggered from the folder card in the grid
 * view; the global "Run Eval" button in the header covers running from
 * inside a folder. */
export default function FolderBreadcrumb({
  folderName,
  count,
  onBack,
  onRename,
  isEditing = false,
  onSaveRename,
  onCancelRename,
  renamePending = false,
  onDelete,
  canDelete = true,
}: {
  folderName: string;
  count: number;
  onBack: () => void;
  onRename?: () => void;
  // Inline-rename state — mirrors ``FolderCard``. When ``isEditing`` is
  // true the folder-name span is swapped for ``InlineFolderNameEditor``.
  isEditing?: boolean;
  onSaveRename?: (next: string) => void;
  onCancelRename?: () => void;
  renamePending?: boolean;
  onDelete?: () => void;
  // ``false`` for the agent's last remaining folder — the button still
  // renders (so the affordance is discoverable) but is disabled with a
  // tooltip explaining the invariant.
  canDelete?: boolean;
}) {
  const displayName = folderName;
  return (
    <div className="flex flex-wrap items-center gap-2 text-[12.5px]">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex cursor-pointer items-center gap-1 font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        All folders
      </button>
      <ChevronRight className="size-3.5 text-muted-foreground/60" />
      <FolderIcon className="size-3.5 text-muted-foreground" />
      {isEditing && onSaveRename && onCancelRename ? (
        <InlineFolderNameEditor
          initialValue={displayName}
          onSave={onSaveRename}
          onCancel={onCancelRename}
          pending={renamePending}
          size="md"
        />
      ) : (
        <>
          <span
            className="max-w-[240px] truncate font-semibold text-foreground"
            title={displayName}
          >
            {displayName}
          </span>
          <span className="text-muted-foreground">
            · {count} scenario{count === 1 ? '' : 's'}
          </span>
          {onRename && (
            <button
              type="button"
              onClick={onRename}
              aria-label={`Rename ${displayName}`}
              title="Rename folder"
              className="ml-1 inline-flex cursor-pointer items-center justify-center rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <Pencil className="size-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={canDelete ? onDelete : undefined}
              disabled={!canDelete}
              aria-label={`Delete folder ${displayName}`}
              title={
                canDelete
                  ? 'Delete folder'
                  : 'Every agent must have at least one folder — create another folder before deleting this one.'
              }
              className={cn(
                'inline-flex items-center justify-center rounded p-1 transition-colors',
                canDelete
                  ? 'cursor-pointer text-muted-foreground hover:bg-destructive/10 hover:text-destructive'
                  : 'cursor-not-allowed text-muted-foreground/40',
              )}
            >
              <Trash2 className="size-3.5" />
            </button>
          )}
        </>
      )}
    </div>
  );
}
