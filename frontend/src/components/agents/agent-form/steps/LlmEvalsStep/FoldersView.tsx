import type { AgentLlmEvalFolder } from '@/types/agentLlmEval';

import FolderCard from './FolderCard';

/** Default view — a grid of folder cards. Clicking a card drills into
 * that folder's scenarios (see ``FolderBreadcrumb``). Every scenario
 * belongs to a real folder — there is no Uncategorized bucket. Empty
 * folders survive after their last scenario is deleted so they still
 * render as a card. */
export default function FoldersView({
  folders,
  isLoading,
  onOpen,
  onRunFolder,
  onRename,
  onDelete,
  isRunning,
  editingFolderId,
  onSaveRename,
  onCancelRename,
  renamePending,
  canDeleteAny,
}: {
  folders: AgentLlmEvalFolder[];
  isLoading: boolean;
  onOpen: (folderId: string) => void;
  onRunFolder: (folderId: string) => void;
  onRename: (folderId: string) => void;
  onDelete: (folderId: string) => void;
  isRunning: boolean;
  // Inline-rename plumbing. ``editingFolderId`` is the id of the folder
  // currently in edit mode (only one at a time). Cards compare their own
  // id against it to decide whether to render the editor.
  editingFolderId: string | null;
  onSaveRename: (next: string) => void;
  onCancelRename: () => void;
  renamePending: boolean;
  // Every agent must always have at least one folder — the delete affordance
  // is hidden on the last folder to prevent the "no folders" empty state.
  canDeleteAny: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading folders…
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {folders.length === 0 ? (
        <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
          No folders yet. Click <span className="font-medium">New folder</span> to create one.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {folders.map((f) => (
            <FolderCard
              key={f.id}
              name={f.name}
              count={f.count}
              canRename
              onOpen={() => onOpen(f.id)}
              onRun={() => onRunFolder(f.id)}
              onRename={() => onRename(f.id)}
              // Always show the Delete affordance so users can see the
              // feature exists — the LAST folder for an agent renders it
              // disabled with an explanatory tooltip (backend enforces
              // the same invariant via ``FOLDER_NOT_DELETABLE``).
              onDelete={() => onDelete(f.id)}
              canDelete={canDeleteAny}
              isRunning={isRunning}
              isEditing={editingFolderId === f.id}
              onSaveRename={onSaveRename}
              onCancelRename={onCancelRename}
              renamePending={renamePending}
            />
          ))}
        </div>
      )}
    </div>
  );
}
