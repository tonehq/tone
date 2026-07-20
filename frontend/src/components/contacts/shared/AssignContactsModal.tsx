'use client';

import { useMemo, useState } from 'react';

import { useAssignContacts } from '@/lib/api/agentContacts';
import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { CustomButton, CustomModal } from '@/components/shared';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import DirectoryContactTree from './DirectoryContactTree';
import SyncContactsModal from './SyncContactsModal';
import {
  useDirectoryContactTreeSelection,
  type DirectorySelectionMeta,
} from './useDirectoryContactTreeSelection';

/**
 * Assign contacts to an agent. Two paths:
 *  - Option 1 — `DirectoryContactTree` tri-state tree-select → confirm sends
 *    `{ directory_ids, contact_ids }` to the assign endpoint (directories expanded to
 *    their active contacts server-side).
 *  - Option 2 — the shared `SyncContactsModal` with this `agentId`, so a fresh CSV import
 *    auto-assigns its imported contacts to the agent on completion.
 *
 * WHEN: opened from the agent editor's Contacts tab (`ContactsStep`).
 */
export interface AssignContactsModalProps {
  open: boolean;
  onClose: () => void;
  agentId: string;
  /** Called after a successful assign / sync completion so the parent can refetch. */
  onAssigned?: () => void;
}

export default function AssignContactsModal({
  open,
  onClose,
  agentId,
  onAssigned,
}: AssignContactsModalProps) {
  const treeSelection = useDirectoryContactTreeSelection();
  const assign = useAssignContacts(agentId);
  const [syncOpen, setSyncOpen] = useState(false);

  // Directory counts for the "N selected" summary (whole-directory picks contribute their
  // live contact_count). One list fetch; the tree does its own paginated/search fetches.
  const { data: directoriesData } = useDirectoriesList({ page_size: 100 });
  const metaByDirectory = useMemo(() => {
    const map = new Map<string, DirectorySelectionMeta>();
    for (const dir of directoriesData?.data ?? []) {
      map.set(dir.id, { contactCount: dir.contact_count });
    }
    return map;
  }, [directoriesData]);

  const selectedCount = treeSelection.countSelected(metaByDirectory);

  const handleClose = () => {
    treeSelection.clear();
    onClose();
  };

  const handleAssign = async () => {
    if (!treeSelection.hasSelection) {
      showToast.error('Select at least one directory or contact.');
      return;
    }
    try {
      const result = await assign.mutateAsync(treeSelection.selection);
      showToast.success(
        `Assigned ${result.assigned} contact${result.assigned === 1 ? '' : 's'}${
          result.skipped ? ` (${result.skipped} already assigned)` : ''
        }`,
      );
      treeSelection.clear();
      onAssigned?.();
      onClose();
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <>
      <CustomModal
        open={open && !syncOpen}
        onClose={handleClose}
        title="Assign contacts"
        hideFooter
        width="sm:max-w-xl"
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Pick whole directories or individual contacts to assign to this agent, or import a new
            CSV that auto-assigns as it lands.
          </p>

          <DirectoryContactTree selection={treeSelection} />

          <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground" aria-live="polite">
                {selectedCount} selected
              </span>
              <CustomButton type="link" size="sm" onClick={() => setSyncOpen(true)}>
                Import from CSV instead
              </CustomButton>
            </div>
            <div className="flex gap-2">
              <CustomButton type="default" onClick={handleClose}>
                Cancel
              </CustomButton>
              <CustomButton
                type="primary"
                onClick={handleAssign}
                loading={assign.isPending}
                disabled={!treeSelection.hasSelection}
              >
                Assign
              </CustomButton>
            </div>
          </div>
        </div>
      </CustomModal>

      {/*
        Option 2 — CSV import with auto-assign. We pass ONLY `agentId` (no `directoryId`), so
        `SyncContactsModal` enters its agent context (`isAgentContext = !directoryId && !!agentId`)
        and shows its own directory picker — defaulting to the org's "Global" directory. Passing
        a concrete `directoryId` here would disable that picker.
      */}
      {syncOpen && (
        <SyncContactsModal
          open={syncOpen}
          onClose={() => setSyncOpen(false)}
          agentId={agentId}
          defaultSchemaId={null}
          onCompleted={() => {
            onAssigned?.();
          }}
        />
      )}
    </>
  );
}
