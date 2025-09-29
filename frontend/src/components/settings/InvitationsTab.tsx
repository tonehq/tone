import { useMemo } from 'react';

import { useAtom } from 'jotai';

import { loadableInvitationsRowsAtom } from '@/atoms/SettingsAtom';

import CustomTable from '@/components/Shared/CustomTable';

import { filterByFields } from '@/utils/filter';
import { getInvitationColumns } from '@/utils/settings';
import { CSS_HEIGHT_PRESETS } from '@/utils/table';

interface Props {
  search: string;
}

const InvitationsTab = ({ search }: Props) => {
  const [invitationsLoadable] = useAtom(loadableInvitationsRowsAtom);

  const invitationsData = invitationsLoadable.state === 'hasData' ? invitationsLoadable.data : [];
  const invitationsLoading = invitationsLoadable.state === 'loading';

  const filteredInvitationsData = useMemo(() => {
    const term = search.trim().toLowerCase();
    return filterByFields(invitationsData, term, [
      (r: any) => r?.name,
      (r: any) => r?.username,
      (r: any) => r?.email,
    ]);
  }, [search, invitationsData]);

  const invitationColumns = useMemo(() => getInvitationColumns(), []);

  return (
    <CustomTable
      rowKey={(r) => String(r.member_id)}
      columns={invitationColumns}
      data={filteredInvitationsData}
      size="large"
      style={{ backgroundColor: 'white' }}
      loading={invitationsLoading}
      withPagination
      scroll={{ y: CSS_HEIGHT_PRESETS.SETTINGS }}
    />
  );
};

export default InvitationsTab;
