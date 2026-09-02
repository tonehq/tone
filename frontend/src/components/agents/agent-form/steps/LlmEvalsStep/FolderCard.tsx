import { ChevronRight, Folder as FolderIcon, Pencil, Play, Trash2 } from 'lucide-react';

import { cn } from '@/utils/cn';

import FolderCardAction from './FolderCardAction';
import InlineFolderNameEditor from './InlineFolderNameEditor';

/** One folder tile — clickable to open, with quick Run + Rename actions
 * always visible at the bottom (muted → foreground on hover). The whole
 * card is a ``<button>``; nested actions use ``<span role="button">`` +
 * ``e.stopPropagation()`` (invalid to nest ``<button>`` inside a button).
 * The delete affordance always renders so users see the feature exists;
 * ``canDelete=false`` renders it disabled with a tooltip (the agent's
 * LAST folder can't be deleted — invariant enforced by the backend too). */
export default function FolderCard({
  name,
  count,
  canRename,
  onOpen,
  onRun,
  onRename,
  onDelete,
  canDelete = true,
  isRunning,
  isEditing = false,
  onSaveRename,
  onCancelRename,
  renamePending = false,
}: {
  name: string;
  count: number;
  canRename: boolean;
  onOpen: () => void;
  onRun: () => void;
  onRename?: () => void;
  // Always provided by ``FoldersView`` — see ``canDelete`` for the gate.
  onDelete?: () => void;
  // ``false`` for the agent's last remaining folder. Renders the Delete
  // button disabled with a tooltip explaining the invariant.
  canDelete?: boolean;
  isRunning: boolean;
  // Inline-edit state. When ``isEditing`` is true, the name span is
  // swapped for ``InlineFolderNameEditor`` and the drill-in click is
  // suppressed so a click inside the input doesn't also open the folder.
  isEditing?: boolean;
  onSaveRename?: (next: string) => void;
  onCancelRename?: () => void;
  renamePending?: boolean;
}) {
  const isMuted = false;
  const runDisabled = isRunning || count === 0;
  // The whole card is normally a ``<button>`` so the entire tile is
  // clickable. During inline edit we swap to a ``<div>`` because native
  // HTML forbids a ``<button>`` inside a ``<button>`` and the editor's
  // ✓/✕ / input are interactive controls.
  const Container = isEditing ? 'div' : 'button';
  return (
    <Container
      type={isEditing ? undefined : ('button' as const)}
      onClick={isEditing ? undefined : onOpen}
      className={cn(
        'group relative flex h-full flex-col gap-4 rounded-xl border border-border/60 p-4 text-left',
        'transition-all duration-150',
        !isEditing &&
          'hover:-translate-y-0.5 hover:border-border hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        isEditing && 'ring-2 ring-ring/40',
        isMuted ? 'bg-muted/30' : 'bg-card',
      )}
      aria-label={isEditing ? `Renaming folder ${name}` : `Open folder ${name}`}
    >
      {/* Top row: folder icon + name. Icon is prominent so the "folder"
          metaphor is instantly readable; the small chevron on the right
          signals "click to drill in" (opacity picks up on hover). */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-lg ring-1',
            isMuted
              ? 'bg-muted text-muted-foreground ring-border'
              : 'bg-violet-500/10 text-violet-700 ring-violet-500/20 dark:text-violet-400',
          )}
        >
          <FolderIcon className="size-5" />
        </div>
        <div className="min-w-0 flex-1 pt-0.5">
          {isEditing && onSaveRename && onCancelRename ? (
            <InlineFolderNameEditor
              initialValue={name}
              onSave={onSaveRename}
              onCancel={onCancelRename}
              pending={renamePending}
              size="sm"
            />
          ) : (
            <div
              className="truncate text-[14px] font-semibold leading-tight text-foreground"
              title={name}
            >
              {name}
            </div>
          )}
          <div className="mt-1 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10.5px] font-medium text-muted-foreground">
            {count} scenario{count === 1 ? '' : 's'}
          </div>
        </div>
        {!isEditing && (
          <ChevronRight
            className={cn(
              'mt-1 size-4 shrink-0 text-muted-foreground/40 transition-all',
              'group-hover:translate-x-0.5 group-hover:text-muted-foreground',
            )}
          />
        )}
      </div>

      {/* Bottom action row — always visible, muted by default so the card
          reads clean, brightens on card hover so users know they're
          interactive. Divider gives visual separation without extra chrome.
          Actions are hidden during inline rename so the editor gets full
          focus (the ✓/✕ inside the editor are the only relevant actions). */}
      {!isEditing && (
        <div className="mt-auto flex items-center gap-1 border-t border-border/50 pt-3">
          {canRename && onRename && (
            <FolderCardAction
              icon={<Pencil className="size-3.5" />}
              label="Rename"
              onActivate={onRename}
              title={`Rename ${name}`}
            />
          )}
          {onDelete && (
            <FolderCardAction
              icon={<Trash2 className="size-3.5" />}
              label="Delete"
              onActivate={onDelete}
              emphasis="danger"
              disabled={!canDelete}
              title={
                canDelete
                  ? `Delete folder ${name}`
                  : 'Every agent must have at least one folder — create another folder before deleting this one.'
              }
            />
          )}
          <FolderCardAction
            icon={<Play className="size-3.5" />}
            label="Run folder"
            onActivate={onRun}
            disabled={runDisabled}
            title={count === 0 ? 'Folder is empty' : `Run ${name}`}
            emphasis="primary"
            className="ml-auto"
          />
        </div>
      )}
    </Container>
  );
}
