'use client';

import { useMemo, useState } from 'react';
import { CheckCircle2, Clock, Copy, ListChecks, Loader2, XCircle } from 'lucide-react';

import { CustomButton, CustomTable, CustomTooltip } from '@/components/shared';
import EvalResultsDrawer from '@/components/knowledge-base/EvalResultsDrawer';
import ManualEvalsModal from '@/components/knowledge-base/ManualEvalsModal';
import { Badge } from '@/components/ui/badge';
import { useEvalSummariesByIngestion } from '@/lib/api/evals';
import { useActivateIngestionRun, useIngestionRuns } from '@/lib/api/ingestion-runs';
import type { EvalRunSummary, EvalRunSummaryTotals } from '@/types/eval';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import type { IngestionRun, IngestionRunStatus } from '@/types/ingestionRun';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface IngestionRunsTabProps {
  uploadId: string;
  // Comes from the parent KB payload (`KnowledgeBase.active_ingestion_pipeline_run_id`).
  // Kept as a prop so the "Active" marker updates alongside its parent view without
  // this tab re-fetching the KB itself.
  activeRunId?: string | null;
}

const statusStyle: Record<
  IngestionRunStatus,
  { label: string; className: string; icon: React.ReactNode }
> = {
  pending: {
    label: 'Pending',
    className: 'bg-slate-500/10 text-slate-700 dark:text-slate-300 ring-1 ring-slate-500/20',
    icon: <Clock className="size-3" />,
  },
  running: {
    label: 'Running',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <Loader2 className="size-3 animate-spin" />,
  },
  ready: {
    label: 'Ready',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  failed: {
    label: 'Failed',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

const DEFAULT_PAGE_SIZE = 20;

// Color the "Evals" chip by pass rate — grey when no batch exists yet, red
// on any FAIL, amber on any PARTIAL (no FAIL), green when everything passed.
function evalChipTone(summary: EvalRunSummary | undefined): {
  className: string;
  label: string;
} {
  if (!summary) {
    return {
      className: 'bg-muted text-muted-foreground ring-1 ring-border/60',
      label: '—',
    };
  }
  const totals = summary.summary as EvalRunSummaryTotals;
  const total = totals?.total ?? 0;
  if (total === 0) {
    return {
      className: 'bg-muted text-muted-foreground ring-1 ring-border/60',
      label: '—',
    };
  }
  const label = `${totals.pass}/${total}`;
  if (summary.status === 'failed' || totals.fail > 0) {
    return {
      className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
      label,
    };
  }
  if (totals.partial > 0) {
    return {
      className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
      label,
    };
  }
  return {
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    label,
  };
}

export default function IngestionRunsTab({ uploadId, activeRunId }: IngestionRunsTabProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<CustomTableSortState>({ field: 'run_number', order: 'desc' });

  const { data, isLoading } = useIngestionRuns(uploadId, {
    page_no: page,
    page_size: pageSize,
    search: search || undefined,
    sort_by: sort.field,
    sort_order: sort.order,
  });

  const activate = useActivateIngestionRun(uploadId);
  const [activatingId, setActivatingId] = useState<string | null>(null);

  const [drawerRun, setDrawerRun] = useState<IngestionRun | null>(null);
  const [manualEvalsOpen, setManualEvalsOpen] = useState(false);

  const runs = data?.data ?? [];
  const total = data?.total ?? 0;

  // Batch-fetch the latest eval-batch summary for every visible ingestion run
  // so the "Evals" column paints in one query instead of N.
  const visibleRunIds = useMemo(() => runs.map((r) => r.id), [runs]);
  const { data: evalSummariesResp } = useEvalSummariesByIngestion(uploadId, visibleRunIds);
  const evalSummariesByIngestion = evalSummariesResp?.items ?? {};

  // When the parent doesn't pass the KB's active run id (e.g. the KB payload
  // isn't reachable in that view), derive it from the runs list so the
  // "Active" marker still highlights correctly. `is_active` is unique per
  // upload server-side.
  const resolvedActiveRunId = activeRunId ?? runs.find((r) => r.is_active)?.id ?? null;

  const handleActivate = async (run: IngestionRun) => {
    if (activatingId) return;
    setActivatingId(run.id);
    try {
      await activate.mutateAsync(run.id);
      showToast.success('Run activated', 'Retrieval now serves from this run.');
    } catch (error) {
      handleApiError(error);
    } finally {
      setActivatingId(null);
    }
  };

  const copyJobId = async (jobId: number) => {
    try {
      await navigator.clipboard.writeText(String(jobId));
      showToast.success('Copied', 'Procrastinate job id copied to clipboard.');
    } catch {
      // Clipboard blocked (e.g. no HTTPS in dev) — silent, non-critical.
    }
  };

  const columns = useMemo<CustomTableColumn<IngestionRun>[]>(
    () => [
      {
        key: 'run_number',
        title: 'Run #',
        dataIndex: 'run_number',
        sorter: true,
        width: 'w-[80px]',
        render: (value) => (
          <span className="text-sm font-medium tabular-nums text-foreground">
            {value as number}
          </span>
        ),
      },
      {
        key: 'status',
        title: 'Status',
        dataIndex: 'status',
        sorter: true,
        width: 'w-[140px]',
        render: (_value, record) => {
          const s = statusStyle[record.status] ?? statusStyle.pending;
          return (
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
                s.className,
              )}
              title={record.error ?? undefined}
            >
              {s.icon}
              {s.label}
            </span>
          );
        },
      },
      {
        key: 'active',
        title: 'Active',
        width: 'w-[80px]',
        align: 'center',
        render: (_v, record) =>
          resolvedActiveRunId && record.id === resolvedActiveRunId ? (
            <CheckCircle2 className="mx-auto size-4 text-emerald-600" />
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'parser',
        title: 'Parser',
        dataIndex: 'parser',
        render: (value) => <span className="text-sm text-foreground">{String(value ?? '—')}</span>,
      },
      {
        key: 'tokeniser',
        title: 'Tokeniser',
        dataIndex: 'tokeniser',
        render: (value) => <span className="text-sm text-foreground">{String(value ?? '—')}</span>,
      },
      {
        key: 'embedder',
        title: 'Embedder',
        render: (_v, r) => (
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm text-foreground">{r.embedding_model}</span>
            <span className="truncate text-xs text-muted-foreground">
              {r.embedding_provider} · {r.embedding_dimensions}D
            </span>
          </div>
        ),
      },
      {
        key: 'vector_store',
        title: 'Store',
        dataIndex: 'vector_store',
        width: 'w-[110px]',
        render: (v) => <span className="text-sm text-foreground">{String(v ?? '—')}</span>,
      },
      {
        key: 'chunk_count',
        title: 'Chunks',
        dataIndex: 'chunk_count',
        sorter: true,
        align: 'right',
        width: 'w-[100px]',
        render: (value) => (
          <span className="text-sm tabular-nums text-muted-foreground">
            {value == null ? '—' : (value as number).toLocaleString()}
          </span>
        ),
      },
      {
        key: 'evals',
        title: 'Evals',
        align: 'center',
        width: 'w-[110px]',
        render: (_v, r) => {
          const summary = evalSummariesByIngestion[r.id];
          const chip = evalChipTone(summary);
          const totals = summary?.summary as EvalRunSummaryTotals | undefined;
          const tooltip = summary
            ? `${totals?.pass ?? 0} pass · ${totals?.partial ?? 0} partial · ${totals?.fail ?? 0} fail (batch #${summary.run_number}) — click to view`
            : 'No eval batch has scored this run yet — click to view';
          return (
            <CustomTooltip content={tooltip}>
              <button
                type="button"
                onClick={() => setDrawerRun(r)}
                className={cn(
                  'inline-flex items-center justify-center rounded-full px-2 py-0.5 text-[11px] font-medium tabular-nums transition-colors hover:brightness-110',
                  chip.className,
                )}
              >
                {chip.label}
              </button>
            </CustomTooltip>
          );
        },
      },
      {
        key: 'completed_at',
        title: 'Completed',
        dataIndex: 'completed_at',
        sorter: true,
        width: 'w-[190px]',
        render: (value) =>
          value ? (
            <span className="text-sm tabular-nums text-muted-foreground">
              {formatDate(value as string)}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'procrastinate_job_id',
        title: 'Job ID',
        width: 'w-[130px]',
        render: (_v, r) =>
          r.procrastinate_job_id != null ? (
            <button
              type="button"
              onClick={() => copyJobId(r.procrastinate_job_id as number)}
              className="inline-flex items-center gap-1 text-xs tabular-nums text-muted-foreground hover:text-foreground"
              title="Copy job id"
            >
              <Copy className="size-3" />
              {r.procrastinate_job_id}
            </button>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'error',
        title: 'Error',
        render: (_v, r) =>
          r.error ? (
            <CustomTooltip content={r.error}>
              <span className="line-clamp-1 max-w-[280px] text-xs text-destructive">{r.error}</span>
            </CustomTooltip>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        width: 'w-[150px]',
        render: (_v, r) => {
          const isActive = resolvedActiveRunId === r.id;
          const disabled = r.status !== 'ready' || isActive || !!activatingId;
          return (
            <CustomButton
              type={isActive ? 'default' : 'primary'}
              size="sm"
              disabled={disabled}
              loading={activatingId === r.id}
              onClick={() => handleActivate(r)}
            >
              {isActive ? 'Serving' : 'Set active'}
            </CustomButton>
          );
        },
      },
    ],
    [resolvedActiveRunId, activatingId, evalSummariesByIngestion],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 py-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Ingestion runs</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Every ingestion attempt — parser, tokeniser, embedder, and store. The active run is what
            live retrieval reads.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {total > 0 && (
            <Badge variant="secondary" className="text-xs tabular-nums">
              {total}
            </Badge>
          )}
          <CustomButton
            type="default"
            size="sm"
            onClick={() => setManualEvalsOpen(true)}
            aria-label="Manage eval questions"
          >
            <ListChecks className="mr-1 size-4" />
            Manage evals
          </CustomButton>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={runs}
          rowKey="id"
          loading={isLoading}
          searchable
          searchPlaceholder="Search parser, model, job id, error…"
          searchValue={search}
          onSearchChange={(v) => {
            setSearch(v);
            setPage(1);
          }}
          onSortChange={(next) => {
            if (next) setSort(next);
          }}
          initialSort={sort}
          pagination={{
            current: page,
            pageSize,
            total,
            pageSizeOptions: [10, 20, 50, 100],
            onChange: (p, size) => {
              setPage(p);
              setPageSize(size);
            },
          }}
          emptyState={
            <div className="py-10 text-center text-sm text-muted-foreground">
              No ingestion runs yet.
            </div>
          }
        />
      </div>

      <EvalResultsDrawer
        open={drawerRun !== null}
        onClose={() => setDrawerRun(null)}
        uploadId={uploadId}
        ingestionRun={drawerRun}
      />

      <ManualEvalsModal
        open={manualEvalsOpen}
        onClose={() => setManualEvalsOpen(false)}
        uploadId={uploadId}
      />
    </div>
  );
}
