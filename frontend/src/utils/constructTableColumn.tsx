import React from 'react';

import { Avatar, Box, Button, Chip, Typography, useTheme } from '@mui/material';
import { capitalize } from 'lodash';
import { MoreHorizontal } from 'lucide-react';

import CustomDropdown from '@/components/shared/CustomDropdown';
import { SelectInput, SelectOption } from '@/components/shared/CustomFormFields';

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

const RenderUser = ({ record }: { record: any }) => {
  const theme = useTheme();
  const rawName =
    [record.first_name, record.last_name].filter(Boolean).join(' ').trim() ||
    record.username ||
    record.email ||
    'Unknown User';
  const displayName = capitalize(rawName);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
      <Avatar
        sx={{
          width: 40,
          height: 40,
          backgroundColor: 'secondary.main',
          color: 'white',
          fontWeight: theme.custom.typography.fontWeight.bold,
          fontSize: theme.custom.typography.fontSize.base,
        }}
      >
        {getInitialsFromName(displayName)}
      </Avatar>
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="body2"
          sx={{ fontWeight: theme.custom.typography.fontWeight.medium, wordBreak: 'break-word' }}
        >
          {displayName}
        </Typography>
        {record.email && record.email !== displayName && (
          <Typography
            variant="caption"
            sx={{ color: 'text.secondary', wordBreak: 'break-word', display: 'block' }}
          >
            {record.email}
          </Typography>
        )}
      </Box>
    </Box>
  );
};

const renderUser = (record: any) => <RenderUser record={record} />;

const RenderInviteUser = ({ record }: { record: OrganizationInviteApi }) => {
  const theme = useTheme();
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
      <Avatar
        sx={{
          width: 40,
          height: 40,
          backgroundColor: 'secondary.main',
          color: 'white',
          fontWeight: theme.custom.typography.fontWeight.bold,
          fontSize: theme.custom.typography.fontSize.base,
        }}
      >
        {getInitialsFromName(record.name || record.username || record.email || '')}
      </Avatar>
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="body2"
          sx={{ fontWeight: theme.custom.typography.fontWeight.medium, wordBreak: 'break-word' }}
        >
          {record?.email}
        </Typography>
      </Box>
    </Box>
  );
};

const renderInviteUser = (record: OrganizationInviteApi) => (
  <RenderInviteUser record={record} />
);

const renderJoined = (value: number | null | undefined) => formatEpochToDate(value ?? null);

const renderRole = (
  role: string,
  record: OrganizationMemberApi,
  onRoleChange?: (memberId: number, role: string) => void,
) => {
  const roleOptions: SelectOption[] = [
    { value: 'admin', label: capitalize('admin') },
    { value: 'member', label: capitalize('member') },
  ];

  return (
    <SelectInput
      name={`role-${record?.member_id}`}
      value={role || ''}
      placeholder="Role"
      onChange={(e) => onRoleChange?.(Number(record?.member_id), e.target.value as string)}
      options={roleOptions}
      withFormItem={false}
      size="small"
      variant="standard"
      disableUnderline
      fullWidth={false}
    />
  );
};

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
          return <Box>{value ?? '-'}</Box>;
      }
    },
  }));
