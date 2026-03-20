'use client';

import {
  cancelInvitationAtom,
  inviteUserToOrganizationAtom,
  loadableInvitationsRowsAtom,
  loadableMembersRowsAtom,
  removeMemberAtom,
  updateMemberRoleAtom,
} from '@/atoms/SettingsAtom';
import { CustomButton, CustomTab } from '@/components/shared';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Loader2, Mail, UserPlus, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

import InvitationsTable from './InvitationsTable';
import InviteMemberModal from './InviteMemberModal';
import MembersTable from './MembersTable';

export default function Members() {
  const [mounted, setMounted] = useState(false);
  const [membersLoadable] = useAtom(loadableMembersRowsAtom);
  const [invitationsLoadable] = useAtom(loadableInvitationsRowsAtom);
  const [, inviteUser] = useAtom(inviteUserToOrganizationAtom);
  const [, updateRole] = useAtom(updateMemberRoleAtom);
  const [, removeMember] = useAtom(removeMemberAtom);
  const [, cancelInvite] = useAtom(cancelInvitationAtom);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleInviteSubmit = async (data: { name: string; email: string; role: string }) => {
    await inviteUser(data);
    showToast.success('Invitation sent successfully');
  };

  const handleRoleChange = async (memberId: number, role: string) => {
    try {
      await updateRole({ memberId, role });
      showToast.success('Role updated successfully');
    } catch (err) {
      handleApiError(err);
    }
  };

  const handleDeleteMember = async (userId: number) => {
    try {
      await removeMember(userId);
      showToast.success('Member removed successfully');
    } catch (err) {
      handleApiError(err);
    }
  };

  const handleCancelInvitation = async (inviteId: number) => {
    try {
      await cancelInvite(inviteId);
      showToast.success('Invitation cancelled');
    } catch (err) {
      handleApiError(err);
    }
  };

  if (!mounted) {
    return (
      <div className="flex h-full w-full items-center justify-center p-4">
        <Loader2 className="size-10 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const isMembersLoading = membersLoadable.state === 'loading';
  const memberRows = membersLoadable.state === 'hasData' ? membersLoadable.data : [];
  const isInvitationsLoading = invitationsLoadable.state === 'loading';
  const invitationRows = invitationsLoadable.state === 'hasData' ? invitationsLoadable.data : [];

  const tabItems = [
    {
      key: 'members',
      label: 'Members',
      icon: <Users className="size-4" />,
      children: (
        <div className="pt-4">
          <MembersTable
            rows={memberRows}
            loading={isMembersLoading}
            onRoleChange={handleRoleChange}
            onDelete={handleDeleteMember}
          />
        </div>
      ),
    },
    {
      key: 'invitations',
      label: 'Invitations',
      icon: <Mail className="size-4" />,
      children: (
        <div className="pt-4">
          <InvitationsTable
            rows={invitationRows}
            loading={isInvitationsLoading}
            onCancel={handleCancelInvitation}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="w-full">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Members</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your team and invite new members
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<UserPlus size={18} />}
          onClick={() => setModalOpen(true)}
        >
          Invite Member
        </CustomButton>
      </div>

      <CustomTab items={tabItems} defaultActiveKey="members" />

      <InviteMemberModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleInviteSubmit}
      />
    </div>
  );
}
