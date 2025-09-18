import { useDeferredValue, useMemo, useState } from 'react';

import {
  Input,
  MenuProps,
  Tabs
} from 'antd';
import { useAtom, useSetAtom } from 'jotai';
import { Search, UserPlus } from 'lucide-react';

import { inviteUserToOrganizationAtom, loadableInvitationsRowsAtom, loadableMembersRowsAtom, refetchInvitationsAtom, refetchMembersAtom, updateMemberRoleAtom } from '@/atoms/SettingsAtom';

import ModalComponent from '@/components/settings/ModalComponent';
import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';

import CustomTable from '@/components/Shared/CustomTable';
import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import { filterByFields } from '@/utils/filter';
import { handleError } from '@/utils/handleError';
import { getInvitationColumns, getMemberColumns } from '@/utils/settings';
import { showToast } from '@/utils/showToast';

const MembersTable = () => {
  const [activeTab, setActiveTab] = useState('members');
  const [searchText, setSearchText] = useState('');
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const deferredSearch = useDeferredValue(searchText);

  // Loadable atoms
  const [membersLoadable] = useAtom(loadableMembersRowsAtom);
  const [invitationsLoadable] = useAtom(loadableInvitationsRowsAtom);
  const refetchMembers = useSetAtom(refetchMembersAtom);
  const refetchInvitations = useSetAtom(refetchInvitationsAtom);
  const inviteUser = useSetAtom(inviteUserToOrganizationAtom);

  const handleInviteUser = async (values: { name: string; email: string; role: string }) => {
    setLoading(true);
    try {
      await inviteUser({ name: values.name, email: values.email, role: values.role });
      refetchInvitations();
      showToast({
        status: 'success',
        message: `Invitation sent to ${values.email}`,
        variant: 'message',
      })
      setInviteModalOpen(false);
    } catch (error) {
      handleError({ error })
        } finally {
      setLoading(false);
    }
  };

  // Resolve data from loadables (raw API arrays)
  const membersData: OrganizationMemberApi[] =
    membersLoadable.state === 'hasData' ? (membersLoadable.data as OrganizationMemberApi[]) : [];
  const invitationsData: OrganizationInviteApi[] =
    invitationsLoadable.state === 'hasData'
      ? (invitationsLoadable.data as OrganizationInviteApi[])
      : [];
  const membersLoading = membersLoadable.state === 'loading';
  const invitationsLoading = invitationsLoadable.state === 'loading';

  const items: MenuProps['items'] = [
    {
      key: 'edit',
      label: 'Edit Role',
    },
    {
      key: 'remove',
      label: 'Remove User',
      danger: true,
    },
  ];

  const updateMemberRole = useSetAtom(updateMemberRoleAtom);

  const handleRoleUpdate = async (memberId: number, role: string) => {
    try {
      await updateMemberRole({ memberId, role });
      showToast({
        status: 'success',
        message: 'Role updated successfully',
        variant: 'message',
      });
    } catch (e) {}
  }

  const memberColumns = useMemo(() => getMemberColumns(items, handleRoleUpdate), [items, handleRoleUpdate]);
  const invitationColumns = useMemo(() => getInvitationColumns(), []);

  const tabItems = [
    {
      key: 'members',
      label: 'Members',
    },
    {
      key: 'invitations',
      label: 'Invitations',
    },
  ];

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    setSearchText('');
    if (key === 'members') {
      refetchMembers();
    } else {
      refetchInvitations();
    }
  };

  // Filter helpers
  const filteredMembersData = useMemo(() => {
    const term = deferredSearch.trim().toLowerCase();
    const getFullName = (r: any) => [r?.first_name, r?.last_name].filter(Boolean).join(' ');
    return filterByFields(membersData, term, [(r: any) => getFullName(r), (r: any) => r?.username, (r: any) => r?.email]);
  }, [deferredSearch, membersData]);

  const filteredInvitationsData = useMemo(() => {
    const term = deferredSearch.trim().toLowerCase();
    return filterByFields(invitationsData, term, [(r: any) => r?.name, (r: any) => r?.username, (r: any) => r?.email]);
  }, [deferredSearch, invitationsData]);

  return (
    <div style={{ padding: '24px', backgroundColor: '#f5f5f5', height: 'calc(100vh - 75px)' }}>
      <div style={{ backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden' }}>
        {/* Tabs Navigation */}
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={tabItems}
          style={{
            paddingLeft: '24px',
            marginBottom: 0,
          }}
          tabBarStyle={{
            borderBottom: '1px solid #f0f0f0',
            marginBottom: '24px',
          }}
        />

        {/* Table Content */}
        <div style={{ padding: '0 24px 0 24px' }}>
          {/* Header Controls */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <Input
              placeholder="Search..."
              value={searchText}
              onChange={(e: any) => setSearchText(e.target.value)}
              style={{ width: 300 }}
              prefix={<Search size={16} color="#c1bfbf" style={{ marginRight: 8 }} />}
            />
            <ButtonComponent
              text="Invite user"
              type="primary"
              icon={<UserPlus size={16} />}
              onClick={() => setInviteModalOpen(true)}
              active={true}
            />
          </div>

          {/* Table */}
          {activeTab === 'members' ? (
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
          ) : (
            <CustomTable
              rowKey={(r) => String(r.member_id)}
              columns={invitationColumns}
              data={filteredInvitationsData}
              size="large"
              style={{ backgroundColor: 'white' }}
              loading={invitationsLoading}
              withPagination
              minScrollYPx={180}
            />
          )}
        </div>
      </div>
      <ModalComponent
        open={inviteModalOpen}
        onCancel={() => setInviteModalOpen(false)}
        onInvite={handleInviteUser}
        loading={loading}
      />
    </div>
  );
};

export default MembersTable;
