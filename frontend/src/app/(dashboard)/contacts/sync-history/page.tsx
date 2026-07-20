'use client';

import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ChevronDown, History } from 'lucide-react';
import { useMemo, useState } from 'react';

import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { useContactSyncsList } from '@/lib/api/contactSyncs';
import { CustomButton, SelectInput } from '@/components/shared';
import SyncErrorTable from '@/components/contacts/shared/SyncErrorTable';
import SyncStatusChip from '@/components/contacts/shared/SyncStatusChip';
import type { ContactSync, ContactSyncStatus } from '@/types/contactSync';
import { cn } from '@/utils/cn';
import { formatTimestamp } from '@/utils/date';

/**
 * `/contacts/sync-history` — an org-wide log of every CSV import across all directories.
 *
 * WHAT: lists past `ContactSync` runs (newest first, paginated) so a user can reopen a
 * finished sync after closing the sync modal — each row shows the directory it targeted,
 * its status + counts, and an expandable per-row error report (`SyncErrorTable`) with a
 * re-downloadable CSV.
 *
 * WHEN: the third item in the focused Contacts section rail, after "Datasource".
 */
const PAGE_SIZE = 10;

// `all` is a sentinel — Radix Select can't use an empty-string item value.
const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'processing', label: 'Processing' },
  { value: 'pending', label: 'Pending' },
];

