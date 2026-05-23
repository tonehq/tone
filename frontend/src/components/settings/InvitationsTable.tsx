'use client';

import { RotateCcw, X } from 'lucide-react';
import { useState } from 'react';

import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import type { ListRequest } from '@/types/list';
import type { OrganizationInviteApi } from '@/types/settings/members';

interface InvitationsTableProps {
  rows: OrganizationInviteApi[];
  total: number;
  params: ListRequest;
  onParamsChange: (patch: Partial<ListRequest>) => void;
  loading?: boolean;
  onCancel: (inviteId: string) => Promise<void>;
  onResend?: (inviteId: string) => Promise<void>;
  onRefresh?: () => Promise<void> | void;
  refreshing?: boolean;
}

const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'expired', label: 'Expired' },
];

export default function InvitationsTable({
  rows,
  total,
  params,
  onParamsChange,
  loading,
  onCancel,
  onResend,
  onRefresh,
  refreshing,
}: InvitationsTableProps) {
  const [cancelTarget, setCancelTarget] = useState<OrganizationInviteApi | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [resendingId, setResendingId] = useState<string | null>(null);

  const handleResend = async (id: string) => {
    if (!onResend) return;
    setResendingId(id);
    try {
      await onResend(id);
    } finally {
      setResendingId(null);
    }
  };

  const statusFilter = (params.filters?.status as string | undefined) ?? 'all';

  const handleConfirmCancel = async () => {
    if (!cancelTarget) return;
    setCancelling(true);
    try {
      await onCancel(cancelTarget.member_id);
    } finally {
      setCancelling(false);
      setCancelTarget(null);
    }
  };

  const handleStatusFilterChange = (val: string) => {
    const filters = { ...(params.filters ?? {}) };
    if (val === 'all') delete filters.status;
    else filters.status = val;
    onParamsChange({ filters });
  };

  const handleSortChange = (sort: CustomTableSortState | null) => {
    onParamsChange({
      sort_by: sort?.field,
      sort_order: sort?.order ?? 'desc',
    });
  };

  const columns: CustomTableColumn<OrganizationInviteApi>[] = [
    {
      key: 'name',
      title: 'Name',
      dataIndex: 'name',
      sorter: true,
      render: (_value, record) => (
        <span className="font-medium text-foreground">{record.name || '—'}</span>
      ),
    },
    {
      key: 'email',
      title: 'Email',
      dataIndex: 'email',
      sorter: true,
    },
    {
      key: 'role',
      title: 'Role',
      dataIndex: 'role',
      width: 'w-28',
      sorter: true,
      render: (_value, record) => (
        <Badge variant="secondary" className="capitalize">
          {record.role}
        </Badge>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      dataIndex: 'status',
      width: 'w-32',
      sorter: true,
      render: (_value, record) => {
        const status = (record.status ?? '').toLowerCase();
        const style =
          status === 'pending'
            ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
            : status === 'accepted'
              ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
              : status === 'expired'
                ? 'bg-red-500/15 text-red-600 dark:text-red-400'
                : '';
        return (
          <Badge variant="secondary" className={`capitalize ${style}`}>
            {record.status}
          </Badge>
        );
      },
    },
    {
      key: 'actions',
      title: '',
      width: 'w-24',
      align: 'right',
      render: (_value, record) => {
        const isPending = (record.status ?? '').toLowerCase() === 'pending';
        const isResending = resendingId === record.member_id;
        return (
          <div className="flex items-center justify-end gap-1">
            {isPending && onResend && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    loading={isResending}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleResend(record.member_id);
                    }}
                    aria-label="Resend invitation"
                    className="text-muted-foreground hover:bg-primary/10 hover:text-primary"
                  >
                    <RotateCcw className="size-4" />
                  </CustomButton>
                </TooltipTrigger>
                <TooltipContent side="top" sideOffset={4}>
                  Resend invitation email
                </TooltipContent>
              </Tooltip>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <CustomButton
                  type="text"
                  size="icon-xs"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCancelTarget(record);
                  }}
                  aria-label="Cancel invitation"
                  className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                >
                  <X className="size-4" />
                </CustomButton>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={4}>
                Cancel invitation
              </TooltipContent>
            </Tooltip>
          </div>
        );
      },
    },
  ];

  return (
    <>
      <CustomTable
        columns={columns}
        dataSource={rows}
        rowKey="member_id"
        loading={loading}
        searchable
        searchPlaceholder="Search invitations by name or email…"
        searchValue={params.search ?? ''}
        onSearchChange={(value) => onParamsChange({ search: value || undefined })}
        onSortChange={handleSortChange}
        onRefresh={onRefresh}
        refreshing={refreshing}
        pagination={{
          current: params.page ?? 1,
          pageSize: params.page_size ?? 10,
          total,
          onChange: (page, pageSize) => onParamsChange({ page, page_size: pageSize }),
        }}
        toolbar={
          <div className="w-40">
            <SelectInput
              name="invite-status-filter"
              options={STATUS_FILTER_OPTIONS}
              value={statusFilter}
              onValueChange={handleStatusFilterChange}
              size="sm"
            />
          </div>
        }
      />
      <CustomModal
        open={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        title="Cancel Invitation"
        description={`Are you sure you want to cancel the invitation for ${cancelTarget?.email}?`}
        confirmText="Cancel Invitation"
        confirmType="danger"
        onConfirm={handleConfirmCancel}
        confirmLoading={cancelling}
      />
    </>
  );
}
