'use client';

import { useAtom } from 'jotai';
import { ScrollText } from 'lucide-react';
import { useState } from 'react';

import {
  auditLogParamsAtom,
  loadableAuditLogPagedAtom,
  refetchAuditLogAtom,
  setAuditLogParamsAtom,
} from '@/atoms/AuditLogAtom';
import type { AuditLogItem } from '@/types/settings/auditLog';

import AuditLogDetailsDrawer from './AuditLogDetailsDrawer';
import AuditLogFilters from './AuditLogFilters';
import AuditLogStats from './AuditLogStats';
import AuditLogsTable from './AuditLogsTable';
import { useAuditLookups } from './useAuditLookups';
import { useAuditStats } from './useAuditStats';

export default function AuditLogs() {
  const [params] = useAtom(auditLogParamsAtom);
  const [, setParams] = useAtom(setAuditLogParamsAtom);
  const [loadableRows] = useAtom(loadableAuditLogPagedAtom);
  const [, refetch] = useAtom(refetchAuditLogAtom);
  const lookups = useAuditLookups();

  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRow, setSelectedRow] = useState<AuditLogItem | null>(null);

  const stats = useAuditStats(params.agent_id, refreshKey);

  const loading = loadableRows.state === 'loading';
  const data = loadableRows.state === 'hasData' ? loadableRows.data : null;
  const rows = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refetch();
      // Nudge the stats hook to re-run alongside the table.
      setRefreshKey((k) => k + 1);
    } finally {
      // Small delay so the spinner is visible even on very fast responses.
      setTimeout(() => setRefreshing(false), 300);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Audit Logs</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Track every configuration change made to your agents.
        </p>
      </div>

      {/* ── Stat cards ─────────────────────────────────────────── */}
      <AuditLogStats stats={stats} agentSelected={!!params.agent_id} />

      {/* ── Filters ────────────────────────────────────────────── */}
      <AuditLogFilters />

      {/* ── Table / empty state ────────────────────────────────── */}
      {!params.agent_id ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/70 bg-card py-16 text-center">
          <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <ScrollText className="size-6" strokeWidth={1.75} />
          </div>
          <h3 className="text-base font-semibold text-foreground">Select an agent</h3>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Pick an agent from the filter above to view its configuration change history.
          </p>
        </div>
      ) : (
        <AuditLogsTable
          rows={rows}
          total={total}
          loading={loading}
          page={params.page}
          pageSize={params.page_size}
          onPageChange={(page, pageSize) => setParams({ page, page_size: pageSize })}
          onRowClick={setSelectedRow}
          onRefresh={handleRefresh}
          refreshing={refreshing}
          lookups={lookups}
          resourceFilter={params.resource_type}
        />
      )}

      {/* ── Details drawer ─────────────────────────────────────── */}
      <AuditLogDetailsDrawer
        row={selectedRow}
        onClose={() => setSelectedRow(null)}
        lookups={lookups}
      />
    </div>
  );
}
