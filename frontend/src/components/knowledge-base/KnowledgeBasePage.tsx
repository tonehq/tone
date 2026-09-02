'use client';

import { useAtom } from 'jotai';
import {
  AlertTriangle,
  Calendar,
  ExternalLink,
  FileText,
  HardDrive,
  ListChecks,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
  User,
} from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import agentsAtom, { fetchAllAgentsAtom } from '@/atoms/AgentsAtom';
import DetailRow from '@/components/knowledge-base/DetailRow';
import DocumentUpload from '@/components/knowledge-base/DocumentUpload';
import EditDocument from '@/components/knowledge-base/EditDocument';
import KnowledgeBaseEmptyState from '@/components/knowledge-base/KnowledgeBaseEmptyState';
import {
  CustomButton,
  CustomModal,
  CustomTable,
  FacetFilterBar,
  FacetFilterDrawer,
  IconChip,
  SelectionBar,
  useFacetedList,
} from '@/components/shared';
import { statusConfig, statusDot } from '@/components/knowledge-base/knowledgeBaseConstants';
import {
  formatFileSize,
  getTypeBadge,
  truncateFileName,
} from '@/components/knowledge-base/knowledgeBaseHelpers';
import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import { knowledgeBaseListConfig } from '@/components/knowledge-base/knowledgeBaseListConfig';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  knowledgeBaseApi,
  useDeleteKnowledgeBase,
  useReprocessKnowledgeBase,
} from '@/lib/api/knowledge-base';
import type { AgentDropdownItem } from '@/types/agent';
import type { CustomTableColumn } from '@/types/components';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/** Extract the human-readable failure reason stored on a failed upload. */
function getErrorMessage(doc: Pick<KnowledgeBaseDocument, 'meta_data'>): string | null {
  return formatIngestionError(doc.meta_data?.error);
}

export default function KnowledgeBasePage() {
  const [agentData] = useAtom(agentsAtom);
  const [, fetchAgents] = useAtom(fetchAllAgentsAtom);
  const hasFetchedAgentsRef = useRef(false);

  const fl = useFacetedList(knowledgeBaseListConfig);
  const documents = fl.rows;
  const total = fl.total;

  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeBaseDocument | null>(null);
  const [editTarget, setEditTarget] = useState<KnowledgeBaseDocument | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBaseDocument | null>(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

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
      fl.refresh();
    } catch (error) {
      handleApiError(error);
    }
  }, [deleteTarget, deleteMutation, selectedDoc, fl]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setBulkDeleting(true);
    const ids = Array.from(selectedIds);
    const results = await Promise.allSettled(ids.map((id) => knowledgeBaseApi.delete(id)));
    const failed = results.filter((r) => r.status === 'rejected').length;
    fl.refresh();
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
  }, [selectedIds, fl]);

  const handleUploadSuccess = useCallback(() => {
    setUploadModalOpen(false);
    fl.refresh();
  }, [fl]);

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
        // Reflect the status flip immediately; pollWhile keeps it fresh after.
        fl.refresh();
      } catch (error) {
        handleApiError(error);
      } finally {
        setReprocessingId(null);
      }
    },
    [reprocessMutation, reprocessingId, fl],
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
                      'shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase leading-none tracking-wider',
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
            <Link
              href={`/knowledge-base/${record.id}`}
              aria-label="View ingestion runs"
              onClick={(e) => e.stopPropagation()}
            >
              <CustomButton
                type="text"
                size="icon-xs"
                className="text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <ListChecks className="size-4" />
              </CustomButton>
            </Link>
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

  const handleDetailDelete = () => {
    if (selectedDoc) setDeleteTarget(selectedDoc);
  };

  const handleDetailEdit = () => {
    if (selectedDoc) setEditTarget(selectedDoc);
  };

  return (
    <div className="animate-page mx-auto flex h-full min-h-0 w-full max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.34em] text-muted-foreground">
            Build
          </p>
          <div className="flex items-baseline gap-3">
            <h1 className="font-display text-[clamp(2rem,3.4vw,2.75rem)] font-semibold leading-none tracking-[-0.04em] text-foreground">
              Knowledge Base
            </h1>
            {total > 0 && (
              <span className="font-mono text-[13px] tabular-nums text-muted-foreground">
                {total}
              </span>
            )}
          </div>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Upload documents to enhance your AI agents with custom knowledge.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus size={15} />}
          className="h-10"
          onClick={() => setUploadModalOpen(true)}
        >
          Add sources
        </CustomButton>
      </div>

      {/* ─── toolbar ──────────────────────────────────────────────────── */}
      <FacetFilterBar
        fields={fl.tokenFields}
        tokens={fl.tokens}
        onTokensChange={fl.setTokens}
        onClear={fl.clearAll}
        showClear={fl.hasActiveFilters}
        placeholder="Search documents… (e.g. name:resort, status:ready)"
        drawerFilterCount={fl.drawerFilterCount}
        onOpenDrawer={() => setFilterDrawerOpen(true)}
      />

      {/* ─── table ────────────────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={fl.listLoading}
          loadingLabel="Loading documents"
          onRowClick={(record) => setSelectedDoc(record)}
          onSortChange={fl.handleSortChange}
          initialSort={knowledgeBaseListConfig.defaultSort ?? undefined}
          pagination={{
            current: fl.page,
            pageSize: fl.pageSize,
            total,
            pageSizeOptions: fl.pageSizeOptions,
            onChange: fl.handlePaginationChange,
          }}
          emptyState={
            <KnowledgeBaseEmptyState
              onAdd={() => setUploadModalOpen(true)}
              hasFilter={fl.hasActiveFilters}
            />
          }
        />
      </div>

      {/* ─── filter drawer ────────────────────────────────────────────── */}
      <FacetFilterDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        description="Filter documents by status."
        sections={knowledgeBaseListConfig.facetSections}
        value={fl.facetSelections}
        facets={fl.facets}
        facetsLoading={fl.facetsLoading}
        onApply={fl.applyDrawer}
      />

      {/* ─── floating selection bar ───────────────────────────────────── */}
      <SelectionBar
        count={selectedIds.size}
        onClear={() => setSelectedIds(new Set())}
        onDelete={() => setBulkDeleteOpen(true)}
        singular="document"
        plural="documents"
      />

      {/* ─── modals ───────────────────────────────────────────────────── */}
      <CustomModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        title="Add sources"
        description="Drop in one or more files. Assigning an agent is optional."
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
              onClick={handleDetailDelete}
            >
              Delete
            </CustomButton>
            <div className="flex items-center gap-2">
              <CustomButton
                type="default"
                icon={<Pencil className="size-4" />}
                onClick={handleDetailEdit}
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
              {selectedDoc && (
                <Link href={`/knowledge-base/${selectedDoc.id}`}>
                  <CustomButton type="default" icon={<ListChecks className="size-4" />}>
                    Ingestion runs
                  </CustomButton>
                </Link>
              )}
            </div>
          </div>
        }
      >
        {selectedDoc && (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <IconChip icon={<FileText strokeWidth={1.75} />} tone="primary" size="lg" />
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
                        'inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider leading-none',
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
