'use client';

import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import type { CustomTableColumn } from '@/types/components';
import type { OrganizationMemberApi } from '@/types/settings/members';
import { Trash2 } from 'lucide-react';
import { useCallback, useState } from 'react';

interface MembersTableProps {
  rows: OrganizationMemberApi[];
  loading?: boolean;
  onRoleChange: (memberId: number, role: string) => Promise<void>;
  onDelete: (userId: number) => Promise<void>;
}

const ROLE_OPTIONS = [
  { value: 'owner', label: 'Owner' },
  { value: 'admin', label: 'Admin' },
  { value: 'member', label: 'Member' },
  { value: 'viewer', label: 'Viewer' },
];

export default function MembersTable({ rows, loading, onRoleChange, onDelete }: MembersTableProps) {
  const [deleteTarget, setDeleteTarget] = useState<OrganizationMemberApi | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [updatingRoleId, setUpdatingRoleId] = useState<number | null>(null);

  const getNameFromEmail = (email: string) => {
    if (!email) return '';

    const namePart = email.split('@')[0];

    return namePart
      .replace(/[^a-zA-Z0-9]/g, ' ')
      .split(' ')
      .filter(Boolean)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join('');
  };

  const handleRoleChange = useCallback(
    async (memberId: number, role: string) => {
      setUpdatingRoleId(memberId);
      try {
        await onRoleChange(memberId, role);
      } finally {
        setUpdatingRoleId(null);
      }
    },
    [onRoleChange],
  );

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await onDelete(deleteTarget.user_id);
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const columns: CustomTableColumn<OrganizationMemberApi>[] = [
    {
      key: 'sno',
      title: 'S.No',
      width: 'w-16',
      render: (_value, _record, index) => (
        <span className="text-muted-foreground">{index + 1}</span>
      ),
    },
    {
      key: 'name',
      title: 'Name',
      render: (_value, record) => (
        <div>
          <p className="text-sm font-medium text-foreground">
            {record.first_name || record.last_name
              ? `${record.first_name ?? ''} ${record.last_name ?? ''}`.trim()
              : record.username || getNameFromEmail(record.email)}
          </p>
          <p className="text-xs text-muted-foreground">{record.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      title: 'Role',
      width: 'w-40',
      render: (_value, record) => {
        const isOwner = record.role === 'owner';
        const isUpdating = updatingRoleId === record.member_id;
        return (
          <SelectInput
            name={`role-${record.member_id}`}
            options={ROLE_OPTIONS}
            value={record.role}
            onValueChange={(val) => handleRoleChange(record.member_id, val)}
            disabled={isOwner || isUpdating}
            loading={isUpdating}
            size="sm"
          />
        );
      },
    },
    {
      key: 'status',
      title: 'Status',
      width: 'w-28',
      render: (_value, record) => {
        const status = record.status ?? 'active';
        const variant = status === 'active' ? 'default' : 'secondary';
        return (
          <Badge
            variant={variant}
            className={
              status === 'active' ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : ''
            }
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </Badge>
        );
      },
    },
    {
      key: 'actions',
      title: '',
      width: 'w-16',
      render: (_value, record) => {
        const isOwner = record.role === 'owner';
        return (
          <CustomButton
            type="text"
            size="icon-xs"
            disabled={isOwner}
            onClick={(e) => {
              e.stopPropagation();
              setDeleteTarget(record);
            }}
            aria-label="Remove member"
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="size-4" />
          </CustomButton>
        );
      },
    },
  ];

  return (
    <>
      <CustomTable columns={columns} dataSource={rows} rowKey="member_id" loading={loading} />
      <CustomModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Remove Member"
        description={`Are you sure you want to remove ${deleteTarget?.username || deleteTarget?.email}? They will lose access to the organization.`}
        confirmText="Remove"
        confirmType="danger"
        onConfirm={handleConfirmDelete}
        confirmLoading={deleting}
      />
    </>
  );
}
