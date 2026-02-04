'use client';

import { Avatar, Box, Divider, IconButton, Tooltip, Typography } from '@mui/material';
import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React from 'react';
import ProfileMenu from '../userMenu';
import { sidemenu } from './constant';

interface SidebarItemProps {
  icon: React.ElementType;
  href: string;
  active?: boolean;
  title?: string;
  isCollapsed: boolean;
}

function SidebarItemMenu({ icon: Icon, href, active, title, isCollapsed }: SidebarItemProps) {
  const content = (
    <Box
      component={Link}
      href={href}
      sx={{
        display: 'flex',
        alignItems: 'center',
        borderRadius: '8px',
        cursor: 'pointer',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        transition: 'all 0.2s',
        textDecoration: 'none',
        ...(isCollapsed
          ? {
              justifyContent: 'center',
              width: 40,
              height: 40,
              mx: 'auto',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
              },
            }
          : {
              width: '100%',
              py: 1.5,
              px: 2,
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
              },
            }),
        ...(active && {
          backgroundColor: 'rgba(255, 255, 255, 0.15)',
        }),
      }}
    >
      <Icon
        size={20}
        style={{
          color: active ? '#ffffff' : 'rgba(255, 255, 255, 0.7)',
          ...(!isCollapsed && { marginRight: '12px' }),
        }}
      />
      {!isCollapsed && (
        <Typography
          variant="body2"
          sx={{
            color: active ? '#ffffff' : 'rgba(255, 255, 255, 0.7)',
            fontWeight: active ? 600 : 500,
            fontSize: '0.875rem',
          }}
        >
          {title}
        </Typography>
      )}
    </Box>
  );

  return isCollapsed ? (
    <Tooltip title={title} placement="right">
      {content}
    </Tooltip>
  ) : (
    content
  );
}

interface SidebarProps {
  drawerWidth?: number;
  collapsedWidth?: number;
  isExpanded?: boolean;
  onToggle?: () => void;
}

function Sidebar({ isExpanded = true, onToggle }: SidebarProps) {
  const pathname = usePathname();

  const isActive = (path: string) => pathname === path || pathname?.startsWith(`${path}/`);

  return (
    <Box
      sx={{
        flexShrink: 0,
        height: '100vh',
        background: 'linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.3s ease',
        position: 'fixed',
        left: 0,
        top: 0,
        zIndex: 1200,
      }}
    >
      {/* Logo */}
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: isExpanded ? 'flex-start' : 'center',
          gap: 1,
        }}
      >
        <Box
          sx={{
            width: 32,
            height: 32,
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: '1.25rem',
            color: '#1e1b4b',
          }}
        >
          T
        </Box>
        {isExpanded && (
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: '1.125rem',
              color: '#ffffff',
            }}
          >
            ToneHq
          </Typography>
        )}
      </Box>

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.1)', mx: 2 }} />

      {/* Expand/Collapse button - floating on right edge */}
      {onToggle && (
        <Tooltip title={isExpanded ? 'Collapse sidebar' : 'Expand sidebar'} placement="right">
          <IconButton
            onClick={onToggle}
            sx={{
              position: 'absolute',
              right: -14,
              top: 48,
              width: 32,
              height: 32,
              borderRadius: '50%',
              backgroundColor: 'white',
              color: '#4b5563',
              boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
              zIndex: 1300,
              '&:hover': {
                backgroundColor: '#e5e7eb',
              },
            }}
          >
            {isExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </IconButton>
        </Tooltip>
      )}

      {/* Organization Selector */}
      <Box sx={{ p: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            p: isExpanded ? 1.5 : 0.5,
            borderRadius: '8px',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.15)',
            },
          }}
        >
          <Avatar
            sx={{
              width: 32,
              height: 32,
              backgroundColor: '#8b5cf6',
              fontSize: '0.875rem',
              fontWeight: 600,
            }}
          >
            M
          </Avatar>
          {isExpanded && (
            <>
              <Box sx={{ flex: 1 }}>
                <Typography
                  sx={{
                    color: '#ffffff',
                    fontWeight: 600,
                    fontSize: '0.875rem',
                    lineHeight: 1.2,
                  }}
                >
                  My Workspace
                </Typography>
                <Typography
                  sx={{
                    color: 'rgba(255, 255, 255, 0.6)',
                    fontSize: '0.75rem',
                  }}
                >
                  1 Member
                </Typography>
              </Box>
              <ChevronDown size={16} color="rgba(255, 255, 255, 0.6)" />
            </>
          )}
        </Box>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.1)', mx: 2 }} />

      {/* Navigation Menu */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          py: 2,
          px: isExpanded ? 2 : 1,
        }}
      >
        <Box
          component="nav"
          sx={{
            display: 'flex',
            flexDirection: 'column',
            gap: 0.5,
            ...(!isExpanded && { alignItems: 'center' }),
          }}
        >
          {sidemenu.map((item) => (
            <SidebarItemMenu
              key={item.key}
              icon={item.icon}
              title={item.title}
              href={item.path}
              active={isActive(item.path)}
              isCollapsed={!isExpanded}
            />
          ))}
        </Box>
      </Box>

      {/* Bottom Section */}
      <ProfileMenu isExpanded={isExpanded} />
    </Box>
  );
}

export default Sidebar;
