'use client';

import { useAtom } from 'jotai';
import { useEffect, useState } from 'react';

import { fetchAllAgentsAtom } from '@/atoms/AgentsAtom';
import {
  AUDIT_ACTION_GROUPS,
  AUDIT_RESOURCE_OPTIONS,
  auditLogParamsAtom,
  setAuditLogParamsAtom,
  type AuditLogActionGroup,
} from '@/atoms/AuditLogAtom';
import { SearchableSelect, SelectInput } from '@/components/shared';
import type { AuditLogResourceType } from '@/types/settings/auditLog';

const ACTION_OPTIONS = AUDIT_ACTION_GROUPS.map((g) => ({ value: g.value, label: g.label }));
const RESOURCE_OPTIONS = AUDIT_RESOURCE_OPTIONS.map((r) => ({ value: r.value, label: r.label }));

export default function AuditLogFilters() {
  const [params] = useAtom(auditLogParamsAtom);
  const [, setParams] = useAtom(setAuditLogParamsAtom);
  const [, fetchAllAgents] = useAtom(fetchAllAgentsAtom);
  const [agentOptions, setAgentOptions] = useState<{ value: string; label: string }[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(true);

  useEffect(() => {
    // Agents dropdown is lightweight (id + name only) and static enough for
    // the audit page's lifetime — fetch once on mount.
    let cancelled = false;
    setLoadingAgents(true);
    fetchAllAgents()
      .then((rows) => {
        if (cancelled) return;
        setAgentOptions(rows.map((a) => ({ value: a.uuid, label: a.name })));
      })
      .finally(() => {
        if (!cancelled) setLoadingAgents(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fetchAllAgents]);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="w-full max-w-xs">
        <SearchableSelect
          name="audit-agent"
          options={agentOptions}
          value={params.agent_id ?? ''}
          onValueChange={(v) => setParams({ agent_id: v || null })}
          placeholder="Select an agent…"
          searchPlaceholder="Search agents…"
          loading={loadingAgents}
        />
      </div>

      <div className="w-40">
        <SelectInput
          name="audit-actions"
          options={ACTION_OPTIONS}
          value={params.action_group}
          onValueChange={(v) => setParams({ action_group: v as AuditLogActionGroup })}
          placeholder="All Actions"
        />
      </div>

      <div className="w-44">
        <SelectInput
          name="audit-resources"
          options={RESOURCE_OPTIONS}
          value={params.resource_type}
          onValueChange={(v) => setParams({ resource_type: v as AuditLogResourceType | 'all' })}
          placeholder="All Resources"
        />
      </div>
    </div>
  );
}
