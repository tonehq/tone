'use client';

import agentsAtom, { fetchAgentList } from '@/atoms/AgentsAtom';
import knowledgeBaseAtom, {
  deleteDocumentsAtom,
  fetchDocumentsAtom,
} from '@/atoms/KnowledgeBaseAtom';
import DocumentUpload from '@/components/knowledge-base/DocumentUpload';
import { CustomButton, CustomModal, CustomTable } from '@/components/shared';
import SearchBar from '@/components/shared/SearchBar';
import { Badge } from '@/components/ui/badge';
import type { ApiAgent } from '@/types/agent';
import type { CustomTableColumn } from '@/types/components';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import debounce from 'lodash/debounce';
import {
  BookOpen,
  Calendar,
  ExternalLink,
  FileText,
  HardDrive,
  Plus,
  Trash2,
  User,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const contentTypeBadgeColors: Record<string, { label: string; color: string }> = {
  'application/pdf': {
    label: 'PDF',
    color: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400',
  },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    label: 'DOCX',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400',
  },
  'text/plain': {
    label: 'TXT',
    color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  },
  'text/csv': {
    label: 'CSV',
    color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  },
  'application/json': {
    label: 'JSON',
    color: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  },
};

function getTypeBadge(contentType: string) {
  const config = contentTypeBadgeColors[contentType];
  if (config) return config;
  const ext = contentType.split('/').pop()?.toUpperCase() ?? 'FILE';
  return { label: ext, color: 'bg-muted text-muted-foreground' };
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  ready: {
    label: 'Active',
    className: 'bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/15 dark:text-emerald-400',
  },
  processing: {
    label: 'Processing',
    className: 'bg-amber-500/15 text-amber-600 hover:bg-amber-500/15 dark:text-amber-400',
  },
  failed: {
    label: 'Failed',
    className: 'bg-destructive/15 text-destructive hover:bg-destructive/15 dark:text-red-400',
  },
};

