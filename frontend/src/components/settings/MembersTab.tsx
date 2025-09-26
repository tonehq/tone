import { useMemo } from 'react';

import { useAtom, useSetAtom } from 'jotai';

import { loadableMembersRowsAtom, updateMemberRoleAtom } from '@/atoms/SettingsAtom';

import CustomTable from '@/components/Shared/CustomTable';

import { filterByFields } from '@/utils/filter';
import { getMemberColumns } from '@/utils/settings';
import { showToast } from '@/utils/showToast';

interface Props {
  search: string;
}

const MembersTab = ({ search }: Props) => {
  const [membersLoadable] = useAtom(loadableMembersRowsAtom);
  const updateMemberRole = useSetAtom(updateMemberRoleAtom);

  const handleRoleUpdate = async (memberId: number, role: string) => {
    try {
      await updateMemberRole({ memberId, role });
      showToast({ status: 'success', message: 'Role updated successfully', variant: 'message' });
    } catch {}
  };

  const items = [
    { key: 'edit', label: 'Edit Role' },
    { key: 'remove', label: 'Remove User', danger: true },
  ];

  const memberColumns = useMemo(
    () => getMemberColumns(items, handleRoleUpdate),
    [items, handleRoleUpdate],
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
      minScrollYPx={180}
    />
  );
};

export default MembersTab;
