'use client';

import { useEffect, useState } from 'react';

import { ACTIONS_BY_GROUP } from '@/atoms/AuditLogAtom';
import { listAuditLogs } from '@/services/auditLogService';
import type { AuditLogAction } from '@/types/settings/auditLog';

// The reference UI shows 5 stat cards. We compute them by asking the backend
// for the `total` of each action group with page_size=1 (we don't need the
// rows, only the count). This costs 5 tiny parallel calls per agent switch —
// cheaper than adding a dedicated stats endpoint, and keeps the backend
// contract untouched.
export interface AuditStats {
  loading: boolean;
  total: number;
  created: number;
  updated: number;
  deleted: number;
  attachments: number;
}

const EMPTY: AuditStats = {
  loading: false,
  total: 0,
  created: 0,
  updated: 0,
  deleted: 0,
  attachments: 0,
};

// Bumping `refreshKey` forces a refetch — used by the parent's refresh button
// so the stats cards stay in sync with the table.
export function useAuditStats(agentId: string | null, refreshKey = 0): AuditStats {
  const [state, setState] = useState<AuditStats>(EMPTY);

  useEffect(() => {
    if (!agentId) {
      setState(EMPTY);
      return;
    }

    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true }));

    async function load(id: string) {
      const call = (actions?: AuditLogAction[]) =>
        listAuditLogs({ agent_id: id, actions, page_no: 1, page_size: 1 });

      const [total, created, updated, deleted, attachments] = await Promise.allSettled([
        call(),
        call(ACTIONS_BY_GROUP.create),
        call(ACTIONS_BY_GROUP.update),
        call(ACTIONS_BY_GROUP.delete),
        call(ACTIONS_BY_GROUP.attach),
      ]);

      if (cancelled) return;

      const pick = (r: PromiseSettledResult<{ total: number }>) =>
        r.status === 'fulfilled' ? r.value.total : 0;

      setState({
        loading: false,
        total: pick(total),
        created: pick(created),
        updated: pick(updated),
        deleted: pick(deleted),
        attachments: pick(attachments),
      });
    }

    void load(agentId);

    return () => {
      cancelled = true;
    };
  }, [agentId, refreshKey]);

  return state;
}
