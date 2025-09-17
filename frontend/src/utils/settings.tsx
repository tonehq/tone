import '@/styles/settings-table.scss';
import '@/styles/text.scss';
import { Avatar, Dropdown, MenuProps, Select, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { capitalize } from 'lodash';
import { MoreHorizontal } from 'lucide-react';

import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';
import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import { formatEpochToDate, getInitialsFromName } from '@/utils/format';

const { Option } = Select;

export const getMemberColumns = (
  actionMenuItems: MenuProps['items']
): ColumnsType<OrganizationMemberApi> => [
  {
    title: 'User',
    dataIndex: 'name',
    key: 'user',
    width: 220,
    // Use wrapping instead of ellipsis
    render: (_: any, record: OrganizationMemberApi) => {
      const rawName = [record.first_name, record.last_name].filter(Boolean).join(' ').trim() || record.username || record.email || 'Unknown User';
      const displayName = capitalize(rawName);
      return (
        <Space className="memberCell">
          <Avatar size={40} className="memberAvatar">
            {getInitialsFromName(rawName)}
          </Avatar>
          <div className="memberTextWrap">
            <div className="memberName text-wrap">{displayName}</div>
            {record.email && record.email !== displayName && (
              <div className="memberEmail text-wrap">{record.email}</div>
            )}
          </div>
        </Space>
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
    render: (role: string) => (
      <Select value={role} className="roleSelect" variant="borderless" suffixIcon={null}>
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
    width: 250,
    // Use wrapping instead of ellipsis
    render: (_: any, record: OrganizationInviteApi) => (
      <Space className="memberCell">
        <Avatar size={40} className="memberAvatar">
          {getInitialsFromName(record.name || record.username || record.email || '')}
        </Avatar>
        <div className="memberTextWrap">
          <div className="memberName text-wrap">{record?.email}</div>
        </div>
      </Space>
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
      const color = normalized === 'pending' ? 'orange' : normalized === 'accepted' ? 'blue' : 'default';
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


