'use client';

import { useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Wrench, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useMemo, useState } from 'react';

import { PageHeader } from '@/components/layout/page-header';
import { ActionMenu, CustomButton, CustomModal, CustomTable } from '@/components/shared';
import SearchBar from '@/components/shared/SearchBar';
import SelectInput from '@/components/shared/SelectInput';
import { Checkbox } from '@/components/ui/checkbox';
import { TOOL_TYPE_HEADER } from '@/constants/toolForm';
import { TOOLS_QUERY_KEY, toolsApi, useDeleteTool, useTools } from '@/lib/api/tools';
import { TOOL_STATUS_OPTIONS, TOOL_TYPE_OPTIONS } from '@/lib/constants/filters';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import type { Tool } from '@/types/tool';
import { cn } from '@/utils/cn';
import { showToast } from '@/utils/toast';

const PAGE_SIZE_OPTIONS = [10, 20, 50];

export default function ToolsListPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState('-updated_at');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const queryParams = useMemo(
    () => ({
      page,
      page_size: pageSize,
      sort_by: sortBy,
      search: search || undefined,
      tool_type: typeFilter !== 'all' ? typeFilter : undefined,
      is_active: statusFilter === 'active' ? true : statusFilter === 'inactive' ? false : undefined,
    }),
    [page, pageSize, sortBy, search, typeFilter, statusFilter],
  );

  const { data, isLoading, isFetching } = useTools(queryParams);
  const tools = data?.items ?? [];
  const total = data?.total ?? 0;

  const deleteMutation = useDeleteTool();

  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    setPage(1);
  }, []);

  const handleTypeFilter = useCallback((value: string) => {
    setTypeFilter(value);
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

  const handleEdit = useCallback(
    (tool: Tool) => {
      router.push(`/tools/edit/${tool.id}`);
    },
    [router],
  );

  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setBulkDeleting(true);
    const ids = Array.from(selectedIds);
    const results = await Promise.allSettled(ids.map((id) => toolsApi.delete(id)));
    const failed = results.filter((r) => r.status === 'rejected').length;
    queryClient.invalidateQueries({ queryKey: [TOOLS_QUERY_KEY] });
    setBulkDeleting(false);
    setBulkDeleteOpen(false);

    if (failed === 0) {
      showToast.success(ids.length === 1 ? 'Tool deleted' : `${ids.length} tools deleted`);
      setSelectedIds(new Set());
    } else if (failed === ids.length) {
      showToast.error('Bulk delete failed', 'No tools were deleted.');
    } else {
      const deleted = ids.length - failed;
      showToast.error(
        'Partial delete',
        `${deleted} of ${ids.length} deleted. ${failed} failed — refresh and try again.`,
      );
      const failedIds = new Set<string>();
      results.forEach((r, i) => {
        if (r.status === 'rejected') failedIds.add(ids[i]);
      });
      setSelectedIds(failedIds);
    }
  }, [selectedIds, queryClient]);

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
      if (tools.length > 0 && tools.every((t) => prev.has(t.id))) {
        return new Set();
      }
      return new Set(tools.map((t) => t.id));
    });
  }, [tools]);

  const allRowsSelected = tools.length > 0 && tools.every((t) => selectedIds.has(t.id));
  const someRowsSelected = !allRowsSelected && tools.some((t) => selectedIds.has(t.id));

  const columns = useMemo<CustomTableColumn<Tool>[]>(
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
            aria-label={`Select ${record.name}`}
          />
        ),
      },
      {
        key: 'name',
        dataIndex: 'name',
        title: 'Name',
        sorter: true,
        width: '220px',
        render: (_val: unknown, record: Tool) => (
          <div className="min-w-0">
            <p className="truncate font-mono text-[13px] font-medium text-foreground">
              {record.name}
            </p>
            <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
              {record.description}
            </p>
          </div>
        ),
      },
      {
        key: 'tool_type',
        dataIndex: 'tool_type',
        title: 'Type',
        width: '110px',
        render: (_val: unknown, record: Tool) => {
          const headerConfig = TOOL_TYPE_HEADER[record.tool_type];
          const label =
            headerConfig?.label ?? (record.tool_type === 'custom' ? 'Custom' : record.tool_type);
          return (
            <span className="inline-flex rounded-full border border-border bg-background px-2.5 py-0.5 text-[11px] font-medium text-foreground">
              {label}
            </span>
          );
        },
      },
      {
        key: 'method',
        dataIndex: 'method',
        title: 'Method',
        width: '90px',
        render: (_val: unknown, record: Tool) => {
          const m = record.method?.toUpperCase() ?? 'POST';
          return (
            <span className="inline-flex rounded-md border border-border bg-background px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-foreground">
              {m}
            </span>
          );
        },
      },
      {
        key: 'url',
        dataIndex: 'url',
        title: 'Endpoint URL',
        render: (_val: unknown, record: Tool) => (
          <span className="truncate font-mono text-[12px] text-muted-foreground">{record.url}</span>
        ),
      },
      {
        key: 'auth_type',
        dataIndex: 'auth_type',
        title: 'Auth',
        width: '100px',
        render: (_val: unknown, record: Tool) => (
          <span className="text-[12px] capitalize text-muted-foreground">
            {!record.auth_type || record.auth_type === 'none'
              ? '-'
              : record.auth_type.replace('_', ' ')}
          </span>
        ),
      },
      {
        key: 'params',
        title: 'Params',
        width: '80px',
        render: (_val: unknown, record: Tool) => {
          const count = Object.keys(record.parameters?.properties ?? {}).length;
          return (
            <span className="text-[12px] text-muted-foreground">
              {count > 0 ? `${count} param${count > 1 ? 's' : ''}` : '-'}
            </span>
          );
        },
      },
      {
        key: 'is_active',
        dataIndex: 'is_active',
        title: 'Status',
        sorter: true,
        width: '80px',
        render: (_val: unknown, record: Tool) => (
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
              record.is_active
                ? 'bg-amber-400/15 text-amber-600 dark:text-amber-500'
                : 'bg-muted text-muted-foreground',
            )}
          >
            {record.is_active && (
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400/70" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
              </span>
            )}
            {record.is_active ? 'Active' : 'Inactive'}
          </span>
        ),
      },
      {
        key: 'actions',
        title: '',
        width: '80px',
        align: 'right' as const,
        render: (_val: unknown, record: Tool) => (
          <ActionMenu
            onEdit={() => handleEdit(record)}
            onDelete={async () => {
              await deleteMutation.mutateAsync(record.id);
              showToast.success('Tool deleted successfully');
              setSelectedIds((prev) => {
                const next = new Set(prev);
                next.delete(record.id);
                return next;
              });
            }}
            itemName={record.name}
          />
        ),
      },
    ],
    [allRowsSelected, someRowsSelected, toggleAllRows, selectedIds, toggleRow, handleEdit],
  );

  const hasFilter = !!search || typeFilter !== 'all' || statusFilter !== 'all';

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-6">
      <PageHeader
        kicker={total > 0 ? `Tools · ${total}` : 'Tools'}
        title="Tools."
        description="Define external API tools your voice agents can call during conversations."
        actions={
          <CustomButton
            type="primary"
            icon={<Plus className="size-4" />}
            onClick={() => router.push('/tools/create')}
          >
            Create New Tool
          </CustomButton>
        }
      />

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <SearchBar
          placeholder="Search tools..."
          value={search}
          onSearch={handleSearch}
          debounceMs={400}
          containerClassName="max-w-xs flex-1"
        />
        <SelectInput
          name="type-filter"
          options={TOOL_TYPE_OPTIONS}
          value={typeFilter}
          onValueChange={handleTypeFilter}
          placeholder="All types"
          size="sm"
          triggerClassName="min-w-[160px]"
        />
        <SelectInput
          name="status-filter"
          options={TOOL_STATUS_OPTIONS}
          value={statusFilter}
          onValueChange={handleStatusFilter}
          placeholder="All statuses"
          size="sm"
          triggerClassName="min-w-[160px]"
        />
      </div>

      {/* Table */}
      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable<Tool>
          columns={columns}
          dataSource={tools}
          rowKey="id"
          loading={isLoading || isFetching}
          onRowClick={handleEdit}
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
            <EmptyState onAdd={() => router.push('/tools/create')} hasFilter={hasFilter} />
          }
        />
      </div>

      {/* Selection bar */}
      <SelectionBar
        count={selectedIds.size}
        onClear={() => setSelectedIds(new Set())}
        onDelete={() => setBulkDeleteOpen(true)}
      />

      {/* Bulk delete modal */}
      <CustomModal
        open={bulkDeleteOpen}
        onClose={() => setBulkDeleteOpen(false)}
        title="Delete tools"
        description={
          selectedIds.size === 1
            ? 'Delete 1 selected tool? This action cannot be undone.'
            : `Delete ${selectedIds.size} selected tools? This action cannot be undone.`
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={bulkDeleting}
        onConfirm={handleBulkDelete}
      />
    </div>
  );
}

function EmptyState({ onAdd, hasFilter }: { onAdd: () => void; hasFilter: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-background">
        <Wrench className="size-6 text-foreground" strokeWidth={1.75} />
      </div>
      <div className="max-w-sm text-center">
        <p className="font-semibold text-foreground">
          {hasFilter ? 'No tools match your filters' : 'No tools yet'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try clearing the search or filters.'
            : 'Create your first tool to give your agents the ability to call external APIs.'}
        </p>
      </div>
      {!hasFilter && (
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={onAdd}>
          Create New Tool
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
          {count === 1 ? 'tool selected' : 'tools selected'}
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
