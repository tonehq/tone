import { useCallback, useMemo } from 'react';

import { useAtom, useSetAtom } from 'jotai';

import { loadableMembersRowsAtom, updateMemberRoleAtom } from '@/atoms/SettingsAtom';

import CustomTable from '@/components/shared/CustomTable';

import { filterByFields } from '@/utils/filter';
import { getMemberColumns } from '@/utils/settings';
import { showToast } from '@/utils/showToast';
import { CSS_HEIGHT_PRESETS } from '@/utils/table';

interface Props {
  search: string;
  userRole?: 'owner' | 'admin' | 'member' | 'viewer';
}

const MembersTab = ({ search, userRole }: Props) => {
  const [membersLoadable] = useAtom(loadableMembersRowsAtom);
  const updateMemberRole = useSetAtom(updateMemberRoleAtom);

  const isOwner = userRole === 'owner';
  const isAdmin = userRole === 'admin';
  const canManageMembers = isOwner || isAdmin;

  const handleRoleUpdate = useCallback(
    async (memberId: number, role: string) => {
      try {
        await updateMemberRole({ memberId, role });
        showToast({ status: 'success', message: 'Role updated successfully', variant: 'message' });
      } catch {}
    },
    [updateMemberRole],
  );

  const items = useMemo(
    () =>
      canManageMembers
        ? [
            { key: 'edit', label: 'Edit Role' },
            { key: 'remove', label: 'Remove User', danger: true },
          ]
        : [],
    [canManageMembers],
  );

  const memberColumns = useMemo(
    () => getMemberColumns(items, canManageMembers ? handleRoleUpdate : undefined, userRole),
    [items, handleRoleUpdate, canManageMembers, userRole],
  );

  const membersData = membersLoadable.state === 'hasData' ? membersLoadable.data : [];
  const membersLoading = membersLoadable.state === 'loading';

  const filteredMembersData = useMemo(() => {
    const term = search.trim().toLowerCase();
    const getFullName = (r: any) => [r?.first_name, r?.last_name].filter(Boolean).join(' ');
    return filterByFields(membersData, term, [
      (r: any) => getFullName(r),
      (r: any) => r?.username,
      (r: any) => r?.email,
    ]);
  }, [search, membersData]);

  return (
    <CustomTable
      rowKey={(r) => String(r.member_id)}
      columns={memberColumns}
      data={filteredMembersData}
      size="large"
      style={{ backgroundColor: 'white' }}
      loading={membersLoading}
      withPagination
      scroll={{ y: CSS_HEIGHT_PRESETS.SETTINGS }}
    />
  );
};

export default MembersTab;
