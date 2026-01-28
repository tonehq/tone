import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';

import { constructColumns } from './constructTableColumn';

interface MenuItemType {
  key: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

export const getMemberColumns = (
  actionMenuItems: MenuItemType[],
  onRoleChange?: (memberId: number, role: string) => void,
  currentUserRole?: 'owner' | 'admin' | 'member' | 'viewer',
) => {
  const canManage = currentUserRole === 'owner' || currentUserRole === 'admin';

  const columns = [
    { key: 'user', title: 'User', sorter: true, width: 220 },
    { key: 'joined_at', title: 'Joined', sorter: true, width: 100 },
    { key: 'role', title: 'Role', width: 100 },
  ];

  if (canManage) {
    columns.push({ key: 'actions', title: '', width: 40 });
  }

  return constructColumns<OrganizationMemberApi>(columns, {
    actionMenuItems,
    onRoleChange,
    currentUserRole,
  });
};

export const getInvitationColumns = () =>
  constructColumns<OrganizationInviteApi>(
    [
      { key: 'user', title: 'User', sorter: true, width: 250 },
      { key: 'invitedDate', title: 'Invited', sorter: true, width: 150 },
      { key: 'status', title: 'Status', width: 100 },
      { key: 'actions', title: '', width: 40 },
    ],
    {
      actionMenuItems: [
        { key: 'resend', label: 'Resend Invitation' },
        { key: 'cancel', label: 'Cancel Invitation', danger: true },
      ],
    },
  );