export default function ContactsSyncHistoryPage() {
  const [page, setPage] = useState(1);
  const [directoryFilter, setDirectoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const { data: syncsPage, isLoading } = useContactSyncsList({
    page_no: page,
    page_size: PAGE_SIZE,
    sort_by: 'created_at',
    sort_order: 'desc',
    directory_id: directoryFilter === 'all' ? undefined : directoryFilter,
    status: statusFilter === 'all' ? undefined : (statusFilter as ContactSyncStatus),
  });

  // Resolve directory ids → names so each sync shows which directory it imported into.
  const { data: directoriesPage } = useDirectoriesList({ page_size: 100 });
  const directoryNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const d of directoriesPage?.data ?? []) map.set(d.id, d.name);
    return map;
  }, [directoriesPage]);

  const directoryOptions = useMemo(
    () => [
      { value: 'all', label: 'All directories' },
      ...(directoriesPage?.data ?? []).map((d) => ({ value: d.id, label: d.name })),
    ],
    [directoriesPage],
  );

  const hasFilters = directoryFilter !== 'all' || statusFilter !== 'all';
  const handleDirectoryFilter = (id: string) => {
    setDirectoryFilter(id);
    setPage(1);
  };
  const handleStatusFilter = (s: string) => {
    setStatusFilter(s);
    setPage(1);
  };
  const clearFilters = () => {
    setDirectoryFilter('all');
    setStatusFilter('all');
    setPage(1);
  };

  const syncs = syncsPage?.data ?? [];
  const total = syncsPage?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="animate-page flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-col gap-1 border-b border-border px-6 py-5">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Sync History</h1>
        <p className="text-sm text-muted-foreground">
          Past CSV imports across your directories — review skipped rows and re-download error
          reports.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-6">
        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <div className="w-56">
              <SelectInput
                name="filter-directory"
                options={directoryOptions}
                value={directoryFilter}
                onValueChange={handleDirectoryFilter}
                placeholder="All directories"
              />
            </div>
            <div className="w-44">
              <SelectInput
                name="filter-status"
                options={STATUS_OPTIONS}
                value={statusFilter}
                onValueChange={handleStatusFilter}
                placeholder="All statuses"
              />
            </div>
            {hasFilters && (
              <CustomButton type="text" size="sm" onClick={clearFilters}>
                Clear filters
              </CustomButton>
            )}
          </div>

          {isLoading ? (
            <SyncHistorySkeleton />
          ) : syncs.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16 text-center">
              <span className="flex size-14 items-center justify-center rounded-full bg-muted/60 ring-1 ring-border">
                <History className="size-6 text-muted-foreground" aria-hidden />
              </span>
              <div className="space-y-1">
                <p className="text-sm font-semibold text-foreground">
                  {hasFilters ? 'No syncs match these filters' : 'No syncs yet'}
                </p>
                <p className="text-sm text-muted-foreground">
                  {hasFilters
                    ? 'Try a different directory or status.'
                    : 'Import a CSV into a directory and its run will show up here.'}
                </p>
              </div>
              {hasFilters && (
                <CustomButton type="default" size="sm" onClick={clearFilters}>
                  Clear filters
                </CustomButton>
              )}
            </div>
          ) : (
            <>
              <ul className="flex flex-col gap-3">
                {syncs.map((sync) => (
                  <li key={sync.id}>
                    <SyncHistoryCard sync={sync} directoryNames={directoryNames} />
                  </li>
                ))}
              </ul>

              <div className="mt-auto flex items-center justify-between gap-3 pt-6">
                <span className="text-xs tabular-nums text-muted-foreground">
                  Page {page} of {totalPages}
                </span>
                <div className="flex items-center gap-2">
                  <CustomButton
                    type="default"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                  >
                    Previous
                  </CustomButton>
                  <CustomButton
                    type="default"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                  >
                    Next
                  </CustomButton>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/** 2–3 shimmering placeholder cards while the first page loads. */
function SyncHistorySkeleton() {
  return (
    <ul className="flex flex-col gap-3" aria-busy="true" aria-label="Loading syncs">
      {Array.from({ length: 3 }).map((_, i) => (
        <li key={i} className="rounded-lg border border-border border-l-2 border-l-border p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-col gap-2">
              <div className="h-4 w-40 animate-pulse rounded bg-muted" />
              <div className="h-3 w-28 animate-pulse rounded bg-muted/70" />
            </div>
            <div className="h-6 w-24 animate-pulse rounded-full bg-muted" />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {Array.from({ length: 4 }).map((_, j) => (
              <div key={j} className="h-6 w-20 animate-pulse rounded-md bg-muted/70" />
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}

/** completed w/ 0 failed → success · completed w/ some failed but progress → warning · failed → error. */
type SyncOutcome = 'success' | 'warning' | 'error' | 'neutral';

function getSyncOutcome(sync: ContactSync): SyncOutcome {
  if (sync.status === 'failed') return 'error';
  if (sync.status === 'completed') {
    const { created = 0, updated = 0, failed = 0 } = sync.counts ?? {};
    if (failed > 0) return created > 0 || updated > 0 ? 'warning' : 'error';
    return 'success';
  }
  return 'neutral';
}

/** Left accent keyed to outcome — soft token tints, not loud fills. */
const OUTCOME_ACCENT: Record<SyncOutcome, string> = {
  success: 'border-l-emerald-400',
  warning: 'border-l-amber-400',
  error: 'border-l-red-400',
  neutral: 'border-l-border',
};

/** One sync run: directory + date + status + counts, with an expandable error report. */
function SyncHistoryCard({
  sync,
  directoryNames,
}: {
  sync: ContactSync;
  directoryNames: Map<string, string>;
}) {
  const [expanded, setExpanded] = useState(false);
  const reduceMotion = useReducedMotion();
  const hasErrors = sync.row_errors.length > 0;
  const directoryName =
    (sync.directory_id && directoryNames.get(sync.directory_id)) || 'Deleted directory';
  const counts = sync.counts ?? {};
  const outcome = getSyncOutcome(sync);

  return (
    <div
      className={cn(
        'rounded-lg border border-border border-l-2 bg-card transition-colors',
        OUTCOME_ACCENT[outcome],
      )}
    >
      <div className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-0.5">
            <span className="truncate text-base font-semibold text-foreground">
              {directoryName}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatTimestamp(sync.created_at)}
            </span>
          </div>
          <SyncStatusChip status={sync.status} />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <StatChip label="Created" value={counts.created ?? 0} tone="created" />
          <StatChip label="Updated" value={counts.updated ?? 0} tone="updated" />
          <StatChip label="Skipped" value={counts.skipped ?? 0} tone="skipped" />
          <StatChip label="Failed" value={counts.failed ?? 0} tone="failed" />
        </div>

        {sync.error && (
          <div
            role="alert"
            className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 ring-1 ring-inset ring-red-200"
          >
            {sync.error}
          </div>
        )}
      </div>

      {hasErrors && (
        <div className="border-t border-border px-4 py-2">
          <CustomButton
            type="text"
            size="xs"
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
            icon={
              <ChevronDown
                className={cn(
                  'size-3.5 transition-transform',
                  expanded ? 'rotate-0' : '-rotate-90',
                )}
              />
            }
          >
            View errors ({sync.row_errors.length})
          </CustomButton>

          <AnimatePresence initial={false}>
            {expanded && (
              <motion.div
                key="errors"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: reduceMotion ? 0 : 0.2, ease: 'easeOut' }}
                className="overflow-hidden"
              >
                <div className="pt-2">
                  <SyncErrorTable rowErrors={sync.row_errors} syncId={sync.id} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

type StatTone = 'created' | 'updated' | 'skipped' | 'failed';

/** Quiet color coding; non-zero values are emphasized, zero values recede to muted. */
const STAT_TONE: Record<StatTone, string> = {
  created: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  updated: 'bg-sky-50 text-sky-700 ring-sky-200',
  skipped: 'bg-amber-50 text-amber-700 ring-amber-200',
  failed: 'bg-red-50 text-red-700 ring-red-200',
};

function StatChip({ label, value, tone }: { label: string; value: number; tone: StatTone }) {
  const active = value > 0;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        active ? STAT_TONE[tone] : 'bg-muted/50 text-muted-foreground ring-transparent',
      )}
    >
      <span className="tabular-nums">{value}</span>
      <span className={cn('font-normal', active ? undefined : 'text-muted-foreground')}>
        {label}
      </span>
    </span>
  );
}
