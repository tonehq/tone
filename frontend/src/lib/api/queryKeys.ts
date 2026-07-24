/**
 * Typed TanStack Query key factory for the Contact Directories feature.
 *
 * WHAT: a single source of truth for every query key used by the contacts api clients,
 * so lists/details/mutations invalidate consistently (partial-key invalidation works
 * because keys share a stable prefix tuple).
 *
 * WHEN: use these instead of hand-writing string arrays in any contacts query or
 * `invalidateQueries` call. Passing `params` narrows to one query; omitting it (or
 * invalidating the plain `.lists()` key) refetches every page/filter of that resource.
 *
 * Keys are `as const` tuples so `queryClient.invalidateQueries({ queryKey })` can match
 * by prefix (e.g. invalidate ALL directory lists by passing `contactKeys.directories.lists()`).
 */

/** Any params object attached to a list key (paging/search/sort/scoping). */
type ListParams = object | undefined;

export const contactKeys = {
  directories: {
    all: () => ['contact-directories'] as const,
    lists: () => ['contact-directories', 'list'] as const,
    list: (params?: ListParams) => ['contact-directories', 'list', params ?? {}] as const,
    detail: (id: string) => ['contact-directories', 'detail', id] as const,
    deleteImpact: (id: string) => ['contact-directories', 'delete-impact', id] as const,
  },
  datasources: {
    all: () => ['contact-datasources'] as const,
    lists: () => ['contact-datasources', 'list'] as const,
    list: (params?: ListParams) => ['contact-datasources', 'list', params ?? {}] as const,
  },
  schemas: {
    all: () => ['contact-schemas'] as const,
    lists: () => ['contact-schemas', 'list'] as const,
    list: (params?: ListParams) => ['contact-schemas', 'list', params ?? {}] as const,
    detail: (id: string) => ['contact-schemas', 'detail', id] as const,
  },
  contacts: {
    all: () => ['contacts'] as const,
    /** All contact lists for one directory (invalidate to refetch every page/filter). */
    lists: (directoryId: string) => ['contacts', directoryId, 'list'] as const,
    list: (directoryId: string, params?: ListParams) =>
      ['contacts', directoryId, 'list', params ?? {}] as const,
  },
  syncs: {
    all: () => ['contact-syncs'] as const,
    lists: () => ['contact-syncs', 'list'] as const,
    list: (params?: ListParams) => ['contact-syncs', 'list', params ?? {}] as const,
    detail: (id: string) => ['contact-syncs', 'detail', id] as const,
  },
  agentContacts: {
    all: (agentId: string) => ['agent-contacts', agentId] as const,
    lists: (agentId: string) => ['agent-contacts', agentId, 'list'] as const,
    list: (agentId: string, params?: ListParams) =>
      ['agent-contacts', agentId, 'list', params ?? {}] as const,
  },
} as const;

/** Query keys for the customer-facing generated API Keys (Settings → API Keys). */
export const apiKeyKeys = {
  all: () => ['generated-api-keys'] as const,
  lists: () => ['generated-api-keys', 'list'] as const,
  list: (params?: ListParams) => ['generated-api-keys', 'list', params ?? {}] as const,
} as const;
