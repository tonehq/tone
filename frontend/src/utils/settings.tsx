import { MenuProps, Select } from 'antd';

import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import { constructColumns } from './constructTableColumn';

const { Option } = Select;

export const getMemberColumns = (
  actionMenuItems: MenuProps['items'],
  onRoleChange?: (memberId: number, role: string) => void
) =>
  constructColumns<OrganizationMemberApi>(
    [
      { key: 'user', title: 'User', sorter: true, width: 220 },
      { key: 'joined_at', title: 'Joined', sorter: true, width: 100 },
      { key: 'role', title: 'Role', width: 100 },
      { key: 'actions', title: '', width: 40 },
    ],
    { actionMenuItems, onRoleChange }
  );

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
    }
  );
