'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useAtom } from 'jotai';
import {
  AlertTriangle,
  BookOpen,
  Calendar,
  ExternalLink,
  FileText,
  HardDrive,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
  User,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import agentsAtom, { fetchAllAgentsAtom } from '@/atoms/AgentsAtom';
import DocumentUpload from '@/components/knowledge-base/DocumentUpload';
import EditDocument from '@/components/knowledge-base/EditDocument';
import { PageHeader } from '@/components/layout/page-header';
import { CustomButton, CustomModal, CustomTable } from '@/components/shared';
import SearchBar from '@/components/shared/SearchBar';
import SelectInput from '@/components/shared/SelectInput';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  KNOWLEDGE_BASE_QUERY_KEY,
  knowledgeBaseApi,
  useDeleteKnowledgeBase,
  useKnowledgeBase,
  useReprocessKnowledgeBase,
} from '@/lib/api/knowledge-base';
import { KNOWLEDGE_BASE_STATUS_OPTIONS } from '@/lib/constants/filters';
import type { AgentDropdownItem } from '@/types/agent';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

// Single-accent design: file-type chips are neutral and read as mono labels.
// The type is signal-free, so it carries no color — only the status dot does.
const NEUTRAL_CHIP = 'border border-border bg-background text-muted-foreground';

const contentTypeLabels: Record<string, string> = {
  'application/pdf': 'PDF',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
  'text/plain': 'TXT',
  'text/csv': 'CSV',
  'text/html': 'HTML',
  'application/json': 'JSON',
};

function getTypeBadge(contentType?: string | null) {
  if (!contentType) return { label: 'FILE', color: NEUTRAL_CHIP };
  const label =
    contentTypeLabels[contentType] ?? contentType.split('/').pop()?.toUpperCase() ?? 'FILE';
  return { label, color: NEUTRAL_CHIP };
}

