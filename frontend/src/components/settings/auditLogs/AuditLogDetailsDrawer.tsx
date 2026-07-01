'use client';

import { CustomDrawer } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { formatDateTime } from '@/lib/utils';
import type { AuditLogItem } from '@/types/settings/auditLog';
import { cn } from '@/utils/cn';

import {
  ACTION_BADGE_CLASS,
  ACTION_LABEL,
  RESOURCE_LABEL,
  resolveActorName,
  resolveTargetName,
  shortId,
} from './constants';
import type { AuditLookups } from './useAuditLookups';

interface AuditLogDetailsDrawerProps {
  row: AuditLogItem | null;
  onClose: () => void;
  lookups: AuditLookups;
}

interface FieldRow {
  key: string;
  before: unknown;
  after: unknown;
}

// Merge before + after keys into an ordered field-diff so the drawer can render
// "key: <before> → <after>" for every changed field, including ones that only
// exist on one side (create/delete/attach cases).
function toFieldRows(row: AuditLogItem): FieldRow[] {
  const before = row.changes?.before ?? {};
  const after = row.changes?.after ?? {};
  const keys = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]));
  return keys.map((key) => ({
    key,
    before: (before as Record<string, unknown>)[key],
    after: (after as Record<string, unknown>)[key],
  }));
}

function formatValue(value: unknown): string {
  if (value === undefined) return '—';
  if (value === null) return 'null';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function AuditLogDetailsDrawer({
  row,
  onClose,
  lookups,
}: AuditLogDetailsDrawerProps) {
  const rows = row ? toFieldRows(row) : [];
  const actor = row ? resolveActorName(row.actor_user_id, lookups.users) : null;
  const target = row ? resolveTargetName(row, lookups.targets) : null;

  return (
    <CustomDrawer
      open={!!row}
      onClose={onClose}
      title="Audit event"
      description={row ? formatDateTime(row.created_at) : undefined}
      width="w-full sm:!max-w-xl"
    >
      {row && (
        <div className="flex flex-col gap-5 pt-2">
          {/* ── Header row: action badge + resource ─────────────── */}
          <div className="flex flex-wrap items-center gap-2">
            <Badge className={ACTION_BADGE_CLASS} variant="secondary">
              {ACTION_LABEL[row.action] ?? row.action}
            </Badge>
            {row.target_resource_type && (
              <span className="text-xs text-muted-foreground">
                on {RESOURCE_LABEL[row.target_resource_type]}
              </span>
            )}
          </div>

          {/* ── Metadata pairs (actor / target / IP / request) ─── */}
          <dl className="grid grid-cols-3 gap-x-4 gap-y-3 text-sm">
            <dt className="col-span-1 text-muted-foreground">Actor</dt>
            <dd className="col-span-2 text-foreground">{actor?.name}</dd>

            {target && (
              <>
                <dt className="col-span-1 text-muted-foreground">Target</dt>
                <dd className="col-span-2 font-mono text-[13px] text-foreground">{target}</dd>
              </>
            )}

            <dt className="col-span-1 text-muted-foreground">IP</dt>
            <dd className="col-span-2 font-mono text-[13px] text-foreground">
              {row.ip_address ?? '—'}
            </dd>

            <dt className="col-span-1 text-muted-foreground">Request ID</dt>
            <dd className="col-span-2 font-mono text-[13px] text-foreground">
              {shortId(row.request_id, 32)}
            </dd>
          </dl>

          {/* ── Changes payload ──────────────────────────────────── */}
          <div>
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Changes {rows.length ? `(${rows.length})` : ''}
            </h3>
            {rows.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                This event has no detailed change payload.
              </p>
            ) : (
              <div className="overflow-hidden rounded-lg border border-border">
                {rows.map((r, idx) => (
                  <div
                    key={r.key}
                    className={cn(
                      'grid grid-cols-[minmax(0,140px)_minmax(0,1fr)] gap-3 px-3 py-2.5 text-[13px]',
                      idx !== rows.length - 1 && 'border-b border-border/60',
                    )}
                  >
                    <div className="truncate font-medium text-foreground">{r.key}</div>
                    <div className="grid grid-cols-2 gap-3 min-w-0">
                      <pre className="whitespace-pre-wrap break-words rounded bg-rose-500/5 p-2 font-mono text-[12px] text-rose-700 dark:text-rose-300">
                        {formatValue(r.before)}
                      </pre>
                      <pre className="whitespace-pre-wrap break-words rounded bg-emerald-500/5 p-2 font-mono text-[12px] text-emerald-700 dark:text-emerald-300">
                        {formatValue(r.after)}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {row.user_agent && (
            <div>
              <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                User Agent
              </h3>
              <p className="break-words rounded bg-muted/30 p-2 font-mono text-[12px] text-muted-foreground">
                {row.user_agent}
              </p>
            </div>
          )}
        </div>
      )}
    </CustomDrawer>
  );
}
