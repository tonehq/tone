'use client';

import { useContactSync } from '@/lib/api/contactSyncs';
import {
  CONTACT_SYNC_TERMINAL_STATUSES,
  type ContactSync,
  type ContactSyncStatus,
} from '@/types/contactSync';

/**
 * Poll one sync until it reaches a terminal status.
 *
 * WHAT: wraps `useContactSync(id, { poll: true })` and derives convenience flags — the
 * live sync, whether it's still running, whether it finished, and whether it completed
 * WITH row-level warnings (partial failures). Polling stops automatically at a terminal
 * status (`completed`/`failed`).
 *
 * WHEN: use in the sync stepper (`SyncContactsModal`) and the Agent Contacts auto-assign
 * flow to drive the progress UI and the completed-with-warnings banner. Pass `null` to
 * disable (before a sync has been created).
 */
export interface UseSyncStatusPollingResult {
  sync: ContactSync | undefined;
  status: ContactSyncStatus | undefined;
  isPolling: boolean;
  isTerminal: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  /** Completed, but at least one row was skipped/failed (has warnings + an error report). */
  completedWithWarnings: boolean;
  isLoading: boolean;
}

export function useSyncStatusPolling(
  syncId: string | null | undefined,
): UseSyncStatusPollingResult {
  const { data: sync, isLoading } = useContactSync(syncId, { poll: true });
  const status = sync?.status;

  const isTerminal = status != null && CONTACT_SYNC_TERMINAL_STATUSES.includes(status);
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';

  const counts = sync?.counts ?? {};
  const hasRowWarnings =
    (sync?.row_errors?.length ?? 0) > 0 || (counts.skipped ?? 0) > 0 || (counts.failed ?? 0) > 0;

  return {
    sync,
    status,
    isPolling: !!syncId && !isTerminal,
    isTerminal,
    isCompleted,
    isFailed,
    completedWithWarnings: isCompleted && hasRowWarnings,
    isLoading,
  };
}
