/**
 * ContactSync types — mirrors `core/models/contact_sync.py` `to_dict()` and the
 * contact-syncs router shapes. A `ContactSync` is one run of the datasource-driven CSV
 * import into a directory (partial-success: valid rows imported, invalid rows recorded).
 */

/** Sync lifecycle status (pending → processing → completed | failed). */
export type ContactSyncStatus = 'pending' | 'processing' | 'completed' | 'failed';

/** The terminal statuses — polling stops once a sync reaches one of these. */
export const CONTACT_SYNC_TERMINAL_STATUSES: readonly ContactSyncStatus[] = ['completed', 'failed'];

/** Per-run counts written by `run_contact_sync`. */
export interface ContactSyncCounts {
  created?: number;
  updated?: number;
  skipped?: number;
  failed?: number;
}

/** A single per-row error entry in `row_errors` (partial-failure detail). */
export interface ContactSyncRowError {
  row: number;
  field: string | null;
  message: string;
  /** The failed row's identity, so the report shows WHICH contact failed. */
  name?: string | null;
  phone_number?: string | null;
}

/** A sync as returned by `to_dict()` (create / get / list rows). */
export interface ContactSync {
  id: string;
  directory_id: string | null;
  datasource_id: string | null;
  schema_id: string | null;
  upload_id: string | null;
  agent_id: string | null;
  status: ContactSyncStatus;
  counts: ContactSyncCounts;
  row_errors: ContactSyncRowError[];
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * Multipart body for `POST /contact-syncs`. Sent as `FormData` (the CSV `file` plus the
 * scalar fields), NOT JSON.
 */
export interface CreateContactSyncPayload {
  directory_id: string;
  schema_id: string;
  agent_id?: string | null;
  file: File;
}

/** Extra scoping field for `POST /contact-syncs/list` (on top of paging params). */
export interface ListContactSyncsParams {
  directory_id?: string | null;
  status?: ContactSyncStatus | null;
}
