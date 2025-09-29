import React, { memo, useEffect } from 'react';

import { Avatar, BreadcrumbProps, Button, Dropdown, MenuProps, Space, Typography } from 'antd';
import { useAtom, useSetAtom } from 'jotai';
import { Bell, LogOut, Settings, User } from 'lucide-react';

import { authAtom, getCurrentUserAtom, logoutAtom } from '@/atoms/AuthAtom';

import CustomBreadCrumb from '@/components/shared/CustomBreadCrumb';

import { cn } from '@/utils/cn';
import { getInitialsFromName } from '@/utils/format';

export interface ButtonConfig {
  key: string;
  label: string;
  icon?: React.ReactNode;
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  onClick: () => void;
  disabled?: boolean;
}

interface PageHeaderProps {
  title: string;
  breadcrumbItems?: BreadcrumbProps['items'];
  breadcrumbItemRender?: BreadcrumbProps['itemRender'];
  buttons?: ButtonConfig[];
  showAvatar?: boolean;
  showNotifications?: boolean;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  breadcrumbItems = [],
  breadcrumbItemRender,
  buttons = [],
  showAvatar = true,
  showNotifications = true,
}) => {
  const [authState] = useAtom(authAtom);
  const getCurrentUser = useSetAtom(getCurrentUserAtom);
  const logout = useSetAtom(logoutAtom);

  useEffect(() => {
    if (!authState.user && !authState.isLoading) {
      getCurrentUser();
    }
  }, [authState.user, authState.isLoading, getCurrentUser]);

  const handleLogout = () => {
    logout();
  };

  const handleProfileClick = () => {
    console.log('Profile clicked');
  };

  const userName = authState.user
    ? `${authState.user.first_name || ''} ${authState.user.last_name || ''}`.trim() ||
      authState.user.username ||
      authState.user.email
    : 'User';

  const avatarMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      label: (
        <div className="flex items-center gap-3 py-1">
          <User size={16} />
          <span>View Profile</span>
        </div>
      ),
      onClick: handleProfileClick,
    },
    {
      key: 'settings',
      label: (
        <div className="flex items-center gap-3 py-1">
          <Settings size={16} />
          <span>Settings</span>
        </div>
      ),
      onClick: () => console.log('Settings clicked'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      label: (
        <div className="flex items-center gap-3 py-1 text-red-600">
          <LogOut size={16} />
          <span>Logout</span>
        </div>
      ),
      onClick: handleLogout,
    },
  ];

  return (
    <div className="w-full bg-white shadow-sm border-b border-gray-100 py-2 px-6 rounded-lg">
      <div className="flex items-center justify-between">
        {/* Left section - Title and Breadcrumbs */}
        <div className="flex-1">
          <Typography.Title
            level={3}
            className="!mt-0 !mb-0 !font-semibold !text-gray-900 !text-2xl"
          >
            {title}
          </Typography.Title>
          {breadcrumbItems.length > 0 && (
            <div className="mb-1">
              <CustomBreadCrumb items={breadcrumbItems} itemRender={breadcrumbItemRender} />
            </div>
          )}
        </div>

        {/* Right section - Search, Notifications, Avatar */}
        <div className="flex items-center gap-4">
          {/* Notifications */}
          {showNotifications && (
            <Button
              type="text"
              icon={<Bell size={18} />}
              className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-gray-100 border-0 relative text-gray-500"
            >
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></span>
            </Button>
          )}

          {/* Action Buttons */}
          {buttons.length > 0 && (
            <Space size="small" className="ml-2">
              {buttons.map((button) => (
                <Button
                  key={button.key}
                  type={button.type || 'default'}
                  icon={button.icon}
                  onClick={button.onClick}
                  disabled={button.disabled}
                  className={cn('flex items-center shadow-sm rounded-lg font-medium')}
                >
                  {button.label}
                </Button>
              ))}
            </Space>
          )}

          {/* Avatar Dropdown */}
          {showAvatar && (
            <Dropdown
              menu={{ items: avatarMenuItems }}
              trigger={['click']}
              placement="bottomRight"
              overlayClassName={cn('min-w-64 shadow-lg rounded-xl overflow-hidden')}
            >
              <Avatar
                size={42}
                className={cn(
                  'text-white font-semibold text-base flex items-center justify-center shadow-md bg-gradient-to-br from-indigo-500 to-purple-600 cursor-pointer',
                )}
                style={{
                  backgroundColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                }}
              >
                {getInitialsFromName(userName)}
              </Avatar>
            </Dropdown>
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(PageHeader);
