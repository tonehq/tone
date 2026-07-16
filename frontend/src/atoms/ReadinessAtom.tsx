import { atom } from 'jotai';

import { getAgentReadiness, getAgentReadinessSummary } from '@/services/readinessService';
import type {
  ReadinessDepth,
  ReadinessReport,
  ReadinessSummary,
  ReadinessTrigger,
} from '@/types/readiness';

/**
 * Write-only atoms mirroring the `AgentsAtom` pattern — components dispatch
 * via `useAtom(...)` and receive the raw response back. No module-level
 * shared state; callers store the result in their own component state or a
 * dedicated read atom family so the readiness for one agent doesn't leak
 * into another agent's view.
 */

export const fetchAgentReadinessAtom = atom(
  null,
  async (
    _get,
    _set,
    args: {
      agentId: string;
      depth: ReadinessDepth;
      configId?: string;
      trigger?: ReadinessTrigger | string;
    },
  ): Promise<ReadinessReport> =>
    getAgentReadiness(args.agentId, args.depth, args.configId, args.trigger),
);

export const fetchAgentReadinessSummaryAtom = atom(
  null,
  async (
    _get,
    _set,
    args: {
      agentId: string;
      configId?: string;
      trigger?: ReadinessTrigger | string;
    },
  ): Promise<ReadinessSummary> =>
    getAgentReadinessSummary(args.agentId, args.configId, args.trigger),
);
