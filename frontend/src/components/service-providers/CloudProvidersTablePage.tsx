'use client';

import { useMemo } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';

import CloudProviderEditDrawer from '@/components/service-providers/CloudProviderEditDrawer';
import { useCloudProviderActions } from '@/components/service-providers/useCloudProviderActions';
import { CustomButton, CustomModal, CustomTable, CustomTooltip } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { CustomTableColumn } from '@/types/components';
import type { CloudProvider } from '@/types/service';
import { cn } from '@/utils/cn';

const PAGE_SIZE_OPTIONS = [10, 20, 50];

export default function CloudProvidersTablePage() {
  const actions = useCloudProviderActions();

  const columns = useMemo<CustomTableColumn<CloudProvider>[]>(
    () => [
      {
        key: 'display_name',
        title: 'Name',
        dataIndex: 'display_name',
        sorter: true,
        render: (value) => (
          <span className="text-sm font-medium text-foreground">{String(value ?? '—')}</span>
        ),
      },
      {
        key: 'provider_id',
        title: 'Provider ID',
        dataIndex: 'provider_id',
        sorter: true,
        render: (value) => (
          <span className="font-mono text-xs text-muted-foreground">{String(value ?? '—')}</span>
        ),
      },
      {
        key: 'slug',
        title: 'Slug',
        dataIndex: 'slug',
        render: (value) => (
          <span className="font-mono text-xs text-muted-foreground">{String(value ?? '—')}</span>
        ),
      },
      {
        key: 'is_active',
        title: 'Status',
        align: 'center',
        width: 'w-[110px]',
        render: (_v, r) => (
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1',
              r.is_active
                ? 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-400'
                : 'bg-muted text-muted-foreground ring-border/60',
            )}
          >
            {r.is_active ? 'Active' : 'Inactive'}
          </span>
        ),
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        width: 'w-[110px]',
        render: (_v, r) => (
          <div className="flex items-center justify-end gap-1">
            <CustomTooltip content="Edit">
              <CustomButton
                type="text"
                size="icon-xs"
                aria-label="Edit cloud provider"
                onClick={() => actions.openEdit(r)}
              >
                <Pencil className="size-3.5" />
              </CustomButton>
            </CustomTooltip>
            <CustomTooltip content="Delete">
              <CustomButton
                type="text"
                size="icon-xs"
                aria-label="Delete cloud provider"
                onClick={() => actions.requestDelete(r)}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="size-3.5" />
              </CustomButton>
            </CustomTooltip>
          </div>
        ),
      },
    ],
    [actions],
  );

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-[1.75rem] font-semibold tracking-[-0.03em] text-foreground">
              Cloud providers
            </h1>
            {actions.total > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {actions.total}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            The clouds a model can be hosted on (e.g. AWS, Azure). A global catalog shared across
            organizations.
          </p>
        </div>
        <CustomButton type="primary" size="sm" onClick={actions.openCreate}>
          <Plus className="mr-1 size-4" />
          Add cloud provider
        </CustomButton>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={actions.rows}
          rowKey="id"
          loading={actions.loading}
          searchable
          searchPlaceholder="Search name, provider id, slug…"
          searchValue={actions.search}
          onSearchChange={(v) => {
            actions.setSearch(v);
            actions.setPage(1);
          }}
          onSortChange={(next) => {
            if (next) actions.setSort(next);
          }}
          initialSort={actions.sort}
          pagination={{
            current: actions.page,
            pageSize: actions.pageSize,
            total: actions.total,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            onChange: (p, size) => {
              actions.setPage(p);
              actions.setPageSize(size);
            },
          }}
          emptyState={
            <div className="py-10 text-center text-sm text-muted-foreground">
              No cloud providers yet.
            </div>
          }
        />
      </div>

      <CloudProviderEditDrawer
        open={actions.editOpen}
        editing={actions.editing}
        onClose={actions.closeEdit}
        onSubmit={actions.submit}
        isPending={actions.saving}
      />

      <CustomModal
        open={!!actions.deleteTarget}
        onClose={actions.closeDelete}
        title="Delete cloud provider?"
        description={
          actions.deleteTarget
            ? `This permanently deletes "${actions.deleteTarget.display_name}". Models still assigned to it must be reassigned first.`
            : ''
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={actions.deleting}
        onConfirm={actions.confirmDelete}
      />
    </div>
  );
}
