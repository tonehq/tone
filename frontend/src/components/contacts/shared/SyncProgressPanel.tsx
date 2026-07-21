'use client';

import { useEffect, useRef } from 'react';

import { CustomButton } from '@/components/shared';

import SyncErrorTable from './SyncErrorTable';
import SyncStatusChip from './SyncStatusChip';
import { useSyncStatusPolling } from './useSyncStatusPolling';

/**
 * The shared import-progress phase: polls a created sync to terminal status and renders
 * the status chip, the created/updated/skipped/failed counts grid, the
 * completed-with-warnings / hard-failure banners, the per-row error table, and the
 * Retry/Done actions.
 *
 * WHAT: self-contained — it owns the `useSyncStatusPolling(syncId)` subscription and fires
 * `onTerminal` exactly once when the sync first reaches a terminal state (so the parent can
 * refresh its list / show a banner without re-deriving the sync).
 *
 * WHEN: reuse in every import modal (the dormant SyncContactsModal and the
 * UploadContactsModal) so there is ONE progress-phase implementation.
 */
export interface SyncProgressPanelProps {
  /** The created sync to track. */
  syncId: string;
  /** Reset back to the form (Retry — shown only on failure). */
  onReset: () => void;
  /** Close/finish the flow (Done). */
  onDone: () => void;
  /** Fired exactly once when the sync first reaches a terminal status. */
  onTerminal?: (syncId: string) => void;
}

export default function SyncProgressPanel({
  syncId,
  onReset,
  onDone,
  onTerminal,
}: SyncProgressPanelProps) {
  const poll = useSyncStatusPolling(syncId);
  const notifiedSyncId = useRef<string | null>(null);

  // Notify the parent exactly once per sync, when it first reaches a terminal state, so it
  // can refetch its contacts list (a render-time call would loop).
  useEffect(() => {
    if (poll.isTerminal && notifiedSyncId.current !== syncId) {
      notifiedSyncId.current = syncId;
      onTerminal?.(syncId);
    }
  }, [poll.isTerminal, syncId, onTerminal]);

  const counts = poll.sync?.counts ?? {};
  const rowErrors = poll.sync?.row_errors ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Import status</span>
        {poll.status && <SyncStatusChip status={poll.status} />}
      </div>

      {poll.isTerminal && (
        <dl className="grid grid-cols-4 gap-2 text-center text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Created</dt>
            <dd className="font-medium">{counts.created ?? 0}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Updated</dt>
            <dd className="font-medium">{counts.updated ?? 0}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Skipped</dt>
            <dd className="font-medium">{counts.skipped ?? 0}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Failed</dt>
            <dd className="font-medium">{counts.failed ?? 0}</dd>
          </div>
        </dl>
      )}

      {poll.completedWithWarnings && (
        <div
          role="alert"
          className="rounded-lg bg-orange-50 px-3 py-2 text-sm text-orange-800 ring-1 ring-inset ring-orange-200"
        >
          Import finished with some skipped rows — review them below.
        </div>
      )}

      {poll.isFailed && (
        <div
          role="alert"
          className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 ring-1 ring-inset ring-red-200"
        >
          {poll.sync?.error ?? 'The import failed. Please check the file and try again.'}
        </div>
      )}

      {poll.isTerminal && <SyncErrorTable rowErrors={rowErrors} syncId={syncId} />}

      <div className="flex justify-end gap-2 pt-2">
        {poll.isFailed && (
          <CustomButton type="default" onClick={onReset}>
            Retry
          </CustomButton>
        )}
        <CustomButton type="primary" onClick={onDone} disabled={poll.isPolling}>
          {poll.isTerminal ? 'Done' : 'Importing…'}
        </CustomButton>
      </div>
    </div>
  );
}