/** Extract the human-readable failure reason stored on a failed upload. */
function getErrorMessage(doc: Pick<KnowledgeBaseDocument, 'meta_data'>): string | null {
  const error = doc.meta_data?.error;
  return typeof error === 'string' && error.trim() ? error : null;
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Visual-only truncation for long file names. Keeps the extension visible and
// shows an ellipsis in the middle: e.g. "Voice AI Testing Platfo…uation.pdf".
// The underlying value is never mutated — pair with title={fullName} for hover.
function truncateFileName(name: string, max = 48): string {
  if (!name || name.length <= max) return name;
  const dotIdx = name.lastIndexOf('.');
  const hasExt = dotIdx > -1 && dotIdx >= name.length - 6 && dotIdx < name.length - 1;
  const ext = hasExt ? name.slice(dotIdx) : '';
  const base = hasExt ? name.slice(0, dotIdx) : name;
  const room = Math.max(max - ext.length - 1, 8); // 1 = ellipsis char
  const head = Math.ceil(room * 0.65);
  const tail = Math.max(room - head, 4);
  return `${base.slice(0, head)}…${base.slice(-tail)}${ext}`;
}

type StatusKey = KnowledgeBaseDocument['status'];

const statusDot: Record<StatusKey, string> = {
  ready: 'bg-emerald-500',
  processing: 'bg-amber-500 animate-pulse',
  failed: 'bg-destructive',
};

const statusConfig: Record<StatusKey, { label: string; className: string }> = {
  ready: {
    label: 'Active',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
  },
  processing: {
    label: 'Processing',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
  },
  failed: {
    label: 'Failed',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
  },
};

const PAGE_SIZE_OPTIONS = [10, 20, 50];

export default function KnowledgeBasePage() {
  const queryClient = useQueryClient();

  const [agentData] = useAtom(agentsAtom);
  const [, fetchAgents] = useAtom(fetchAllAgentsAtom);
  const hasFetchedAgentsRef = useRef(false);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState('-updated_at');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeBaseDocument | null>(null);
  const [editTarget, setEditTarget] = useState<KnowledgeBaseDocument | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBaseDocument | null>(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const queryParams = useMemo(
    () => ({
      page,
      page_size: pageSize,
      sort_by: sortBy,
      search: search || undefined,
      status: statusFilter && statusFilter !== 'all' ? statusFilter : undefined,
    }),
    [page, pageSize, sortBy, search, statusFilter],
  );

  const { data, isLoading } = useKnowledgeBase(queryParams);
  const documents = data?.items ?? [];
  const total = data?.total ?? 0;

  const deleteMutation = useDeleteKnowledgeBase();
  const reprocessMutation = useReprocessKnowledgeBase();
  const [reprocessingId, setReprocessingId] = useState<string | null>(null);

  useEffect(() => {
    if (hasFetchedAgentsRef.current) return;
    hasFetchedAgentsRef.current = true;
    fetchAgents().catch(() => {
      // agents endpoint may be disabled; the upload modal will show an empty list
    });
  }, [fetchAgents]);

  const agentNameMap = useMemo(() => {
    const map = new Map<string, string>();
    agentData.agentList.forEach((a: AgentDropdownItem) => {
      if (a.uuid) map.set(a.uuid, a.name);
      if (a.id != null) map.set(String(a.id), a.name);
    });
    return map;
  }, [agentData.agentList]);

  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    setPage(1);
  }, []);

  const handleStatusFilter = useCallback((value: string) => {
    setStatusFilter(value);
    setPage(1);
  }, []);

  const handleSortChange = useCallback((sort: CustomTableSortState | null) => {
    if (!sort) {
      setSortBy('-updated_at');
    } else {
      setSortBy(sort.order === 'desc' ? `-${sort.field}` : sort.field);
    }
    setPage(1);
  }, []);

  const handlePageChange = useCallback((nextPage: number, nextPageSize: number) => {
    setPage(nextPage);
    setPageSize(nextPageSize);
  }, []);

  const toggleRow = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAllRows = useCallback(() => {
    setSelectedIds((prev) => {
      if (documents.length > 0 && documents.every((d) => prev.has(d.id))) {
        return new Set();
      }
      return new Set(documents.map((d) => d.id));
    });
  }, [documents]);

  const allRowsSelected = documents.length > 0 && documents.every((d) => selectedIds.has(d.id));
  const someRowsSelected = !allRowsSelected && documents.some((d) => selectedIds.has(d.id));

  const handleEditSaved = useCallback(
    (updated?: KnowledgeBaseDocument) => {
      if (updated && selectedDoc?.id === updated.id) {
        setSelectedDoc(updated);
      }
      setEditTarget(null);
    },
    [selectedDoc],
  );

  const handleSingleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      showToast.success('Document deleted');
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(deleteTarget.id);
        return next;
      });
      if (selectedDoc?.id === deleteTarget.id) setSelectedDoc(null);
      setDeleteTarget(null);
    } catch (error) {
      handleApiError(error);
    }
  }, [deleteTarget, deleteMutation, selectedDoc]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setBulkDeleting(true);
    const ids = Array.from(selectedIds);
    const results = await Promise.allSettled(ids.map((id) => knowledgeBaseApi.delete(id)));
    const failed = results.filter((r) => r.status === 'rejected').length;
    queryClient.invalidateQueries({ queryKey: [KNOWLEDGE_BASE_QUERY_KEY] });
    setBulkDeleting(false);
    setBulkDeleteOpen(false);

    if (failed === 0) {
      showToast.success(ids.length === 1 ? 'Document deleted' : `${ids.length} documents deleted`);
      setSelectedIds(new Set());
    } else if (failed === ids.length) {
      showToast.error('Bulk delete failed', 'No documents were deleted.');
    } else {
      const deleted = ids.length - failed;
      showToast.error(
        'Partial delete',
        `${deleted} of ${ids.length} deleted. ${failed} failed — refresh and try again.`,
      );
      // Keep failed selections for retry
      const failedIds = new Set<string>();
      results.forEach((r, i) => {
        if (r.status === 'rejected') failedIds.add(ids[i]);
      });
      setSelectedIds(failedIds);
    }
  }, [selectedIds, queryClient]);

  const handleUploadSuccess = useCallback(() => {
    setUploadModalOpen(false);
    queryClient.invalidateQueries({ queryKey: [KNOWLEDGE_BASE_QUERY_KEY] });
  }, [queryClient]);

  const handleReprocess = useCallback(
    async (doc: KnowledgeBaseDocument) => {
      if (reprocessingId) return;
      setReprocessingId(doc.id);
      try {
        const updated = await reprocessMutation.mutateAsync(doc.id);
        showToast.success('Retrying', 'Document processing has been restarted.');
        // Keep the detail modal in sync if it's open on this document. Merge so
        // fields not returned by the reprocess endpoint (e.g. agent_id) survive.
        setSelectedDoc((prev) => (prev && prev.id === doc.id ? { ...prev, ...updated } : prev));
      } catch (error) {
        handleApiError(error);
      } finally {
        setReprocessingId(null);
      }
    },
    [reprocessMutation, reprocessingId],
  );

  const columns = useMemo<CustomTableColumn<KnowledgeBaseDocument>[]>(
    () => [
      {
        key: 'select',
        title: (
          <Checkbox
            checked={allRowsSelected ? true : someRowsSelected ? 'indeterminate' : false}
            onCheckedChange={toggleAllRows}
            aria-label="Select all"
          />
        ),
        width: 'w-12',
        render: (_value, record) => (
          <Checkbox
            checked={selectedIds.has(record.id)}
            onCheckedChange={() => toggleRow(record.id)}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select ${record.file_name}`}
          />
        ),
      },
      {
        key: 'file_name',
        title: 'Name / Type',
        dataIndex: 'file_name',
        sorter: true,
        render: (_value, record) => {
          const badge = getTypeBadge(record.file_type);
          return (
            <div className="flex min-w-0 items-center gap-3">
              <div className="relative flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted/60 ring-1 ring-border">
                <FileText className="size-4 text-muted-foreground" />
                <span
                  className={cn(
                    'absolute -right-0.5 -top-0.5 inline-flex h-2 w-2 rounded-full ring-2 ring-background',
                    statusDot[record.status] ?? statusDot.processing,
                  )}
                  aria-hidden
                />
              </div>
              <div className="flex min-w-0 flex-col">
                <div className="flex items-center gap-2">
                  <span
                    className="truncate text-sm font-medium text-foreground"
                    title={record.file_name}
                  >
                    {truncateFileName(record.file_name)}
                  </span>
                  <span
                    className={cn(
                      'shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase leading-none tracking-wider',
                      badge.color,
                    )}
                  >
                    {badge.label}
                  </span>
                </div>
                <span className="truncate text-xs text-muted-foreground">
                  {agentNameMap.get(record.agent_id ?? '') ?? 'Unknown agent'}
                </span>
              </div>
            </div>
          );
        },
      },
      {
        key: 'size_bytes',
        title: 'Size',
        dataIndex: 'size_bytes',
        sorter: true,
        width: 'w-[110px]',
        render: (value) => (
          <span className="text-sm tabular-nums text-muted-foreground">
            {formatFileSize(value as number)}
          </span>
        ),
      },
      {
        key: 'status',
        title: 'Status',
        dataIndex: 'status',
        sorter: true,
        width: 'w-[130px]',
        render: (_value, record) => {
          const cfg = statusConfig[record.status] ?? statusConfig.processing;
          const errorMsg = record.status === 'failed' ? getErrorMessage(record) : null;
          return (
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
                cfg.className,
              )}
              title={errorMsg ?? undefined}
            >
              <span className={cn('h-1.5 w-1.5 rounded-full', statusDot[record.status])} />
              {cfg.label}
            </span>
          );
        },
      },
      {
        key: 'updated_at',
        title: 'Last updated',
        dataIndex: 'updated_at',
        sorter: true,
        width: 'w-[200px]',
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
        key: 'actions',
        title: '',
        align: 'right',
        width: 'w-[96px]',
        render: (_value, record) => (
          <div className="flex items-center justify-end gap-0.5">
            {record.status === 'failed' && (
              <CustomButton
                type="text"
                size="icon-xs"
                disabled={!!reprocessingId}
                onClick={(e) => {
                  e.stopPropagation();
                  handleReprocess(record);
                }}
                aria-label="Retry processing"
                className="text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <RotateCcw
                  className={cn('size-4', reprocessingId === record.id && 'animate-spin')}
                />
              </CustomButton>
            )}
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                setEditTarget(record);
              }}
              aria-label="Edit document"
              className="text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <Pencil className="size-4" />
            </CustomButton>
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                setDeleteTarget(record);
              }}
              aria-label="Delete document"
              className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            >
              <Trash2 className="size-4" />
            </CustomButton>
          </div>
        ),
      },
    ],
    [
      allRowsSelected,
      someRowsSelected,
      toggleAllRows,
      selectedIds,
      toggleRow,
      agentNameMap,
      handleReprocess,
      reprocessingId,
    ],
  );

  const detailBadge = selectedDoc ? getTypeBadge(selectedDoc.file_type) : null;
  const detailStatus = selectedDoc
    ? (statusConfig[selectedDoc.status] ?? statusConfig.processing)
    : null;
  const detailError =
    selectedDoc && selectedDoc.status === 'failed' ? getErrorMessage(selectedDoc) : null;

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-6">
      {/* ─── header ───────────────────────────────────────────────────── */}
      <PageHeader
        kicker="Knowledge base"
        title={
          <span className="inline-flex items-center gap-3">
            Knowledge base.
            {total > 0 && (
              <span className="font-mono text-[13px] font-medium tabular-nums tracking-normal text-muted-foreground">
                {total}
              </span>
            )}
          </span>
        }
        description="Upload documents to enhance your AI agents with custom knowledge."
        actions={
          <CustomButton
            type="primary"
            icon={<Plus className="size-4" />}
            onClick={() => setUploadModalOpen(true)}
          >
            Add Sources
          </CustomButton>
        }
      />

      {/* ─── toolbar ──────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <SearchBar
          placeholder="Search documents by name…"
          value={search}
          onSearch={handleSearch}
          debounceMs={400}
          containerClassName="max-w-xs flex-1"
        />
        <SelectInput
          name="status-filter"
          options={KNOWLEDGE_BASE_STATUS_OPTIONS}
          value={statusFilter}
          onValueChange={handleStatusFilter}
          placeholder="All statuses"
          size="sm"
          triggerClassName="min-w-[160px]"
        />
      </div>

      {/* ─── table ────────────────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={isLoading}
          onRowClick={(record) => setSelectedDoc(record)}
          onSortChange={handleSortChange}
          initialSort={{ field: 'updated_at', order: 'desc' }}
          pagination={{
            current: page,
            pageSize,
            total,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            onChange: handlePageChange,
          }}
          emptyState={
            <EmptyState
              onAdd={() => setUploadModalOpen(true)}
              hasFilter={!!search || statusFilter !== 'all'}
            />
          }
        />
      </div>

      {/* ─── floating selection bar ───────────────────────────────────── */}
      <SelectionBar
        count={selectedIds.size}
        onClear={() => setSelectedIds(new Set())}
        onDelete={() => setBulkDeleteOpen(true)}
      />

      {/* ─── modals ───────────────────────────────────────────────────── */}
      <CustomModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        title="Add sources"
        description="Pick an agent, drop in one or more files."
        width="sm:max-w-lg"
        hideFooter
      >
        <DocumentUpload
          agents={agentData.agentList}
          agentsLoading={false}
          onUploadSuccess={handleUploadSuccess}
        />
      </CustomModal>

      <CustomModal
        open={!!selectedDoc}
        onClose={() => setSelectedDoc(null)}
        title="Document details"
        width="sm:max-w-lg"
        footer={
          <div className="flex w-full items-center justify-between">
            <CustomButton
              type="danger"
              icon={<Trash2 className="size-4" />}
              onClick={() => {
                if (selectedDoc) setDeleteTarget(selectedDoc);
              }}
            >
              Delete
            </CustomButton>
            <div className="flex items-center gap-2">
              <CustomButton
                type="default"
                icon={<Pencil className="size-4" />}
                onClick={() => {
                  if (selectedDoc) setEditTarget(selectedDoc);
                }}
              >
                Edit
              </CustomButton>
              {selectedDoc?.url && (
                <CustomButton
                  type="default"
                  icon={<ExternalLink className="size-4" />}
                  onClick={() => window.open(selectedDoc.url ?? '', '_blank')}
                >
                  View file
                </CustomButton>
              )}
            </div>
          </div>
        }
      >
        {selectedDoc && (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-background">
                <FileText className="size-5 text-foreground" />
              </div>
              <div className="min-w-0 flex-1">
                <p
                  className="break-all text-sm font-semibold text-foreground"
                  title={selectedDoc.file_name}
                >
                  {truncateFileName(selectedDoc.file_name, 72)}
                </p>
                <div className="mt-1 flex items-center gap-2">
                  {detailBadge && (
                    <span
                      className={cn(
                        'inline-flex rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase leading-none tracking-wider',
                        detailBadge.color,
                      )}
                    >
                      {detailBadge.label}
                    </span>
                  )}
                  {detailStatus && (
                    <Badge className={detailStatus.className}>{detailStatus.label}</Badge>
                  )}
                </div>
              </div>
            </div>

            {detailError && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/10 px-3.5 py-3"
              >
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium text-destructive">Processing failed</p>
                  <p className="mt-0.5 break-words text-[13px] text-destructive/90">
                    {detailError}
                  </p>
                  <CustomButton
                    type="default"
                    size="sm"
                    icon={
                      <RotateCcw
                        className={cn(
                          'size-4',
                          reprocessingId === selectedDoc.id && 'animate-spin',
                        )}
                      />
                    }
                    disabled={!!reprocessingId}
                    onClick={() => handleReprocess(selectedDoc)}
                    className="mt-2.5"
                  >
                    Retry processing
                  </CustomButton>
                </div>
              </div>
            )}

            <div className="rounded-xl border border-border bg-muted/20">
              <DetailRow
                icon={<User className="size-4" />}
                label="Agent"
                value={agentNameMap.get(selectedDoc.agent_id ?? '') ?? 'Unknown agent'}
              />
              <DetailRow
                icon={<HardDrive className="size-4" />}
                label="File size"
                value={formatFileSize(selectedDoc.size_bytes)}
              />
              <DetailRow
                icon={<Calendar className="size-4" />}
                label="Uploaded"
                value={formatDate(selectedDoc.created_at)}
              />
              <DetailRow
                icon={<Calendar className="size-4" />}
                label="Last updated"
                value={formatDate(selectedDoc.updated_at)}
                last
              />
            </div>
          </div>
        )}
      </CustomModal>

      {/* Edit modal — rename and/or replace the underlying file */}
      <CustomModal
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        title="Edit document"
        description="Rename the document and optionally replace the underlying file."
        width="sm:max-w-lg"
        hideFooter
      >
        {editTarget && <EditDocument document={editTarget} onSaved={handleEditSaved} />}
      </CustomModal>

      <CustomModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete document"
        description={`Are you sure you want to delete "${deleteTarget?.file_name}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deleteMutation.isPending}
        onConfirm={handleSingleDelete}
      />

      <CustomModal
        open={bulkDeleteOpen}
        onClose={() => setBulkDeleteOpen(false)}
        title="Delete documents"
        description={
          selectedIds.size === 1
            ? 'Delete 1 selected document? This action cannot be undone.'
            : `Delete ${selectedIds.size} selected documents? This action cannot be undone.`
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={bulkDeleting}
        onConfirm={handleBulkDelete}
      />
    </div>
  );
}

// ─── tiny presentational helpers ────────────────────────────────────────────
function DetailRow({
  icon,
  label,
  value,
  last,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div className={cn('flex items-center gap-3 px-4 py-3', !last && 'border-b border-border/60')}>
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-[13px] text-muted-foreground">{label}</span>
      <span className="ml-auto truncate text-[13px] font-medium text-foreground">{value}</span>
    </div>
  );
}

function EmptyState({ onAdd, hasFilter }: { onAdd: () => void; hasFilter: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-background">
        <BookOpen className="size-6 text-foreground" />
      </div>
      <div className="max-w-sm text-center">
        <p className="font-semibold text-foreground">
          {hasFilter ? 'No matching documents' : 'No documents yet'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try clearing the search or status filter.'
            : 'Upload your first document to build your knowledge base.'}
        </p>
      </div>
      {!hasFilter && (
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={onAdd}>
          Add Sources
        </CustomButton>
      )}
    </div>
  );
}

function SelectionBar({
  count,
  onClear,
  onDelete,
}: {
  count: number;
  onClear: () => void;
  onDelete: () => void;
}) {
  const open = count > 0;
  return (
    <div
      className={cn(
        'pointer-events-none fixed bottom-6 left-1/2 z-40 -translate-x-1/2 transition-all duration-300',
        open ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0',
      )}
      aria-hidden={!open}
    >
      <div className="pointer-events-auto flex items-center gap-3 rounded-2xl border border-border bg-card/95 px-3 py-2 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <span className="ml-2 inline-flex h-6 min-w-[1.5rem] items-center justify-center rounded-full bg-primary/15 px-2 text-xs font-semibold text-primary">
          {count}
        </span>
        <span className="text-sm text-muted-foreground">
          {count === 1 ? 'document selected' : 'documents selected'}
        </span>
        <div className="mx-1 h-5 w-px bg-border" />
        <CustomButton type="text" size="sm" icon={<X className="size-3.5" />} onClick={onClear}>
          Clear
        </CustomButton>
        <CustomButton
          type="danger"
          size="sm"
          icon={<Trash2 className="size-3.5" />}
          onClick={onDelete}
        >
          Delete
        </CustomButton>
      </div>
    </div>
  );
}
