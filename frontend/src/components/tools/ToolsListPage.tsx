'use client';

import { Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useMemo, useState } from 'react';

import {
  ActionMenu,
  CustomButton,
  CustomModal,
  CustomTable,
  FacetFilterBar,
  FacetFilterDrawer,
  OAuthConnectionStatus,
  SelectionBar,
  useFacetedList,
} from '@/components/shared';
import ToolsListEmptyState from '@/components/tools/ToolsListEmptyState';
import { Checkbox } from '@/components/ui/checkbox';
import { METHOD_COLORS, TOOL_TYPE_HEADER } from '@/constants/toolForm';
import { toolsApi, useDeleteTool } from '@/lib/api/tools';
import { toolsListConfig } from '@/components/tools/toolsListConfig';
import type { CustomTableColumn } from '@/types/components';
import type { Tool } from '@/types/tool';
import { cn } from '@/utils/cn';
import { showToast } from '@/utils/toast';

export default function ToolsListPage() {
  const router = useRouter();

  const fl = useFacetedList(toolsListConfig);
  const tools = fl.rows;
  const total = fl.total;

  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const deleteMutation = useDeleteTool();

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
    fl.refresh();
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
  }, [selectedIds, fl]);

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
          const badgeClass =
            record.tool_type === 'custom'
              ? 'bg-sky-500/10 text-sky-700 dark:text-sky-400'
              : headerConfig
                ? `${headerConfig.bg} ${headerConfig.color}`
                : 'bg-amber-500/10 text-amber-700 dark:text-amber-400';
          return (
            <span
              className={cn(
                'inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-medium',
                badgeClass,
              )}
            >
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
            <span
              className={cn(
                'inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold',
                METHOD_COLORS[m] ?? 'bg-muted text-muted-foreground',
              )}
            >
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
        key: 'oauth_status',
        title: 'OAuth',
        width: '220px',
        render: (_val: unknown, record: Tool) => {
          // Only OAuth-linked tools with a hydrated summary get the widget —
          // API-key / bearer / none rows render the placeholder dash, keeping
          // the column visually consistent without adding meaningless badges.
          if (!record.oauth_connection) {
            return <span className="text-[12px] text-muted-foreground">-</span>;
          }
          return (
            <OAuthConnectionStatus
              connectionId={record.oauth_connection.id}
              providerSlug={record.oauth_connection.provider_slug}
              tokenExpiry={record.oauth_connection.token_expiry}
              compact
            />
          );
        },
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
              'inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium',
              record.is_active
                ? 'bg-emerald-500/15 text-emerald-600'
                : 'bg-muted text-muted-foreground',
            )}
          >
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
              fl.refresh();
            }}
            itemName={record.name}
          />
        ),
      },
    ],
    [
      allRowsSelected,
      someRowsSelected,
      toggleAllRows,
      selectedIds,
      toggleRow,
      handleEdit,
      deleteMutation,
      fl,
    ],
  );

  const hasFilter = fl.hasActiveFilters;

  return (
    <div className="animate-page mx-auto flex h-full min-h-0 w-full max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.34em] text-muted-foreground">
            Build
          </p>
          <div className="flex items-baseline gap-3">
            <h1 className="font-display text-[clamp(2rem,3.4vw,2.75rem)] font-semibold leading-none tracking-[-0.04em] text-foreground">
              Tools
            </h1>
            {total > 0 && (
              <span className="font-mono text-[13px] tabular-nums text-muted-foreground">
                {total}
              </span>
            )}
          </div>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Define external API tools your voice agents can call during conversations.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus size={15} />}
          className="h-10"
          onClick={() => router.push('/tools/create')}
        >
          Create tool
        </CustomButton>
      </div>

      {/* Toolbar */}
      <FacetFilterBar
        fields={fl.tokenFields}
        tokens={fl.tokens}
        onTokensChange={fl.setTokens}
        onClear={fl.clearAll}
        showClear={fl.hasActiveFilters}
        placeholder="Search tools… (e.g. name:weather, status:active)"
        drawerFilterCount={fl.drawerFilterCount}
        onOpenDrawer={() => setFilterDrawerOpen(true)}
      />

      {/* Table */}
      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable<Tool>
          columns={columns}
          dataSource={tools}
          rowKey="id"
          loading={fl.listLoading}
          loadingLabel="Loading tools"
          onRowClick={handleEdit}
          onSortChange={fl.handleSortChange}
          initialSort={toolsListConfig.defaultSort ?? undefined}
          pagination={{
            current: fl.page,
            pageSize: fl.pageSize,
            total,
            pageSizeOptions: fl.pageSizeOptions,
            onChange: fl.handlePaginationChange,
          }}
          emptyState={
            <ToolsListEmptyState onAdd={() => router.push('/tools/create')} hasFilter={hasFilter} />
          }
        />
      </div>

      {/* Filter drawer */}
      <FacetFilterDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        description="Filter tools by type and status."
        sections={toolsListConfig.facetSections}
        value={fl.facetSelections}
        facets={fl.facets}
        facetsLoading={fl.facetsLoading}
        onApply={fl.applyDrawer}
      />

      {/* Selection bar */}
      <SelectionBar
        count={selectedIds.size}
        onClear={() => setSelectedIds(new Set())}
        onDelete={() => setBulkDeleteOpen(true)}
        singular="tool"
        plural="tools"
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
