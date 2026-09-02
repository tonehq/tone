import { useQuery } from '@tanstack/react-query';

import { listAgentTemplates } from '@/services/agentsService';

/**
 * Agent template catalog (used by the "start from a template" picker in the
 * create-agent modal). Read-only, so it lives in TanStack Query; pass
 * `{ enabled: open }` to fetch only while the modal is open. `retry: false`
 * keeps the previous single-shot fetch semantics.
 */
export const agentTemplateKeys = {
  list: () => ['agent-templates', 'list'] as const,
};

export function useAgentTemplates(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: agentTemplateKeys.list(),
    queryFn: listAgentTemplates,
    enabled: options?.enabled ?? true,
    retry: false,
  });
}
