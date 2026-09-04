'use client';

import { useQuery } from '@tanstack/react-query';

import { getAllAgents } from '@/services/agentsService';
import type { AgentDropdownItem } from '@/types/agent';

export const AGENTS_DROPDOWN_QUERY_KEY = 'agents-dropdown';

/**
 * Fetch the org's agent dropdown list (id + name) via TanStack Query.
 *
 * Replaces the ref-guarded Jotai `fetchAllAgentsAtom` effect that pages used to
 * populate the agents atom — server state belongs in the query cache, so any
 * page that needs the agent list shares one cache entry and one fetch.
 */
export function useAgents() {
  return useQuery<AgentDropdownItem[]>({
    queryKey: [AGENTS_DROPDOWN_QUERY_KEY],
    queryFn: getAllAgents,
    staleTime: 5 * 60 * 1000,
  });
}