export default function KnowledgeBasePage() {
  const [data] = useAtom(knowledgeBaseAtom);
  const [agentData] = useAtom(agentsAtom);
  const [, fetchDocs] = useAtom(fetchDocumentsAtom);
  const [, fetchAgents] = useAtom(fetchAgentList);
  const [, removeDocs] = useAtom(deleteDocumentsAtom);

  const [loading, setLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeBaseDocument | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBaseDocument | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortParam, setSortParam] = useState('-updated_at');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const hasFetchedRef = useRef(false);

  const agentNameMap = useMemo(() => {
    const map = new Map<number, string>();
    agentData.agentList.forEach((a: ApiAgent) => map.set(a.id, a.name));
    return map;
  }, [agentData.agentList]);

  const fetchWithParams = useCallback(
    async (overrides?: { name?: string; sort?: string; page?: number; page_size?: number }) => {
      setLoading(true);
      try {
        await fetchDocs({
          sort: overrides?.sort ?? sortParam,
          name: overrides?.name ?? (searchQuery || undefined),
          page: overrides?.page ?? page,
          page_size: overrides?.page_size ?? pageSize,
        });
      } catch {
        // handled silently
      } finally {
        setLoading(false);
      }
    },
    [fetchDocs, sortParam, searchQuery, page, pageSize],
  );

  // Stable ref so the debounce closure always calls the latest fetchWithParams
  const fetchRef = useRef(fetchWithParams);
  fetchRef.current = fetchWithParams;

  // Debounced search — stable across re-renders
  const debouncedSearch = useMemo(
    () =>
      debounce((name: string) => {
        setPage(1);
        fetchRef.current({ name, page: 1 });
      }, 400),
    [],
  );

  // Cleanup debounce on unmount
  useEffect(() => () => debouncedSearch.cancel(), [debouncedSearch]);

  // Initial fetch
  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;

    const init = async () => {
      setLoading(true);
      try {
        await Promise.all([
          fetchDocs({ sort: '-updated_at', page: 1, page_size: 10 }),
          fetchAgents(),
        ]);
      } catch {
        // handled silently
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [fetchDocs, fetchAgents]);

  const handleSortChange = useCallback(
    (sort: { field: string; order: 'asc' | 'desc' } | null) => {
      const newSort = sort
        ? sort.order === 'desc'
          ? `-${sort.field}`
          : sort.field
        : '-updated_at';
      setSortParam(newSort);
      setPage(1);
      fetchWithParams({ sort: newSort, page: 1 });
    },
    [fetchWithParams],
  );

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setSearchQuery(value);
      debouncedSearch(value);
    },
    [debouncedSearch],
  );

  const handlePageChange = useCallback(
    (newPage: number, newPageSize: number) => {
      setPage(newPage);
      setPageSize(newPageSize);
      fetchWithParams({ page: newPage, page_size: newPageSize });
    },
    [fetchWithParams],
  );

  const handleUploadSuccess = useCallback(() => {
    setUploadModalOpen(false);
    fetchWithParams();
  }, [fetchWithParams]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await removeDocs([deleteTarget.id]);
      showToast.success('Document deleted');
      setDeleteTarget(null);
      if (selectedDoc?.id === deleteTarget.id) {
        setSelectedDoc(null);
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget, removeDocs, selectedDoc]);

  const handleRowClick = useCallback((record: KnowledgeBaseDocument) => {
    setSelectedDoc(record);
  }, []);

  const handleDeleteFromDetail = useCallback(() => {
    if (!selectedDoc) return;
    setDeleteTarget(selectedDoc);
  }, [selectedDoc]);

  const columns: CustomTableColumn<KnowledgeBaseDocument>[] = [
    {
      key: 'file_name',
      title: 'Name / Type',
      dataIndex: 'file_name',
      width: 'w-[40%]',
      render: (_value, record) => {
        const badge = getTypeBadge(record.content_type);
        return (
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center gap-2">
              <span className="font-medium text-foreground">{record.file_name}</span>
              <span
                className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase leading-none ${badge.color}`}
              >
                {badge.label}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
              {agentNameMap.get(record.agent_id) ?? `Agent #${record.agent_id}`}
            </span>
          </div>
        );
      },
    },
    {
      key: 'file_size_bytes',
      title: 'File Size',
      dataIndex: 'file_size_bytes',
      width: 'w-[120px]',
      render: (value) => (
        <span className="text-sm text-muted-foreground">{formatFileSize(value as number)}</span>
      ),
    },
    {
      key: 'updated_at',
      title: 'Last Updated',
      dataIndex: 'updated_at',
      sorter: true,
      width: 'w-[200px]',
      render: (value) =>
        value ? (
          <span className="text-sm text-muted-foreground">{formatDate(value as number)}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: 'actions',
      title: '',
      align: 'right',
      width: 'w-[60px]',
      render: (_value, record) => (
        <CustomButton
          type="text"
          size="icon-xs"
          onClick={(e) => {
            e.stopPropagation();
            setDeleteTarget(record);
          }}
          aria-label="Delete document"
          className="text-destructive hover:text-destructive/90"
        >
          <Trash2 className="size-4" />
        </CustomButton>
      ),
    },
  ];

  // Detail modal content
  const detailBadge = selectedDoc ? getTypeBadge(selectedDoc.content_type) : null;
  const detailStatus = selectedDoc
    ? (statusConfig[selectedDoc.status] ?? statusConfig.processing)
    : null;

  return (
    <div className="animate-page flex h-full flex-col p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Knowledge Base
            </h1>
            {data.pagination.total > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {data.pagination.total}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload documents to enhance your AI agents with custom knowledge.
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus />} onClick={() => setUploadModalOpen(true)}>
          Add Sources
        </CustomButton>
      </div>

      {/* Search bar */}
      <SearchBar
        placeholder="Search by name..."
        value={searchQuery}
        onChange={handleSearchChange}
        containerClassName="mb-4"
      />

      {/* Table */}
      <CustomTable
        columns={columns}
        dataSource={data.documents}
        rowKey="id"
        loading={loading}
        onRowClick={handleRowClick}
        onSortChange={handleSortChange}
        pagination={{
          current: page,
          pageSize,
          total: data.pagination.total,
          onChange: handlePageChange,
        }}
        emptyState={
          <div className="flex flex-col items-center gap-4 py-8">
            <div className="flex size-12 items-center justify-center rounded-xl bg-muted">
              <BookOpen className="size-6 text-muted-foreground" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-foreground">No documents yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Upload your first document to build your knowledge base.
              </p>
            </div>
            <CustomButton type="primary" icon={<Plus />} onClick={() => setUploadModalOpen(true)}>
              Add Sources
            </CustomButton>
          </div>
        }
      />

      {/* Upload modal */}
      <CustomModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        title="Upload Document"
        description="Select an agent and upload a file to add to its knowledge base."
        width="sm:max-w-lg"
        hideFooter
      >
        <DocumentUpload
          agents={agentData.agentList}
          agentsLoading={false}
          onUploadSuccess={handleUploadSuccess}
        />
      </CustomModal>

      {/* Document detail modal */}
      <CustomModal
        open={!!selectedDoc}
        onClose={() => setSelectedDoc(null)}
        title="Document Details"
        width="sm:max-w-lg"
        footer={
          <div className="flex w-full items-center justify-between">
            <CustomButton
              type="danger"
              icon={<Trash2 className="size-4" />}
              onClick={handleDeleteFromDetail}
            >
              Delete
            </CustomButton>
            {selectedDoc?.url && (
              <CustomButton
                type="default"
                icon={<ExternalLink className="size-4" />}
                onClick={() => window.open(selectedDoc.url, '_blank')}
              >
                View File
              </CustomButton>
            )}
          </div>
        }
      >
        {selectedDoc && (
          <div className="space-y-4">
            {/* File name + type badge */}
            <div className="flex items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <FileText className="size-5 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="break-all text-sm font-semibold text-foreground">
                  {selectedDoc.file_name}
                </p>
                <div className="mt-1 flex items-center gap-2">
                  {detailBadge && (
                    <span
                      className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase leading-none ${detailBadge.color}`}
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

            {/* Info rows */}
            <div className="rounded-lg border border-border">
              <div className="flex items-center gap-3 border-b border-border/60 px-4 py-3">
                <User className="size-4 shrink-0 text-muted-foreground" />
                <span className="text-[13px] text-muted-foreground">Agent</span>
                <span className="ml-auto text-[13px] font-medium text-foreground">
                  {agentNameMap.get(selectedDoc.agent_id) ?? `Agent #${selectedDoc.agent_id}`}
                </span>
              </div>
              <div className="flex items-center gap-3 border-b border-border/60 px-4 py-3">
                <HardDrive className="size-4 shrink-0 text-muted-foreground" />
                <span className="text-[13px] text-muted-foreground">File Size</span>
                <span className="ml-auto text-[13px] font-medium text-foreground">
                  {formatFileSize(selectedDoc.file_size_bytes)}
                </span>
              </div>
              <div className="flex items-center gap-3 border-b border-border/60 px-4 py-3">
                <Calendar className="size-4 shrink-0 text-muted-foreground" />
                <span className="text-[13px] text-muted-foreground">Uploaded</span>
                <span className="ml-auto text-[13px] font-medium text-foreground">
                  {formatDate(selectedDoc.created_at)}
                </span>
              </div>
              <div className="flex items-center gap-3 px-4 py-3">
                <Calendar className="size-4 shrink-0 text-muted-foreground" />
                <span className="text-[13px] text-muted-foreground">Last Updated</span>
                <span className="ml-auto text-[13px] font-medium text-foreground">
                  {formatDate(selectedDoc.updated_at)}
                </span>
              </div>
            </div>
          </div>
        )}
      </CustomModal>

      {/* Delete confirmation */}
      <CustomModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Document"
        description={`Are you sure you want to delete "${deleteTarget?.file_name}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}
