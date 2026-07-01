'use client';

import { useMemo } from 'react';

import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import { formatRelative, getInitials } from '@/lib/utils';
import type { CustomTableColumn } from '@/types/components';
import type { AuditLogItem } from '@/types/settings/auditLog';
import { cn } from '@/utils/cn';

import {
  ACTION_BADGE_CLASS,
  ACTION_LABEL,
  resolveActorName,
  resolveTargetName,
  shortId,
} from './constants';
import type { AuditLookups } from './useAuditLookups';

interface AuditLogsTableProps {
  rows: AuditLogItem[];
  total: number;
  loading: boolean;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
  onRowClick: (row: AuditLogItem) => void;
  onRefresh: () => void;
  refreshing: boolean;
  lookups: AuditLookups;
  // Client-side resource filter — the backend doesn't support filtering by
  // target_resource_type directly, so we filter the current page in-memory.
  resourceFilter: string;
}

function actorForTable(
  userId: string | null,
  users: Map<string, string>,
): { name: string; initials: string; isSystem: boolean } {
  const { name, isSystem } = resolveActorName(userId, users);
  if (isSystem) return { name, initials: 'SY', isSystem };
  const [first = '', last = ''] = name.split(' ');
  const initials = getInitials(first, last);
  return { name, initials: initials === '?' ? '?' : initials, isSystem };
}

function resourceDisplay(
  row: AuditLogItem,
  lookups: AuditLookups,
): { primary: string; secondary: string } {
  if (!row.target_resource_id) return { primary: '—', secondary: '' };
  const primary = resolveTargetName(row, lookups.targets) || row.target_resource_type || 'resource';
  return { primary, secondary: shortId(row.target_resource_id, 28) };
}

function changesSummary(row: AuditLogItem): string {
  if (!row.changes) return '—';
  const before = row.changes.before ?? {};
  const after = row.changes.after ?? {};
  const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
  if (keys.size === 0) return '—';
  return `${keys.size} field${keys.size === 1 ? '' : 's'}`;
}

export default function AuditLogsTable({
  rows,
  total,
  loading,
  page,
  pageSize,
  onPageChange,
  onRowClick,
  onRefresh,
  refreshing,
  lookups,
  resourceFilter,
}: AuditLogsTableProps) {
  // Apply the client-side resource filter here so the table always sees the
  // final list. Server-side filtering would need a backend change.
  const filteredRows = useMemo(() => {
    if (resourceFilter === 'all') return rows;
    return rows.filter((r) => r.target_resource_type === resourceFilter);
  }, [rows, resourceFilter]);

  // Memoise the column defs so CustomTable's internal `useMemo` on columnDefs
  // stays hot — the render fns close over `lookups`, so we key on that too.
  const columns = useMemo<CustomTableColumn<AuditLogItem>[]>(
    () => [
      {
        key: 'action',
        title: 'Action',
        width: 'w-52',
        render: (_: unknown, record: AuditLogItem) => (
          <Badge variant="secondary" className={ACTION_BADGE_CLASS}>
            {ACTION_LABEL[record.action] ?? record.action}
          </Badge>
        ),
      },
      {
        key: 'resource',
        title: 'Resource',
        render: (_: unknown, record: AuditLogItem) => {
          const { primary, secondary } = resourceDisplay(record, lookups);
          return (
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{primary}</p>
              {secondary && (
                <p className="truncate font-mono text-[11px] text-muted-foreground">{secondary}</p>
              )}
            </div>
          );
        },
      },
      {
        key: 'user',
        title: 'User',
        width: 'w-48',
        render: (_: unknown, record: AuditLogItem) => {
          const actor = actorForTable(record.actor_user_id, lookups.users);
          return (
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={cn(
                  'flex size-6 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold',
                  actor.isSystem ? 'bg-muted text-muted-foreground' : 'bg-primary/10 text-primary',
                )}
              >
                {actor.initials}
              </span>
              <span className="truncate text-sm text-foreground">{actor.name}</span>
            </div>
          );
        },
      },
      {
        key: 'ip',
        title: 'IP Address',
        width: 'w-44',
        render: (_: unknown, record: AuditLogItem) => (
          <span className="font-mono text-[12px] text-muted-foreground">
            {record.ip_address ?? '—'}
          </span>
        ),
      },
      {
        key: 'changes',
        title: 'Changes',
        width: 'w-28',
        render: (_: unknown, record: AuditLogItem) => (
          <span className="text-[12px] text-muted-foreground">{changesSummary(record)}</span>
        ),
      },
      {
        key: 'time',
        title: 'Time',
        width: 'w-32',
        render: (_: unknown, record: AuditLogItem) => (
          <span className="text-[12px] text-muted-foreground">
            {formatRelative(record.created_at)}
          </span>
        ),
      },
    ],
    [lookups],
  );

  return (
    <CustomTable
      columns={columns}
      dataSource={filteredRows}
      rowKey="id"
      loading={loading}
      searchable
      searchPlaceholder="Search logs…"
      onRowClick={onRowClick}
      onRefresh={onRefresh}
      refreshing={refreshing}
      pagination={{
        current: page,
        pageSize,
        total,
        onChange: onPageChange,
      }}
    />
  );
}
