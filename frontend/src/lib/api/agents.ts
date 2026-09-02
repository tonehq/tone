import { useQuery } from '@tanstack/react-query';

import { getAllAgents } from '@/services/agentsService';
import type { AgentDropdownItem } from '@/types/agent';

export const agentKeys = {
  all: () => ['agents'] as const,
  dropdown: () => ['agents', 'dropdown'] as const,
};

/**
 * All agents as lightweight dropdown items ({@link AgentDropdownItem}).
 * Mirrors the sipTrunks.ts query-hook pattern so server data lives in the
 * TanStack cache instead of per-component useState.
 */
export function useAllAgents(options?: { enabled?: boolean }) {
  return useQuery<AgentDropdownItem[]>({
    queryKey: agentKeys.dropdown(),
    queryFn: getAllAgents,
    enabled: options?.enabled ?? true,
  });
}
