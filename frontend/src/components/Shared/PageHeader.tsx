import React, { memo, useEffect } from 'react';

import { Avatar, Badge, Box, Button, IconButton, Stack, Typography } from '@mui/material';
import { useAtom, useSetAtom } from 'jotai';
import { Bell, LogOut, Settings, User } from 'lucide-react';

import { authAtom, getCurrentUserAtom, logoutAtom } from '@/atoms/AuthAtom';

import CustomBreadCrumb from '@/components/shared/CustomBreadCrumb';
import CustomDropdown from '@/components/shared/CustomDropdown';

import { getInitialsFromName } from '@/utils/format';

export interface ButtonConfig {
  key: string;
  label: string;
  icon?: React.ReactNode;
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  onClick: () => void;
  disabled?: boolean;
}

interface BreadcrumbItem {
  title: React.ReactNode;
  href?: string;
  className?: string;
}

interface PageHeaderProps {
  title: string;
  breadcrumbItems?: BreadcrumbItem[];
  breadcrumbItemRender?: (
    item: BreadcrumbItem,
    index: number,
    items: BreadcrumbItem[],
  ) => React.ReactNode;
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

  const avatarMenuItems = [
    {
      key: 'profile',
      label: (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 0.5 }}>
          <User size={16} />
          <Typography variant="body2">View Profile</Typography>
        </Box>
      ),
      onClick: handleProfileClick,
    },
    {
      key: 'settings',
      label: (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 0.5 }}>
          <Settings size={16} />
          <Typography variant="body2">Settings</Typography>
        </Box>
      ),
      onClick: () => console.log('Settings clicked'),
    },
    {
      key: 'logout',
      label: (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 0.5, color: 'error.main' }}>
          <LogOut size={16} />
          <Typography variant="body2" sx={{ color: 'error.main' }}>
            Logout
          </Typography>
        </Box>
      ),
      onClick: handleLogout,
      danger: true,
    },
  ];

  return (
    <Box
      sx={{
        width: '100%',
        backgroundColor: 'background.default',
        py: 1,
        px: 3,
        borderRadius: 2,
        boxShadow:
          '0 0 0 1px rgba(0, 0, 0, 0.05), 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06), 0 -2px 4px -1px rgba(0, 0, 0, 0.06)',
        margin: '0 0 16px 0',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Left section - Title and Breadcrumbs */}
        <Box sx={{ flex: 1 }}>
          <Typography
            variant="h3"
            sx={{
              marginTop: 0,
              marginBottom: 0,
              fontWeight: 600,
              color: 'text.primary',
              fontSize: '24px',
            }}
          >
            {title}
          </Typography>
          {breadcrumbItems.length > 0 && (
            <Box sx={{ mb: 1 }}>
              <CustomBreadCrumb items={breadcrumbItems} itemRender={breadcrumbItemRender} />
            </Box>
          )}
        </Box>

        {/* Right section - Search, Notifications, Avatar */}
        <Stack direction="row" spacing={2} alignItems="center">
          {/* Notifications */}
          {showNotifications && (
            <IconButton
              sx={{
                width: 40,
                height: 40,
                borderRadius: '50%',
                '&:hover': {
                  backgroundColor: '#f3f4f6',
                },
              }}
            >
              <Badge
                badgeContent={1}
                color="error"
                sx={{
                  '& .MuiBadge-badge': {
                    width: 8,
                    height: 8,
                    minWidth: 8,
                  },
                }}
              >
                <Bell size={18} />
              </Badge>
            </IconButton>
          )}

          {/* Action Buttons */}
          {buttons.length > 0 && (
            <Stack direction="row" spacing={1}>
              {buttons.map((button) => {
                const getVariant = () => {
                  if (button.type === 'primary') return 'contained';
                  if (button.type === 'text' || button.type === 'link') return 'text';
                  return 'outlined';
                };

                return (
                  <Button
                    key={button.key}
                    variant={getVariant()}
                    startIcon={button.icon}
                    onClick={button.onClick}
                    disabled={button.disabled}
                    sx={{
                      textTransform: 'none',
                      boxShadow: 1,
                      borderRadius: 2,
                      fontWeight: 500,
                    }}
                  >
                    {button.label}
                  </Button>
                );
              })}
            </Stack>
          )}

          {/* Avatar Dropdown */}
          {showAvatar && (
            <CustomDropdown items={avatarMenuItems}>
              <Avatar
                sx={{
                  width: 42,
                  height: 42,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  cursor: 'pointer',
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                  fontWeight: 600,
                }}
              >
                {getInitialsFromName(userName)}
              </Avatar>
            </CustomDropdown>
          )}
        </Stack>
      </Box>
    </Box>
  );
};

export default memo(PageHeader);
