import { useDeferredValue, useState } from 'react';

import { Box, InputAdornment, useTheme } from '@mui/material';
import { useSetAtom } from 'jotai';
import { Mail, Search, UserPlus, Users } from 'lucide-react';

import {
  inviteUserToOrganizationAtom,
  refetchInvitationsAtom,
  refetchMembersAtom,
} from '@/atoms/SettingsAtom';

import ModalComponent from '@/components/settings/ModalComponent';
import CustomButton from '@/components/shared/CustomButton';
import { TextInput } from '@/components/shared/CustomFormFields';
import CustomTab from '@/components/shared/CustomTab';

import { TabItem } from '@/types/tab';

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
  const theme = useTheme();

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
      <Box
        sx={{
          backgroundColor: theme.palette.background.default,
          borderRadius: 2,
          overflow: 'hidden',
          p: 3,
          flexShrink: 0,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 3,
          }}
        >
          <Box sx={{ width: 320 }}>
            <TextInput
              name="search"
              type="search"
              placeholder="Search"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              withFormItem={false}
              fullWidth
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={16} style={{ color: theme.palette.text.secondary }} />
                  </InputAdornment>
                ),
              }}
            />
          </Box>
          <CustomButton
            text="Invite user"
            type="primary"
            icon={<UserPlus size={16} />}
            onClick={() => setInviteModalOpen(true)}
          />
        </Box>
        <CustomTab
          items={tabItems}
          activeKey={activeTab}
          onChange={handleTabChange}
          variant="underline"
          size="medium"
          animated={true}
        />
      </Box>
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
