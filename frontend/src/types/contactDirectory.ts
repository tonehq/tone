/**
 * ContactDirectory types — mirrors `core/models/contact_directory.py` `to_dict()` and
 * the directory router request/response shapes. A directory is the org-scoped container
 * that owns its contacts + a CSV datasource and references one reusable org-level schema
 * as its default shape (`default_schema_id`).
 */

/** A single directory as returned by `GET /contact-directories/{id}` (bare `to_dict`). */
export interface ContactDirectory {
  id: string;
  name: string;
  description: string | null;
  default_schema_id: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * A directory row inside `POST /contact-directories/list` — the list endpoint enriches
 * each `to_dict` with a live `contact_count` for the rail + tree badges.
 */
export interface ContactDirectoryListItem extends ContactDirectory {
  contact_count: number;
}

/** Body for `POST /contact-directories` (create; admin/owner). */
export interface CreateDirectoryPayload {
  name: string;
  description?: string | null;
  /** Optional org schema to set as the directory's default. Omitted → no default
   * schema (none is auto-created per directory). */
  default_schema_id?: string | null;
}

/** Body for `PATCH /contact-directories/{id}` (update; admin/owner). */
export interface UpdateDirectoryPayload {
  name?: string | null;
  description?: string | null;
  is_active?: boolean;
  default_schema_id?: string | null;
}

/**
 * `GET /contact-directories/{id}/delete-impact` — the confirm-modal blast radius from
 * `summarize_directory_deletion`. Counts are rows that will be DELETED (contacts,
 * agent_contacts, scheduled_calls) or DETACHED (syncs); org schemas are always kept.
 */
export interface DirectoryDeleteImpact {
  contacts: number;
  agent_contacts: number;
  scheduled_calls: number;
  syncs_detached: number;
  schemas_kept: boolean;
}

/**
 * `DELETE /contact-directories/{id}` — the summary from
 * `hard_delete_directory_and_children` (what was actually removed/detached).
 */
export interface DirectoryDeleteResult {
  directory_id: string;
  contacts_deleted: number;
  agent_contacts_deleted: number;
  scheduled_calls_deleted: number;
  dial_jobs_cancelled: number;
  datasources_deleted: number;
  syncs_marked_failed: number;
  syncs_detached: number;
}
