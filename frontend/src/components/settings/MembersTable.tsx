'use client';

import { Trash2 } from 'lucide-react';
import { useCallback, useState } from 'react';

import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import type { ListRequest } from '@/types/list';
import type { OrganizationMemberApi } from '@/types/settings/members';

interface MembersTableProps {
  rows: OrganizationMemberApi[];
  total: number;
  params: ListRequest;
  onParamsChange: (patch: Partial<ListRequest>) => void;
  loading?: boolean;
  onRoleChange: (memberId: string, role: string) => Promise<void>;
  onDelete: (userId: string) => Promise<void>;
  onRefresh?: () => Promise<void> | void;
  refreshing?: boolean;
}

const ROLE_OPTIONS = [
  { value: 'owner', label: 'Owner' },
  { value: 'admin', label: 'Admin' },
  { value: 'member', label: 'Member' },
  { value: 'viewer', label: 'Viewer' },
];

const ROLE_FILTER_OPTIONS = [{ value: 'all', label: 'All roles' }, ...ROLE_OPTIONS];

function getDisplayName(record: OrganizationMemberApi): string {
  if (record.first_name || record.last_name) {
    return `${record.first_name ?? ''} ${record.last_name ?? ''}`.trim();
  }
  if (record.username) return record.username;
  const namePart = (record.email || '').split('@')[0] ?? '';
  return namePart
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default function MembersTable({
  rows,
  total,
  params,
  onParamsChange,
  loading,
  onRoleChange,
  onDelete,
  onRefresh,
  refreshing,
}: MembersTableProps) {
  const [deleteTarget, setDeleteTarget] = useState<OrganizationMemberApi | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [updatingRoleId, setUpdatingRoleId] = useState<string | null>(null);

  const roleFilter = (params.filters?.role as string | undefined) ?? 'all';
  // Owners stay deletable as long as another owner remains. Only the LAST
  // owner is locked to keep the org from ending up ownerless.
  const ownerCount = rows.filter((r) => r.role === 'owner').length;
  const isLastOwner = (record: OrganizationMemberApi) => record.role === 'owner' && ownerCount <= 1;

  const handleRoleChange = useCallback(
    async (memberId: string, role: string) => {
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

  const handleRoleFilterChange = (val: string) => {
    const filters = { ...(params.filters ?? {}) };
    if (val === 'all') delete filters.role;
    else filters.role = val;
    onParamsChange({ filters });
  };

  const handleSortChange = (sort: CustomTableSortState | null) => {
    onParamsChange({
      sort_by: sort?.field,
      sort_order: sort?.order ?? 'desc',
    });
  };

  const columns: CustomTableColumn<OrganizationMemberApi>[] = [
    {
      key: 'sno',
      title: 'S.No',
      width: 'w-16',
      render: (_value, _record, index) => (
        <span className="text-muted-foreground">
          {((params.page ?? 1) - 1) * (params.page_size ?? 10) + index + 1}
        </span>
      ),
    },
    {
      key: 'name',
      title: 'Name',
      dataIndex: 'first_name',
      sorter: true,
      render: (_value, record) => (
        <div>
          <p className="text-sm font-medium text-foreground">{getDisplayName(record)}</p>
          <p className="text-xs text-muted-foreground">{record.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      title: 'Role',
      dataIndex: 'role',
      width: 'w-40',
      sorter: true,
      render: (_value, record) => {
        const isUpdating = updatingRoleId === record.member_id;
        // Lock role only for the last remaining owner — otherwise demoting
        // them would leave the org without an owner. Any other owner can be
        // re-assigned to a different role.
        const lockRole = isLastOwner(record);
        return (
          <SelectInput
            name={`role-${record.member_id}`}
            options={ROLE_OPTIONS}
            value={record.role}
            onValueChange={(val) => handleRoleChange(record.member_id, val)}
            disabled={lockRole || isUpdating}
            loading={isUpdating}
            size="sm"
          />
        );
      },
    },
    {
      key: 'status',
      title: 'Status',
      dataIndex: 'status',
      width: 'w-28',
      sorter: true,
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
        const lockDelete = isLastOwner(record);
        return (
          <CustomButton
            type="text"
            size="icon-xs"
            disabled={lockDelete}
            onClick={(e) => {
              e.stopPropagation();
              setDeleteTarget(record);
            }}
            aria-label={lockDelete ? 'Cannot remove the last owner' : 'Remove member'}
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
      <CustomTable
        columns={columns}
        dataSource={rows}
        rowKey="member_id"
        loading={loading}
        searchable
        searchPlaceholder="Search members by name or email…"
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
          <div className="w-36">
            <SelectInput
              name="role-filter"
              options={ROLE_FILTER_OPTIONS}
              value={roleFilter}
              onValueChange={handleRoleFilterChange}
              size="sm"
            />
          </div>
        }
      />
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
