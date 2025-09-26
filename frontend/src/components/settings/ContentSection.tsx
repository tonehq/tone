import { useDeferredValue, useState } from 'react';

import { Input, Tabs } from 'antd';
import { useSetAtom } from 'jotai';
import { Search, UserPlus } from 'lucide-react';

import {
  inviteUserToOrganizationAtom,
  refetchInvitationsAtom,
  refetchMembersAtom,
} from '@/atoms/SettingsAtom';

import ModalComponent from '@/components/settings/ModalComponent';
import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';

import { settingsTabItems } from '@/constants/settings';

import { handleError } from '@/utils/handleError';
import { showToast } from '@/utils/showToast';

import InvitationsTab from './InvitationsTab';
import MembersTab from './MembersTab';

const ContentSection = () => {
  const [activeTab, setActiveTab] = useState('members');
  const [searchText, setSearchText] = useState('');
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const deferredSearch = useDeferredValue(searchText);

  const refetchMembers = useSetAtom(refetchMembersAtom);
  const refetchInvitations = useSetAtom(refetchInvitationsAtom);
  const inviteUser = useSetAtom(inviteUserToOrganizationAtom);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    setSearchText('');

    if (key === 'members') {
      refetchMembers();
    } else {
      refetchInvitations();
    }
  };

  const handleInviteUser = async (values: { name: string; email: string; role: string }) => {
    setLoading(true);
    try {
      await inviteUser(values);
      refetchInvitations();
      showToast({
        status: 'success',
        message: `Invitation sent to ${values.email}`,
        variant: 'message',
      });
      setInviteModalOpen(false);
    } catch (error) {
      handleError({ error });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px', backgroundColor: '#f5f5f5', height: 'calc(100vh - 75px)' }}>
      <div style={{ backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden' }}>
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={settingsTabItems}
          style={{ paddingLeft: '24px', marginBottom: 0 }}
          tabBarStyle={{ borderBottom: '1px solid #f0f0f0', marginBottom: '24px' }}
        />

        <div style={{ padding: '0 24px 0 24px' }}>
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
              active
            />
          </div>

          {/* Lazy-load tabs */}
          {activeTab === 'members' ? (
            <MembersTab search={deferredSearch} />
          ) : (
            <InvitationsTab search={deferredSearch} />
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

export default ContentSection;
