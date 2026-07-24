'use client';

import { useAtom, useSetAtom } from 'jotai';
import { Key, MoreVertical, Plus, ShieldOff, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { authAtom, getCurrentUserAtom } from '@/atoms/AuthAtom';
import { CustomButton, CustomModal } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
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

// Mirror of the backend guard require_admin_or_owner. Non-admin/owner members
// can still LIST keys (require_org_member) but can't create/revoke/delete.
const CAN_MANAGE_ROLES = new Set(['admin', 'owner']);
const NO_PERMISSION_TOOLTIP = 'Only Admins or Owners can manage API keys.';

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

  // Populate authAtom from LOGIN_DATA if it hasn't been seeded yet — matches
  // the pattern in components/shared/userMenu.tsx.
  const [authState] = useAtom(authAtom);
  const getCurrentUser = useSetAtom(getCurrentUserAtom);
  useEffect(() => {
    if (!authState.user && !authState.isLoading) getCurrentUser();
  }, [authState.user, authState.isLoading, getCurrentUser]);
  const canManage = CAN_MANAGE_ROLES.has(authState.user?.role ?? '');

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
                <DropdownMenuItem
                  disabled={!canManage}
                  onClick={() => setConfirmRevoke(row)}
                  title={canManage ? undefined : NO_PERMISSION_TOOLTIP}
                >
                  <ShieldOff className="size-4" />
                  Revoke
                </DropdownMenuItem>
              )}
              <DropdownMenuItem
                variant="destructive"
                disabled={!canManage}
                onClick={() => setConfirmDelete(row)}
                title={canManage ? undefined : NO_PERMISSION_TOOLTIP}
              >
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
        {canManage ? (
          <CustomButton
            type="primary"
            icon={<Plus size={18} />}
            onClick={() => setCreateOpen(true)}
          >
            Add API Key
          </CustomButton>
        ) : (
          // Disabled buttons don't fire pointer events, so the tooltip needs
          // a wrapper span to catch hover — matches Radix's recommended pattern.
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-block">
                <CustomButton type="primary" icon={<Plus size={18} />} disabled>
                  Add API Key
                </CustomButton>
              </span>
            </TooltipTrigger>
            <TooltipContent>{NO_PERMISSION_TOOLTIP}</TooltipContent>
          </Tooltip>
        )}
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
