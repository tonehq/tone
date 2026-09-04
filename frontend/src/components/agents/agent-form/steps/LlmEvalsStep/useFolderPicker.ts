import { useEffect, useState } from 'react';

import { useCreateAgentLlmEvalFolder } from '@/lib/api/agentLlmEvals';
import type { AgentLlmEvalFolder } from '@/types/agentLlmEval';
import { showToast } from '@/utils/toast';

import { NEW_FOLDER_OPTION_VALUE } from './constants';

// Resolution returned by ``resolveFolderIdOrCreate``. ``valid`` is ``false``
// only when the user chose "+ Create new folder…" but left the name blank
// (an error toast has already been shown) — callers that need to abort the
// submit read this flag; callers that historically proceeded regardless can
// ignore it and use ``folderId`` (which is ``null`` in that case).
export interface FolderResolution {
  folderId: string | null;
  valid: boolean;
}

/** Shared folder-selection state + resolve logic for the scenario create/edit
 * and generate modals. Owns the ``folderId`` / ``newFolderName`` state, the
 * create-folder mutation, the backfill effect that picks the first folder once
 * the folders query resolves, and the "resolve the id — creating a new folder
 * first if the user asked for one" logic. Both modals share exactly one copy
 * of this behaviour (validation + create-folder mutation + query
 * invalidation). */
export function useFolderPicker(
  agentId: string,
  { open, folderOptions }: { open: boolean; folderOptions: AgentLlmEvalFolder[] },
) {
  const createFolder = useCreateAgentLlmEvalFolder(agentId);
  // Folder id, or the ``NEW_FOLDER_OPTION_VALUE`` sentinel while creating.
  const [folderId, setFolderId] = useState('');
  const [newFolderName, setNewFolderName] = useState('');

  // Defensive backfill: if the modal opened before the folders query
  // resolved, folderId is '' — pick the first folder once folders arrive so
  // the SelectInput's rendered value matches state (fixes silent display/state
  // divergence in ``FolderPicker``).
  useEffect(() => {
    if (!open || folderId || folderId === NEW_FOLDER_OPTION_VALUE) return;
    if (folderOptions.length === 0) return;
    setFolderId(folderOptions[0].id);
  }, [open, folderId, folderOptions]);

  const resolveFolderIdOrCreate = async (): Promise<FolderResolution> => {
    if (folderId === NEW_FOLDER_OPTION_VALUE) {
      const trimmed = newFolderName.trim();
      if (!trimmed) {
        showToast.error('Folder name is required');
        return { folderId: null, valid: false };
      }
      const created = await createFolder.mutateAsync({ name: trimmed });
      setFolderId(created.id);
      return { folderId: created.id, valid: true };
    }
    return { folderId: folderId || null, valid: true };
  };

  return {
    folderId,
    setFolderId,
    newFolderName,
    setNewFolderName,
    resolveFolderIdOrCreate,
    isCreatingFolder: createFolder.isPending,
  };
}
