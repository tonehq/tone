import { Avatar, Dropdown, MenuProps, Select, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { capitalize } from 'lodash';
import { MoreHorizontal } from 'lucide-react';

import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';
import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import { formatEpochToDate, getInitialsFromName } from '@/utils/format';

const { Option } = Select;

export const getMemberColumns = (
  actionMenuItems: MenuProps['items'],
  onRoleChange?: (memberId: number, role: string) => void,
): ColumnsType<OrganizationMemberApi> => [
  {
    title: 'User',
    dataIndex: 'name',
    key: 'user',
    sorter: true,
    width: 220,
    render: (_: any, record: OrganizationMemberApi) => {
      const rawName =
        [record.first_name, record.last_name].filter(Boolean).join(' ').trim() ||
        record.username ||
        record.email ||
        'Unknown User';
      const displayName = capitalize(rawName);
      return (
        <div className="flex items-center gap-2 min-w-0">
          <Avatar
            size={40}
            className="text-white font-bold text-base flex items-center justify-center"
            style={{
              backgroundColor: '#7c3aed',
            }}
          >
            {getInitialsFromName(rawName)}
          </Avatar>
          <div className="min-w-0">
            <div className="font-medium break-words">{displayName}</div>
            {record.email && record.email !== displayName && (
              <div className="text-gray-600 text-xs break-words">{record.email}</div>
            )}
          </div>
        </div>
      );
    },
  },
  {
    title: 'Joined',
    dataIndex: 'joined_at',
    key: 'joined',
    sorter: true,
    width: 100,
    render: (value: number | null | undefined) => formatEpochToDate(value ?? null),
  },
  {
    title: 'Role',
    dataIndex: 'role',
    key: 'role',
    width: 100,
    render: (role: string, record: any) => (
      <Select
        value={role}
        className="w-32"
        variant="borderless"
        suffixIcon={null}
        onChange={(val) => onRoleChange && onRoleChange(Number(record?.member_id ?? record?.id), val)}
      >
        <Option value="admin">{capitalize('admin')}</Option>
        <Option value="member">{capitalize('member')}</Option>
      </Select>
    ),
  },
  {
    title: '',
    key: 'actions',
    width: 40,
    render: (_: any, record: OrganizationMemberApi) => (
      <Dropdown
        menu={{
          items: actionMenuItems,
        }}
        trigger={['click']}
        getPopupContainer={(triggerNode) => triggerNode?.parentElement || document.body}
      >
        <ButtonComponent type="text" icon={<MoreHorizontal size={16} />} />
      </Dropdown>
    ),
  },
];

export const getInvitationColumns = (): ColumnsType<OrganizationInviteApi> => [
  {
    title: 'User',
    dataIndex: 'name',
    key: 'user',
    sorter: true,
    width: 250,
    render: (_: any, record: OrganizationInviteApi) => (
      <div className="flex items-center gap-2 min-w-0">
        <Avatar
          size={40}
          className="text-white font-bold text-base flex items-center justify-center"
          style={{
            backgroundColor: '#7c3aed',
          }}
        >
          {getInitialsFromName(record.name || record.username || record.email || '')}
        </Avatar>
        <div className="min-w-0">
          <div className="font-medium break-words">{record?.email}</div>
        </div>
      </div>
    ),
  },
  {
    title: 'Invited',
    dataIndex: 'invitedDate',
    key: 'invited',
    width: 150,
    sorter: true,
  },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    width: 100,
    render: (status: string) => {
      const normalized = (status || '').toString().toLowerCase();
      const color =
        normalized === 'pending'
          ? 'orange'
          : normalized === 'accepted'
          ? 'blue'
          : 'default';
      return <Tag color={color}>{capitalize(status)}</Tag>;
    },
  },
  {
    title: '',
    key: 'actions',
    width: 40,
    render: (_: any, record: OrganizationInviteApi) => (
      <Dropdown
        menu={{
          items: [
            { key: 'resend', label: 'Resend Invitation' },
            { key: 'cancel', label: 'Cancel Invitation', danger: true },
          ],
        }}
        trigger={['click']}
      >
        <ButtonComponent type="text" icon={<MoreHorizontal size={16} />} />
      </Dropdown>
    ),
  },
];
