import { useDeferredValue, useState } from 'react';

import { Input } from 'antd';
import { useSetAtom } from 'jotai';
import { Mail, Search, UserPlus, Users } from 'lucide-react';

import {
  inviteUserToOrganizationAtom,
  refetchInvitationsAtom,
  refetchMembersAtom,
} from '@/atoms/SettingsAtom';

import ModalComponent from '@/components/settings/ModalComponent';
import CustomTab from '@/components/Shared/CustomTab';
import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';

import { TabItem } from '@/types/tab';

import { cn } from '@/utils/cn';
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

  const tabItems: TabItem[] = [
    {
      key: 'members',
      label: 'Members',
      icon: <Users size={16} />,
      content: <MembersTab search={deferredSearch} />,
    },
    {
      key: 'invitations',
      label: 'Invitations',
      icon: <Mail size={16} />,
      content: <InvitationsTab search={deferredSearch} />,
    },
  ];

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
    <>
      <div className={cn('bg-white rounded-lg overflow-hidden p-6')}>
        <div className={cn('flex justify-between items-center mb-6')}>
          <Input
            placeholder="Search"
            value={searchText}
            onChange={(e: any) => setSearchText(e.target.value)}
            className={cn('!w-80')}
            prefix={<Search size={16} className={cn('text-gray-400 mr-2')} />}
          />
          <ButtonComponent
            text="Invite user"
            type="primary"
            icon={<UserPlus size={16} />}
            onClick={() => setInviteModalOpen(true)}
            active
          />
        </div>

        <CustomTab
          items={tabItems}
          activeKey={activeTab}
          onChange={handleTabChange}
          variant="underline"
          size="medium"
          animated={true}
        />
      </div>
      <ModalComponent
        open={inviteModalOpen}
        onCancel={() => setInviteModalOpen(false)}
        onInvite={handleInviteUser}
        loading={loading}
      />
    </>
  );
};

export default ContentSection;
