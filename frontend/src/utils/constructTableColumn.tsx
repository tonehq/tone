import React from 'react';

import { Avatar, Button, Chip, Select, MenuItem, FormControl } from '@mui/material';
import { capitalize } from 'lodash';
import { MoreHorizontal } from 'lucide-react';

import CustomDropdown from '@/components/shared/CustomDropdown';

import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';

import { formatEpochToDate, getInitialsFromName } from '@/utils/format';

// Define column type for MUI table compatibility
export interface TableColumn<T> {
  title: string;
  key: string;
  dataIndex: string;
  width?: number;
  sorter?: boolean;
  render?: (value: any, record: T) => React.ReactNode;
}

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
        sx={{
          width: 40,
          height: 40,
          backgroundColor: '#7c3aed',
          color: 'white',
          fontWeight: 'bold',
          fontSize: '16px',
        }}
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
      sx={{
        width: 40,
        height: 40,
        backgroundColor: '#7c3aed',
        color: 'white',
        fontWeight: 'bold',
        fontSize: '16px',
      }}
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
  <FormControl size="small" sx={{ minWidth: 128 }}>
  <Select
    value={role}
      onChange={(e) => onRoleChange?.(Number(record?.member_id), e.target.value)}
      variant="standard"
      disableUnderline
      sx={{
        fontSize: '14px',
        '& .MuiSelect-select': {
          padding: '4px 8px',
        },
      }}
    >
      <MenuItem value="admin">{capitalize('admin')}</MenuItem>
      <MenuItem value="member">{capitalize('member')}</MenuItem>
  </Select>
  </FormControl>
);

const renderStatus = (status: string) => {
  const normalized = (status || '').toLowerCase();
  const colorMap: Record<
    string,
    'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
  > = {
    pending: 'warning',
    accepted: 'info',
    default: 'default',
  };
  const color = colorMap[normalized] || 'default';
  return <Chip label={capitalize(status)} color={color} size="small" />;
};

interface MenuItemType {
  key: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

const renderActions = (items: MenuItemType[]) => (
  <CustomDropdown items={items}>
    <Button type="button" variant="text" sx={{ minWidth: 'auto', padding: '4px' }}>
      <MoreHorizontal size={16} />
    </Button>
  </CustomDropdown>
);

interface ColumnConfig {
  key: string;
  title?: string;
  width?: number;
  sorter?: boolean;
}

interface ExtraHandlers {
  onRoleChange?: (memberId: number, role: string) => void;
  actionMenuItems?: MenuItemType[];
}

export const constructColumns = <T extends object>(
  configs: ColumnConfig[],
  extra?: ExtraHandlers,
): TableColumn<T>[] =>
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
