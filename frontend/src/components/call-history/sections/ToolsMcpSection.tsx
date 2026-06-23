'use client';

import ToolExecutionDetailDrawer from '@/components/call-history/tools-mcp/ToolExecutionDetailDrawer';
import ToolExecutionsTable from '@/components/call-history/tools-mcp/ToolExecutionsTable';
import ToolExecutionStats from '@/components/call-history/tools-mcp/ToolExecutionStats';
import {
  ALL_TOOLS,
  STATUS_FILTER_OPTIONS,
  summarize,
  uniqueToolNames,
} from '@/components/call-history/tools-mcp/helpers';
import { SelectInput } from '@/components/shared';
import { getCallToolExecutions } from '@/services/callLogService';
import type { CallLogRow, ToolExecution, ToolExecutionStatus } from '@/types/callLog';
import { handleApiError } from '@/utils/helpers';
import { Wrench } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

interface ToolsMcpSectionProps {
  callLog: CallLogRow;
}

type StatusFilter = 'all' | ToolExecutionStatus;

function Header({ total, loading }: { total: number; loading: boolean }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 className="text-sm font-medium text-foreground">Tools & MCP</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {loading
            ? 'Loading tool invocations…'
            : total === 0
              ? 'No tools were invoked during this call.'
              : `${total} ${total === 1 ? 'invocation' : 'invocations'} captured.`}
        </p>
      </div>
    </div>
  );
}

interface FilterBarProps {
  /** `'all'` or a specific tool_name present in this call. */
  tool: string;
  onToolChange: (tool: string) => void;
  status: StatusFilter;
  onStatusChange: (s: StatusFilter) => void;
  /** Unique tool names actually invoked in this call — populates the tool dropdown. */
  toolNames: string[];
}

function FilterBar({ tool, onToolChange, status, onStatusChange, toolNames }: FilterBarProps) {
  const toolOptions = useMemo(
    () => [
      { value: ALL_TOOLS, label: 'All tools' },
      ...toolNames.map((name) => ({ value: name, label: name })),
    ],
    [toolNames],
  );

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="w-[240px]">
        <SelectInput
          name="tool-execution-tool"
          size="sm"
          value={tool}
          onValueChange={onToolChange}
          options={toolOptions}
          disabled={toolNames.length === 0}
        />
      </div>

      <div className="w-[180px]">
        <SelectInput
          name="tool-execution-status"
          size="sm"
          value={status}
          onValueChange={(v) => onStatusChange(v as StatusFilter)}
          options={STATUS_FILTER_OPTIONS.map((o) => ({ value: o.key, label: o.label }))}
        />
      </div>
    </div>
  );
}

function EmptyState({ hasAny, loading }: { hasAny: boolean; loading: boolean }) {
  if (loading) return null;
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <div className="flex size-10 items-center justify-center rounded-full bg-muted">
        <Wrench className="size-5 text-muted-foreground" />
      </div>
      <p className="text-sm text-muted-foreground">
        {hasAny
          ? 'No tool calls match the current filters.'
          : 'No tool calls were recorded for this call.'}
      </p>
    </div>
  );
}

/**
 * "Tools & MCP" tab of the call-detail page. Fetches the tool_executions for
 * the call once, then filters/aggregates client-side — a single call rarely
 * has more than a few dozen invocations, so server-side filtering would be
 * over-engineering. Composed from three small pieces:
 *   - `ToolExecutionStats`  — KPI tiles (StatCard, same as Metrics tab)
 *   - `ToolExecutionsTable` — `CustomTable` of executions
 *   - `ToolExecutionDetailDrawer` — slide-in with full args / result / error
 */
const ToolsMcpSection: React.FC<ToolsMcpSectionProps> = ({ callLog }) => {
  const [rows, setRows] = useState<ToolExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [tool, setTool] = useState<string>(ALL_TOOLS);
  const [status, setStatus] = useState<StatusFilter>('all');
  const [selected, setSelected] = useState<ToolExecution | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    // Drop any open selection from a previous call — a stale execution would
    // otherwise sit in the drawer while a different call's rows load behind it.
    setSelected(null);
    // Reset the per-tool filter when the call changes — the previous call's
    // tool name almost certainly isn't present in the new call.
    setTool(ALL_TOOLS);
    getCallToolExecutions(callLog.id)
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [callLog.id]);

  const summary = useMemo(() => summarize(rows), [rows]);
  const toolNames = useMemo(() => uniqueToolNames(rows), [rows]);
  const filtered = useMemo(() => {
    const byTool = tool === ALL_TOOLS ? rows : rows.filter((r) => r.tool_name === tool);
    if (status === 'all') return byTool;
    return byTool.filter((r) => r.status === status);
  }, [rows, tool, status]);

  return (
    <div className="flex h-full flex-col gap-5">
      <Header total={summary.total} loading={loading} />

      <ToolExecutionStats summary={summary} />

      <FilterBar
        tool={tool}
        onToolChange={setTool}
        status={status}
        onStatusChange={setStatus}
        toolNames={toolNames}
      />

      <ToolExecutionsTable
        rows={filtered}
        loading={loading}
        onRowClick={setSelected}
        emptyState={<EmptyState hasAny={rows.length > 0} loading={loading} />}
      />

      <ToolExecutionDetailDrawer
        execution={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
};

export default ToolsMcpSection;
