'use client';

import { CustomTable, CustomTooltip } from '@/components/shared';
import type { ToolExecution } from '@/types/callLog';
import type { CustomTableColumn } from '@/types/components';
import { cn } from '@/utils/cn';
import { ChevronRight } from 'lucide-react';
import React, { useMemo } from 'react';

import {
  authFor,
  durationToneClass,
  endpointFor,
  formatDuration,
  formatStartedAt,
  statusPill,
  toolTypeChipClasses,
  toolTypeLabel,
} from './helpers';

interface ToolExecutionsTableProps {
  rows: ToolExecution[];
  loading: boolean;
  onRowClick: (execution: ToolExecution) => void;
  emptyState: React.ReactNode;
}

/**
 * The actual table grid for the Tools & MCP tab. Columns are pure render
 * helpers — all formatting, color and labeling live in `./helpers` so the
 * drawer and table stay in sync.
 */
const ToolExecutionsTable: React.FC<ToolExecutionsTableProps> = ({
  rows,
  loading,
  onRowClick,
  emptyState,
}) => {
  const columns = useMemo<CustomTableColumn<ToolExecution>[]>(
    () => [
      {
        key: 'tool_name',
        title: 'Tool',
        render: (_v, record) => (
          <p className="truncate font-mono text-[13px] font-medium text-foreground">
            {record.tool_name}
          </p>
        ),
      },
      {
        key: 'tool_type',
        title: 'Type',
        width: '110px',
        render: (_v, record) => (
          <span
            className={cn(
              'inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-medium',
              toolTypeChipClasses(record.tool_type),
            )}
          >
            {toolTypeLabel(record.tool_type)}
          </span>
        ),
      },
      {
        key: 'mcp_server_name',
        title: 'MCP Server',
        width: '160px',
        render: (_v, record) =>
          record.mcp_server_name ? (
            <span className="truncate font-mono text-[12px] text-foreground">
              {record.mcp_server_name}
            </span>
          ) : (
            <span className="text-[12px] text-muted-foreground">—</span>
          ),
      },
      {
        key: 'endpoint',
        title: 'Endpoint',
        width: '220px',
        render: (_v, record) => {
          const endpoint = endpointFor(record);
          return endpoint ? (
            <CustomTooltip content={endpoint}>
              <span className="block truncate font-mono text-[12px] text-foreground">
                {endpoint}
              </span>
            </CustomTooltip>
          ) : (
            <span className="text-[12px] text-muted-foreground">—</span>
          );
        },
      },
      {
        key: 'auth',
        title: 'Auth',
        width: '110px',
        render: (_v, record) => {
          const value = authFor(record);
          return value ? (
            <span className="inline-flex rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
              {value}
            </span>
          ) : (
            <span className="text-[12px] text-muted-foreground">—</span>
          );
        },
      },
      {
        key: 'status',
        title: 'Status',
        width: '110px',
        render: (_v, record) => {
          const pill = statusPill(record.status);
          return (
            <CustomTooltip
              content={
                record.error_message
                  ? record.error_message
                  : record.status_code
                    ? `HTTP ${record.status_code}`
                    : pill.label
              }
            >
              <span
                className={cn(
                  'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
                  pill.className,
                )}
              >
                {pill.label}
              </span>
            </CustomTooltip>
          );
        },
      },
      {
        key: 'duration_ms',
        title: 'Duration',
        align: 'right',
        width: '110px',
        sorter: (a, b) => (a.duration_ms ?? 0) - (b.duration_ms ?? 0),
        render: (_v, record) => {
          const d = formatDuration(record.duration_ms);
          return (
            <span className={cn('font-mono text-[12px]', durationToneClass(d.tone))}>{d.text}</span>
          );
        },
      },
      {
        key: 'turn_number',
        title: 'Turn',
        align: 'right',
        width: '70px',
        sorter: (a, b) => (a.turn_number ?? 0) - (b.turn_number ?? 0),
        render: (_v, record) => (
          <span className="font-mono text-[12px] text-muted-foreground">
            {record.turn_number == null ? '—' : `#${record.turn_number}`}
          </span>
        ),
      },
      {
        key: 'started_at',
        title: 'Started',
        width: '110px',
        render: (_v, record) => (
          <span className="font-mono text-[12px] text-muted-foreground">
            {formatStartedAt(record.started_at)}
          </span>
        ),
      },
      {
        key: 'open',
        title: '',
        width: '40px',
        align: 'right',
        render: () => <ChevronRight className="ml-auto size-4 text-muted-foreground" />,
      },
    ],
    [],
  );

  return (
    <CustomTable<ToolExecution>
      columns={columns}
      dataSource={rows}
      rowKey="id"
      loading={loading}
      onRowClick={onRowClick}
      emptyState={emptyState}
      pagination={{ current: 1, pageSize: 20, pageSizeOptions: [10, 20, 50] }}
    />
  );
};

export default ToolExecutionsTable;
