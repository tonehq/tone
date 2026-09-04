'use client';

import { useMemo, useState } from 'react';
import { CheckCircle2, Clock, Copy, Loader2, Play, Plus, Trash2, XCircle } from 'lucide-react';

import { CustomButton, CustomTable, CustomTooltip } from '@/components/shared';
import CustomModal from '@/components/shared/CustomModal';
import EvalResultsDrawer from '@/components/knowledge-base/EvalResultsDrawer';
import EvalsCell from '@/components/knowledge-base/EvalsCell';
import IngestionChunksDrawer from '@/components/knowledge-base/IngestionChunksDrawer';
import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import NewIngestionRunModal from '@/components/knowledge-base/NewIngestionRunModal';
import { Badge } from '@/components/ui/badge';
import { useEvalSummariesByIngestion, useTriggerEvalRun } from '@/lib/api/evals';
import {
  useActivateIngestionRun,
  useDeleteIngestionRun,
  useIngestionRuns,
} from '@/lib/api/ingestion-runs';
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

  const deleteRun = useDeleteIngestionRun(uploadId);
  // The run awaiting delete confirmation (drives the confirm modal). Null when
  // the modal is closed.
  const [deleteTarget, setDeleteTarget] = useState<IngestionRun | null>(null);

  const runEvalsMutation = useTriggerEvalRun(uploadId);
  // Track which row is currently kicking off an eval so per-row loading state
  // is per-row (the mutation is shared across all rows via the hook binding).
  // Single-flight so a user doesn't stampede the eval queue by mashing buttons.
  const [runningEvalId, setRunningEvalId] = useState<string | null>(null);

  const [drawerRun, setDrawerRun] = useState<IngestionRun | null>(null);
  const [chunksDrawerRun, setChunksDrawerRun] = useState<IngestionRun | null>(null);
  const [newRunOpen, setNewRunOpen] = useState(false);

  const runs = data?.data ?? [];
  const total = data?.total ?? 0;

  // Batch-fetch the latest eval-batch summary for every visible ingestion run
  // so the "Evals" column paints in one query instead of N. Memo the derived
  // map so its identity is stable across renders — otherwise the {} fallback
  // on the loading tick invalidates the columns useMemo on every render.
  const visibleRunIds = useMemo(() => runs.map((r) => r.id), [runs]);
  const { data: evalSummariesResp } = useEvalSummariesByIngestion(uploadId, visibleRunIds);
  const evalSummariesByIngestion = useMemo(
    () => evalSummariesResp?.items ?? {},
    [evalSummariesResp],
  );
  // Ingestion runs whose eval batch is queued/running (no score row yet). The
  // hook polls while this is non-empty; the "Evals" cell shows a spinner.
  const inFlightEvalRunIds = useMemo(
    () => new Set(evalSummariesResp?.in_flight_ingestion_run_ids ?? []),
    [evalSummariesResp],
  );

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

  const handleRunEvals = async (run: IngestionRun) => {
    if (runningEvalId) return;
    setRunningEvalId(run.id);
    try {
      await runEvalsMutation.mutateAsync({ ingestion_run_id: run.id });
      showToast.success(
        'Evals queued',
        `Scoring run #${run.run_number} — the chip will update once results land.`,
      );
    } catch (error) {
      handleApiError(error);
    } finally {
      setRunningEvalId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteRun.mutateAsync(deleteTarget.id);
      showToast.success(
        'Run deleted',
        `Run #${deleteTarget.run_number} and its chunks and evaluation results were removed.`,
      );
      setDeleteTarget(null);
    } catch (error) {
      // Surfaces the backend 409 message ("activate another run first") too.
      handleApiError(error);
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
            #{value as number}
          </span>
        ),
      },
      {
        key: 'ingestion_config',
        title: 'Config',
        width: 'w-[180px]',
        render: (_v, r) =>
          r.ingestion_config_name ? (
            <CustomTooltip content={r.ingestion_config_name}>
              <span
                onClick={(e) => e.stopPropagation()}
                className="line-clamp-1 max-w-[170px] text-sm text-foreground"
              >
                {r.ingestion_config_name}
              </span>
            </CustomTooltip>
          ) : (
            <span className="text-sm italic text-muted-foreground">Custom</span>
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
          // For error rows the pill is a tooltip trigger — the user is clicking
          // to inspect the error, not to open the chunks drawer. Non-error
          // pills stay inert (no stopPropagation) so the row-click still fires.
          const friendlyError = formatIngestionError(record.error);
          const pillClass = cn(
            'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
            s.className,
          );
          if (friendlyError) {
            return (
              <CustomTooltip
                content={
                  <div className="max-h-40 max-w-xs overflow-auto whitespace-pre-wrap break-words text-xs leading-snug">
                    {friendlyError}
                  </div>
                }
              >
                <span onClick={(e) => e.stopPropagation()} className={pillClass}>
                  {s.icon}
                  {s.label}
                </span>
              </CustomTooltip>
            );
          }
          return (
            <span className={pillClass}>
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
        render: (_v, r) => (
          <EvalsCell
            summary={evalSummariesByIngestion[r.id]}
            isInFlight={inFlightEvalRunIds.has(r.id)}
            onView={() => setDrawerRun(r)}
          />
        ),
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
            <CustomButton
              type="text"
              size="xs"
              icon={<Copy className="size-3" />}
              onClick={(e) => {
                e.stopPropagation();
                copyJobId(r.procrastinate_job_id as number);
              }}
              title="Copy job id"
              className="h-auto gap-1 px-0 text-xs tabular-nums text-muted-foreground hover:bg-transparent hover:text-foreground"
            >
              {r.procrastinate_job_id}
            </CustomButton>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'error',
        title: 'Error',
        render: (_v, r) => {
          const friendly = formatIngestionError(r.error);
          return friendly ? (
            <CustomTooltip
              content={
                <div className="max-h-40 max-w-xs overflow-auto whitespace-pre-wrap break-words text-xs leading-snug">
                  {friendly}
                </div>
              }
            >
              <span
                onClick={(e) => e.stopPropagation()}
                className="line-clamp-1 max-w-[280px] text-xs text-destructive"
              >
                {friendly}
              </span>
            </CustomTooltip>
          ) : (
            <span className="text-muted-foreground">—</span>
          );
        },
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        width: 'w-[240px]',
        render: (_v, r) => {
          const isActive = resolvedActiveRunId === r.id;
          const activateDisabled = r.status !== 'ready' || isActive || !!activatingId;
          // A batch is in flight for this row (enqueue call OR a queued/running
          // Procrastinate job the server reports) — show the button as busy.
          const runningEvals = runningEvalId === r.id || inFlightEvalRunIds.has(r.id);
          // A run must be ready before it can be scored — a
          // pending/running/failed run has nothing for retrieval to hit.
          // Single-flight across rows via runningEvalId; also block re-runs
          // while this row already has a batch in flight (see handleRunEvals).
          const evalsDisabled = r.status !== 'ready' || !!runningEvalId || runningEvals;
          return (
            // Fill the whole cell so clicks on the surrounding <td> padding
            // are also absorbed — otherwise clicking just off-target inside
            // the actions column bubbles to the row and opens the drawer.
            <div
              className="-mx-4 -my-3.5 flex items-center justify-end gap-1 px-4 py-3.5"
              onClick={(e) => e.stopPropagation()}
            >
              <CustomTooltip
                content={
                  r.status === 'ready'
                    ? 'Run evals against this run'
                    : 'Evals available once the run is ready'
                }
              >
                <CustomButton
                  type="text"
                  size="icon-xs"
                  aria-label="Run evals for this run"
                  disabled={evalsDisabled}
                  loading={runningEvals}
                  onClick={() => handleRunEvals(r)}
                >
                  {!runningEvals && <Play className="size-3.5" />}
                </CustomButton>
              </CustomTooltip>
              <CustomButton
                type={isActive ? 'default' : 'primary'}
                size="sm"
                disabled={activateDisabled}
                loading={activatingId === r.id}
                onClick={() => handleActivate(r)}
              >
                {isActive ? 'Serving' : 'Set active'}
              </CustomButton>
              <CustomTooltip
                content={
                  isActive
                    ? "Active run can't be deleted — activate another first."
                    : 'Delete this run'
                }
              >
                {/* Span wrapper keeps the tooltip working while the button is
                    disabled (a disabled button fires no pointer events). */}
                <span className="inline-flex">
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    aria-label="Delete this run"
                    disabled={isActive}
                    onClick={() => setDeleteTarget(r)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="size-3.5" />
                  </CustomButton>
                </span>
              </CustomTooltip>
            </div>
          );
        },
      },
    ],
    [
      resolvedActiveRunId,
      activatingId,
      runningEvalId,
      evalSummariesByIngestion,
      inFlightEvalRunIds,
    ],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 py-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-foreground">Ingestion runs</h2>
            {total > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {total}
              </Badge>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Every ingestion attempt — parser, tokeniser, embedder, and store. The active run is what
            live retrieval reads.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CustomButton
            type="primary"
            size="sm"
            onClick={() => setNewRunOpen(true)}
            aria-label="Start a new ingestion run"
          >
            <Plus className="mr-1 size-4" />
            New run
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
          onRowClick={(row) => setChunksDrawerRun(row)}
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

      <IngestionChunksDrawer
        open={chunksDrawerRun !== null}
        onClose={() => setChunksDrawerRun(null)}
        uploadId={uploadId}
        ingestionRun={chunksDrawerRun}
      />

      <NewIngestionRunModal
        open={newRunOpen}
        onClose={() => setNewRunOpen(false)}
        uploadId={uploadId}
      />

      <CustomModal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete ingestion run?"
        description="This permanently deletes this run's chunks and its evaluation results. The document's eval questions are kept. This can't be undone."
        confirmText="Delete run"
        cancelText="Cancel"
        confirmType="danger"
        confirmLoading={deleteRun.isPending}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
