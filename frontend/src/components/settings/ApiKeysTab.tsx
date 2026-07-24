'use client';

import { Key, MoreVertical, Plus, ShieldOff, Trash2 } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';

import { CustomButton, CustomModal } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  useApiKeysList,
  useCreateApiKey,
  useDeleteApiKey,
  useRevokeApiKey,
} from '@/lib/api/apiKeys';
import type { CustomTableColumn } from '@/types/components';
import type { ApiKeyRow, ApiKeyStatus, CreateApiKeyPayload } from '@/types/settings/apiKey';
import { formatDate, formatRelative } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import CreateApiKeyModal from './CreateApiKeyModal';
import RevealApiKeyModal from './RevealApiKeyModal';

const STATUS_BADGE: Record<ApiKeyStatus, { label: string; className: string }> = {
  active: {
    label: 'Active',
    className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400',
  },
  expired: {
    label: 'Expired',
    className: 'bg-muted text-muted-foreground',
  },
  revoked: {
    label: 'Revoked',
    className: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
  },
};

export default function ApiKeysTab() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [revealState, setRevealState] = useState<{ key: string; name: string } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<ApiKeyRow | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<ApiKeyRow | null>(null);

  const listParams = { page_no: page, page_size: pageSize, search: search || undefined };
  const query = useApiKeysList(listParams);
  const createMutation = useCreateApiKey();
  const revokeMutation = useRevokeApiKey();
  const deleteMutation = useDeleteApiKey();

  const rows = query.data?.data ?? [];
  const total = query.data?.total ?? 0;

  const handleCreate = useCallback(
    async (payload: CreateApiKeyPayload) => {
      try {
        const result = await createMutation.mutateAsync(payload);
        setRevealState({ key: result.key, name: result.name });
        showToast.success('API key created');
      } catch (err) {
        handleApiError(err);
        throw err;
      }
    },
    [createMutation],
  );

  const handleRevoke = useCallback(
    async (row: ApiKeyRow) => {
      try {
        await revokeMutation.mutateAsync(row.id);
        showToast.success('API key revoked');
        setConfirmRevoke(null);
      } catch (err) {
        handleApiError(err);
      }
    },
    [revokeMutation],
  );

  const handleDelete = useCallback(
    async (row: ApiKeyRow) => {
      try {
        await deleteMutation.mutateAsync(row.id);
        showToast.success('API key deleted');
        setConfirmDelete(null);
      } catch (err) {
        handleApiError(err);
      }
    },
    [deleteMutation],
  );

  const columns = useMemo<CustomTableColumn<ApiKeyRow>[]>(
    () => [
      {
        key: 'name',
        title: 'Name',
        render: (_v, row) => (
          <div className="flex items-center gap-2">
            <Key className="size-4 text-muted-foreground" />
            <span className="text-sm text-foreground">{row.name}</span>
          </div>
        ),
      },
      {
        key: 'key',
        title: 'Key',
        render: (_v, row) => (
          <code className="font-mono text-[12px] text-muted-foreground">{row.masked}</code>
        ),
      },
      {
        key: 'status',
        title: 'Status',
        width: 'w-28',
        render: (_v, row) => {
          const badge = STATUS_BADGE[row.status];
          return (
            <Badge variant="secondary" className={badge.className}>
              {badge.label}
            </Badge>
          );
        },
      },
      {
        key: 'expires_at',
        title: 'Expires',
        width: 'w-40',
        render: (_v, row) => (
          <span className="text-[12px] text-muted-foreground">
            {row.expires_at ? formatDate(row.expires_at) : 'Never'}
          </span>
        ),
      },
      {
        key: 'last_used_at',
        title: 'Last used',
        width: 'w-32',
        render: (_v, row) => (
          <span className="text-[12px] text-muted-foreground">
            {row.last_used_at ? formatRelative(row.last_used_at) : 'Never'}
          </span>
        ),
      },
      {
        key: 'created_at',
        title: 'Created',
        width: 'w-32',
        render: (_v, row) => (
          <span className="text-[12px] text-muted-foreground">
            {row.created_at ? formatDate(row.created_at) : '—'}
          </span>
        ),
      },
      {
        key: 'actions',
        title: '',
        width: 'w-14',
        render: (_v, row) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <CustomButton
                type="text"
                size="icon-xs"
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <MoreVertical className="size-4" />
              </CustomButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {row.status === 'active' && (
                <DropdownMenuItem onClick={() => setConfirmRevoke(row)}>
                  <ShieldOff className="size-4" />
                  Revoke
                </DropdownMenuItem>
              )}
              <DropdownMenuItem variant="destructive" onClick={() => setConfirmDelete(row)}>
                <Trash2 className="size-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ),
      },
    ],
    [],
  );

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <CustomButton type="primary" icon={<Plus size={18} />} onClick={() => setCreateOpen(true)}>
          Add API Key
        </CustomButton>
      </div>

      <CustomTable
        columns={columns}
        dataSource={rows}
        rowKey="id"
        loading={query.isLoading}
        searchable
        searchPlaceholder="Search keys…"
        searchValue={search}
        onSearchChange={(v) => {
          setSearch(v);
          setPage(1);
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (nextPage, nextSize) => {
            setPage(nextPage);
            setPageSize(nextSize);
          },
        }}
      />

      <CreateApiKeyModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
      />

      <RevealApiKeyModal
        open={revealState !== null}
        onClose={() => setRevealState(null)}
        apiKey={revealState?.key ?? null}
        name={revealState?.name ?? null}
      />

      <CustomModal
        open={confirmRevoke !== null}
        onClose={() => (revokeMutation.isPending ? undefined : setConfirmRevoke(null))}
        title="Revoke API key?"
        description={
          confirmRevoke
            ? `"${confirmRevoke.name}" will stop working immediately for any client using it. This cannot be undone.`
            : ''
        }
        confirmText="Revoke"
        confirmType="danger"
        onConfirm={() => confirmRevoke && handleRevoke(confirmRevoke)}
        confirmLoading={revokeMutation.isPending}
      />

      <CustomModal
        open={confirmDelete !== null}
        onClose={() => (deleteMutation.isPending ? undefined : setConfirmDelete(null))}
        title="Delete API key?"
        description={
          confirmDelete
            ? `"${confirmDelete.name}" will be permanently removed. Any client using it will stop working immediately.`
            : ''
        }
        confirmText="Delete"
        confirmType="danger"
        onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
        confirmLoading={deleteMutation.isPending}
      />
    </div>
  );
}
