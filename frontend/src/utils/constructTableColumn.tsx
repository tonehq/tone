import { Avatar, Dropdown, MenuProps, Select, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { capitalize } from 'lodash';
import { MoreHorizontal } from 'lucide-react';

import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';

import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';

import { formatEpochToDate, getInitialsFromName } from '@/utils/format';

const { Option } = Select;

const renderUser = (record: any) => {
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
        style={{ backgroundColor: '#7c3aed' }}
      >
        {getInitialsFromName(displayName)}
      </Avatar>
      <div className="min-w-0">
        <div className="font-medium break-words">{displayName}</div>
        {record.email && record.email !== displayName && (
          <div className="text-gray-600 text-xs break-words">{record.email}</div>
        )}
      </div>
    </div>
  );
};

const renderInviteUser = (record: OrganizationInviteApi) => (
  <div className="flex items-center gap-2 min-w-0">
    <Avatar
      size={40}
      className="text-white font-bold text-base flex items-center justify-center"
      style={{ backgroundColor: '#7c3aed' }}
    >
      {getInitialsFromName(record.name || record.username || record.email || '')}
    </Avatar>
    <div className="min-w-0">
      <div className="font-medium break-words">{record?.email}</div>
    </div>
  </div>
);

const renderJoined = (value: number | null | undefined) => formatEpochToDate(value ?? null);

const renderRole = (
  role: string,
  record: OrganizationMemberApi,
  onRoleChange?: (memberId: number, role: string) => void,
) => (
  <Select
    value={role}
    className="w-32"
    variant="borderless"
    suffixIcon={null}
    onChange={(val) => onRoleChange?.(Number(record?.member_id), val)}
  >
    <Option value="admin">{capitalize('admin')}</Option>
    <Option value="member">{capitalize('member')}</Option>
  </Select>
);

const renderStatus = (status: string) => {
  const normalized = (status || '').toLowerCase();
  const color =
    normalized === 'pending' ? 'orange' : normalized === 'accepted' ? 'blue' : 'default';
  return <Tag color={color}>{capitalize(status)}</Tag>;
};

const renderActions = (items: MenuProps['items']) => (
  <Dropdown menu={{ items }} trigger={['click']}>
    <ButtonComponent type="text" icon={<MoreHorizontal size={16} />} />
  </Dropdown>
);

interface ColumnConfig {
  key: string;
  title?: string;
  width?: number;
  sorter?: boolean;
}

interface ExtraHandlers {
  onRoleChange?: (memberId: number, role: string) => void;
  actionMenuItems?: MenuProps['items'];
}

export const constructColumns = <T extends object>(
  configs: ColumnConfig[],
  extra?: ExtraHandlers,
): ColumnsType<T> =>
  configs.map((col) => ({
    title: col.title || '',
    key: col.key,
    dataIndex: col.key,
    width: col.width,
    sorter: col.sorter,
    render: (value: any, record: any) => {
      switch (col.key) {
        case 'user':
          return 'first_name' in record || 'last_name' in record
            ? renderUser(record)
            : renderInviteUser(record as OrganizationInviteApi);
        case 'joined':
          return renderJoined(value);
        case 'role':
          return renderRole(value, record, extra?.onRoleChange);
        case 'status':
          return renderStatus(value);
        case 'actions':
          return renderActions(extra?.actionMenuItems ?? []);
        default:
          return <div>{value ?? '-'}</div>;
      }
    },
  }));
