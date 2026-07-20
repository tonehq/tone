/**
 * AgentContact types — mirrors the agent-contacts router shapes. Assigning attaches
 * contacts to an agent (idempotent, no scheduling gate); directories in the assign body
 * are expanded server-side to their active contacts.
 */

import type { Contact } from '@/types/contact';

/**
 * A row in `POST /agents/{id}/contacts/list` — the assigned contact's `to_dict()` plus
 * assignment metadata joined in by `list_agent_contacts`.
 */
export interface AgentContactRow extends Contact {
  assignment_id: string;
  assigned_at: string | null;
}

/**
 * Body for `POST /agents/{id}/contacts/assign`. Send whole `directory_ids` (expanded to
 * their active contacts server-side) and/or explicit `contact_ids`; at least one should
 * be non-empty (otherwise the call is a no-op).
 */
export interface AssignContactsPayload {
  directory_ids?: string[];
  contact_ids?: string[];
}

/** `POST /agents/{id}/contacts/assign` response — idempotent assign counts. */
export interface AssignContactsResult {
  assigned: number;
  skipped: number;
}

/** Body for `POST /agents/{id}/contacts/unassign`. */
export interface UnassignContactsPayload {
  contact_ids: string[];
}

/** `POST /agents/{id}/contacts/unassign` response — rows actually removed. */
export interface UnassignContactsResult {
  unassigned: number;
}
