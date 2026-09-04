'use client';

import { useMemo, useState } from 'react';
import { MoreVertical, Pencil, Plus, Trash2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import IngestionConfigDrawer from '@/components/knowledge-base/IngestionConfigDrawer';
import { CustomButton, CustomPopover, CustomTable } from '@/components/shared';
import { useDeleteIngestionConfig, useIngestionConfigs } from '@/lib/api/ingestion-configs';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import type { IngestionConfig } from '@/types/ingestionConfig';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const DEFAULT_PAGE_SIZE = 20;

export default function IngestionConfigsTab() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<CustomTableSortState>({
    field: 'updated_at',
    order: 'desc',
  });

  const { data, isLoading } = useIngestionConfigs({
    page_no: page,
    page_size: pageSize,
    search: search || undefined,
    sort_by: sort.field,
    sort_order: sort.order,
  });

  const deleteMutation = useDeleteIngestionConfig();

  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<IngestionConfig | null>(null);
  const [deleting, setDeleting] = useState<IngestionConfig | null>(null);

  const rows = data?.data ?? [];
  const total = data?.total ?? 0;

  const handleDeleteConfirm = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      showToast.success('Config deleted', `Removed "${deleting.name}".`);
      setDeleting(null);
    } catch (error) {
      handleApiError(error);
    }
  };

  const columns = useMemo<CustomTableColumn<IngestionConfig>[]>(
    () => [
      {
        key: 'name',
        title: 'Name',
        dataIndex: 'name',
        sorter: true,
        render: (_value, record) => (
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-foreground">{record.name}</div>
            {record.description && (
              <div className="truncate text-[11px] text-muted-foreground">{record.description}</div>
            )}
          </div>
        ),
      },
      {
        key: 'parser',
        title: 'Parser',
        dataIndex: 'parser',
        render: (value) => <span className="text-sm text-foreground">{value as string}</span>,
      },
      {
        key: 'tokeniser',
        title: 'Chunker',
        dataIndex: 'tokeniser',
        render: (value) => <span className="text-sm text-foreground">{value as string}</span>,
      },
      {
        key: 'embedding',
        title: 'Embedding',
        render: (_v, r) => (
          <div className="flex flex-col">
            <span className="text-sm text-foreground">{r.embedding_model}</span>
            <span className="text-[11px] text-muted-foreground">
              {r.embedding_provider} · {r.embedding_dimensions} dims
            </span>
          </div>
        ),
      },
      {
        key: 'vector_store',
        title: 'Vector store',
        dataIndex: 'vector_store',
        render: (value) => <span className="text-sm text-foreground">{value as string}</span>,
      },
      {
        key: 'updated_at',
        title: 'Updated',
        dataIndex: 'updated_at',
        sorter: true,
        render: (value) => (
          <span className="text-[11px] text-muted-foreground">
            {value ? formatDate(value as string) : '—'}
          </span>
        ),
      },
      {
        key: 'actions',
        title: '',
        width: 'w-[52px]',
        align: 'center',
        render: (_v, record) => (
          <CustomPopover
            trigger={
              <CustomButton
                type="text"
                size="icon-xs"
                aria-label={`Actions for ${record.name}`}
                className="size-7"
                icon={<MoreVertical className="size-4" />}
              />
            }
            align="end"
            sideOffset={4}
            width="w-36"
            contentClassName="max-h-none overflow-visible p-1"
          >
            <CustomButton
              type="text"
              fullWidth
              onClick={() => setEditing(record)}
              className="h-auto justify-start gap-2 rounded-sm px-2 py-1.5 text-left text-sm font-normal text-foreground hover:bg-muted"
              icon={<Pencil className="size-3.5" />}
            >
              Edit
            </CustomButton>
            <CustomButton
              type="text"
              fullWidth
              onClick={() => setDeleting(record)}
              className="h-auto justify-start gap-2 rounded-sm px-2 py-1.5 text-left text-sm font-normal text-destructive hover:bg-destructive/10 hover:text-destructive"
              icon={<Trash2 className="size-3.5" />}
            >
              Delete
            </CustomButton>
          </CustomPopover>
        ),
      },
    ],
    [],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 py-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Ingestion configs</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Save reusable pipeline recipes (parser, chunker, embedder, vector store) and pick one
            when starting a new ingestion run.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {total > 0 && (
            <Badge variant="secondary" className="text-xs tabular-nums">
              {total}
            </Badge>
          )}
          <CustomButton
            type="primary"
            size="sm"
            onClick={() => setCreateOpen(true)}
            aria-label="Create ingestion config"
          >
            <Plus className="mr-1 size-4" />
            New config
          </CustomButton>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={rows}
          rowKey="id"
          loading={isLoading}
          searchable
          searchPlaceholder="Search name, parser, model, store…"
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
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <p className="text-sm text-muted-foreground">
                No ingestion configs yet. Save a recipe once and reuse it across runs.
              </p>
              <CustomButton type="primary" size="sm" onClick={() => setCreateOpen(true)}>
                <Plus className="mr-1 size-4" />
                New config
              </CustomButton>
            </div>
          }
        />
      </div>

      <IngestionConfigDrawer open={createOpen} onClose={() => setCreateOpen(false)} />
      <IngestionConfigDrawer
        open={editing !== null}
        onClose={() => setEditing(null)}
        config={editing}
      />
      <ConfirmDeleteModal
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete ingestion config"
        description={
          deleting
            ? `Delete "${deleting.name}"? Historical runs that used this config will keep their snapshotted values.`
            : undefined
        }
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
