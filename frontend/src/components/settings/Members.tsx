'use client';

import { useAtom } from 'jotai';
import { Mail, UserPlus, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  cancelInvitationAtom,
  invitationsParamsAtom,
  inviteUserToOrganizationAtom,
  loadableInvitationsPagedAtom,
  loadableMembersPagedAtom,
  membersParamsAtom,
  refetchInvitationsAtom,
  refetchMembersAtom,
  removeMemberAtom,
  resendInvitationAtom,
  setInvitationsParamsAtom,
  setMembersParamsAtom,
  updateMemberRoleAtom,
} from '@/atoms/SettingsAtom';
import { CustomButton, CustomTab } from '@/components/shared';
import ToneLoader from '@/components/shared/ToneLoader';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import InvitationsTable from './InvitationsTable';
import InviteMemberModal from './InviteMemberModal';
import MembersTable from './MembersTable';

export default function Members() {
  const [mounted, setMounted] = useState(false);
  const [membersLoadable] = useAtom(loadableMembersPagedAtom);
  const [invitationsLoadable] = useAtom(loadableInvitationsPagedAtom);
  const [membersParams] = useAtom(membersParamsAtom);
  const [invitationsParams] = useAtom(invitationsParamsAtom);
  const [, setMembersParams] = useAtom(setMembersParamsAtom);
  const [, setInvitationsParams] = useAtom(setInvitationsParamsAtom);
  const [, inviteUser] = useAtom(inviteUserToOrganizationAtom);
  const [, updateRole] = useAtom(updateMemberRoleAtom);
  const [, removeMember] = useAtom(removeMemberAtom);
  const [, cancelInvite] = useAtom(cancelInvitationAtom);
  const [, resendInvite] = useAtom(resendInvitationAtom);
  const [, refetchMembers] = useAtom(refetchMembersAtom);
  const [, refetchInvitations] = useAtom(refetchInvitationsAtom);
  const [modalOpen, setModalOpen] = useState(false);
  const [membersRefreshing, setMembersRefreshing] = useState(false);
  const [invitesRefreshing, setInvitesRefreshing] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleInviteSubmit = async (data: { name: string; email: string; role: string }) => {
    try {
      await inviteUser(data);
      showToast.success('Invitation sent successfully');
    } catch (err) {
      // Surface a toast so the user sees the failure even if the modal closes,
      // then re-throw so the modal's catch can also set the inline field error.
      handleApiError(err);
      throw err;
    }
  };

  const handleRoleChange = async (memberId: string, role: string) => {
    try {
      await updateRole({ memberId, role });
      showToast.success('Role updated successfully');
    } catch (err) {
      handleApiError(err);
    }
  };

  const handleDeleteMember = async (userId: string) => {
    try {
      await removeMember(userId);
      showToast.success('Member removed successfully');
    } catch (err) {
      handleApiError(err);
    }
  };

  const handleCancelInvitation = async (inviteId: string) => {
    try {
      await cancelInvite(inviteId);
      showToast.success('Invitation cancelled');
    } catch (err) {
      handleApiError(err);
    }
  };

  const handleResendInvitation = async (inviteId: string) => {
    try {
      await resendInvite(inviteId);
      showToast.success('Invitation re-sent');
    } catch (err) {
      handleApiError(err);
    }
  };

  const handleRefreshMembers = async () => {
    setMembersRefreshing(true);
    try {
      await refetchMembers();
    } finally {
      setTimeout(() => setMembersRefreshing(false), 400);
    }
  };

  const handleRefreshInvitations = async () => {
    setInvitesRefreshing(true);
    try {
      await refetchInvitations();
    } finally {
      setTimeout(() => setInvitesRefreshing(false), 400);
    }
  };

  if (!mounted) {
    return (
      <div className="flex h-full w-full items-center justify-center p-4">
        <ToneLoader label="Loading members..." />
      </div>
    );
  }

  const isMembersLoading = membersLoadable.state === 'loading';
  const membersData = membersLoadable.state === 'hasData' ? membersLoadable.data : null;
  const memberRows = membersData?.rows ?? [];
  const membersTotal = membersData?.total ?? 0;

  const isInvitationsLoading = invitationsLoadable.state === 'loading';
  const invitationsData = invitationsLoadable.state === 'hasData' ? invitationsLoadable.data : null;
  const invitationRows = invitationsData?.rows ?? [];
  const invitationsTotal = invitationsData?.total ?? 0;

  const tabItems = [
    {
      key: 'members',
      label: 'Members',
      icon: <Users className="size-4" />,
      children: (
        <div className="pt-4">
          <MembersTable
            rows={memberRows}
            total={membersTotal}
            params={membersParams}
            onParamsChange={setMembersParams}
            loading={isMembersLoading}
            onRoleChange={handleRoleChange}
            onDelete={handleDeleteMember}
            onRefresh={handleRefreshMembers}
            refreshing={membersRefreshing}
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
            total={invitationsTotal}
            params={invitationsParams}
            onParamsChange={setInvitationsParams}
            loading={isInvitationsLoading}
            onCancel={handleCancelInvitation}
            onResend={handleResendInvitation}
            onRefresh={handleRefreshInvitations}
            refreshing={invitesRefreshing}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="w-full">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            Members
          </h1>
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
