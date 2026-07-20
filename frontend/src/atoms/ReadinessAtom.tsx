import { atom } from 'jotai';

import {
  getAgentReadiness,
  getAgentReadinessRun,
  getAgentReadinessSummary,
  listAgentReadinessRuns,
} from '@/services/readinessService';
import type {
  ReadinessCategory,
  ReadinessDepth,
  ReadinessReport,
  ReadinessRunList,
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
      /** Targeted-deep filter — only probes these categories live when `depth`
       * is `'deep'`. Ignored when `depth` is `'shallow'`. */
      categories?: ReadinessCategory[];
      /** Force a fresh run + persisted event (bypasses backend caches). */
      force?: boolean;
    },
  ): Promise<ReadinessReport> =>
    getAgentReadiness(
      args.agentId,
      args.depth,
      args.configId,
      args.trigger,
      args.categories,
      args.force,
    ),
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

export const fetchAgentReadinessRunsAtom = atom(
  null,
  async (_get, _set, args: { agentId: string; limit?: number }): Promise<ReadinessRunList> =>
    listAgentReadinessRuns(args.agentId, args.limit),
);

export const fetchAgentReadinessRunAtom = atom(
  null,
  async (_get, _set, args: { agentId: string; runNumber: number }): Promise<ReadinessReport> =>
    getAgentReadinessRun(args.agentId, args.runNumber),
);
