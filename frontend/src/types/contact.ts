/**
 * Contact types — mirrors `core/models/contact.py` `to_dict()` and the directory-scoped
 * contacts router shapes.
 *
 * A `Contact` now belongs to exactly one `ContactDirectory` (`directory_id`, required)
 * and records the sync run that last wrote it (`sync_id`). The old `source_upload_id`
 * field is GONE. Create is bulk + partial-success (C-7): `POST
 * /contact-directories/{id}/contacts` returns `{ created, failed }`, not a single object.
 */

import type { PaginatedListParams, PaginatedResponse } from '@/types/contactList';

/** A single contact row (mirrors `Contact.to_dict()`). */
export interface Contact {
  id: string;
  directory_id: string | null;
  external_id: string;
  name: string | null;
  phone_number: string | null;
  contact_metadata: Record<string, unknown>;
  sync_id: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/** `POST /contact-directories/{id}/contacts/list` response. */
export type ContactListResponse = PaginatedResponse<Contact>;

/** List params for the directory-scoped contacts list (paging/search/sort). */
export type ListContactsParams = PaginatedListParams;

/** One row in a create-contacts request body. */
export interface ContactRowPayload {
  name?: string | null;
  phone_number?: string | null;
  external_id?: string | null;
  contact_metadata?: Record<string, unknown>;
}

/**
 * Body for `POST /contact-directories/{id}/contacts`. Send EITHER a single `contact` or
 * a `contacts` array — both normalise to the same `{ created, failed }` response.
 */
export interface CreateContactsPayload {
  contact?: ContactRowPayload;
  contacts?: ContactRowPayload[];
  /**
   * Optional agent to assign the created contacts to. When set, the backend also inserts
   * `agent_contacts` for every created contact (idempotent); when omitted the contacts are
   * just created. Lets the directory General view and the agent Contacts tab share one
   * create endpoint.
   */
  agent_id?: string;
}

/** A row that failed create validation (C-7). `index` is its position in the input. */
export interface CreateContactFailure {
  index: number;
  errors: string[];
}

/**
 * `POST /contact-directories/{id}/contacts` response (C-7): partial success — valid rows
 * land in `created`, invalid rows are reported in `failed` (nothing is rolled back).
 */
export interface CreateContactsResponse {
  created: Contact[];
  failed: CreateContactFailure[];
  /** Present only when the request carried `agent_id` — count of contacts assigned. */
  assigned?: number;
}

/** Body for `PATCH /contacts/{id}`. */
export interface UpdateContactPayload {
  name?: string | null;
  phone_number?: string | null;
  contact_metadata?: Record<string, unknown>;
}

/** `POST /contact-directories/{id}/contacts/bulk-delete` — soft-deletes by id. */
export interface BulkDeleteContactsResponse {
  deleted: number;
}

/**
 * Body for `POST /contact/schedule-calls` (unchanged endpoint — no scheduling gate).
 * `scheduled_at` is a UTC ISO string (from the shared `DateTimePicker`).
 */
export interface ScheduleContactCallsPayload {
  agent_id: string;
  from_number: string;
  contact_ids: string[];
  scheduled_at?: string | null;
}

/** `POST /contact/schedule-calls` response. */
export interface ScheduleContactCallsResponse {
  count: number;
  invalid: { contact_id: string; error: string }[];
  data: unknown[];
}
