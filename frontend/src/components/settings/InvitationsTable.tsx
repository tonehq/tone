'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import type { CustomTableColumn } from '@/types/components';
import type { OrganizationInviteApi } from '@/types/settings/members';
import { Loader2, X } from 'lucide-react';
import { useState } from 'react';

interface InvitationsTableProps {
  rows: OrganizationInviteApi[];
  loading?: boolean;
  onCancel: (inviteId: number) => Promise<void>;
}

export default function InvitationsTable({ rows, loading, onCancel }: InvitationsTableProps) {
  const [cancelTarget, setCancelTarget] = useState<OrganizationInviteApi | null>(null);
  const [cancelling, setCancelling] = useState(false);

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

  const columns: CustomTableColumn<OrganizationInviteApi>[] = [
    {
      key: 'name',
      title: 'Name',
      dataIndex: 'name',
    },
    {
      key: 'email',
      title: 'Email',
      dataIndex: 'email',
    },
    {
      key: 'role',
      title: 'Role',
      width: 'w-28',
      render: (_value, record) => (
        <Badge variant="secondary" className="capitalize">
          {record.role}
        </Badge>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      width: 'w-28',
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
      width: 'w-16',
      render: (_value, record) => (
        <CustomButton
          type="text"
          size="icon-xs"
          onClick={(e) => {
            e.stopPropagation();
            setCancelTarget(record);
          }}
          aria-label="Cancel invitation"
          className="text-muted-foreground hover:text-destructive"
        >
          <X className="size-4" />
        </CustomButton>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="size-9 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <>
      <CustomTable columns={columns} dataSource={rows} rowKey="member_id" />
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
