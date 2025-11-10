'use client';

import type React from 'react';

import { Box, Divider, IconButton, Tooltip, Typography, useTheme } from '@mui/material';
import { ArrowLeftToLine, ArrowRightToLine } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import Organization from '../Organization';
import { sidemenu } from './constant';

interface SidebarItemProps {
  icon: React.ElementType;
  href: string;
  active?: boolean;
  title?: string;
  isCollapsed: boolean;
}

function SidebarItemMenu({ icon: Icon, href, active, title, isCollapsed }: SidebarItemProps) {
  const theme = useTheme();
  const content = (
    <Box
      component={Link}
      href={href}
      sx={{
        display: 'flex',
        alignItems: 'center',
        borderRadius: 1,
        cursor: 'pointer',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        transition: 'all 0.2s',
        ...(isCollapsed
          ? {
              justifyContent: 'center',
              width: 40,
              height: 40,
              mx: 'auto',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
              },
            }
          : {
              width: '100%',
              py: 1.5,
              px: 2,
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
              },
            }),
        ...(active && {
          backgroundColor: 'rgba(255, 255, 255, 0.2)',
        }),
      }}
    >
      <Icon
        size={20}
        style={{
          color: theme.palette.common.white,
          ...(!isCollapsed && { marginRight: theme.spacing(1.5) }),
        }}
      />
      {!isCollapsed && (
        <Typography
          variant="body2"
          sx={{
            color: theme.palette.common.white,
            fontWeight: 500,
          }}
        >
          {title}
        </Typography>
      )}
    </Box>
  );

  return isCollapsed ? (
    <Tooltip title={title} placement="right" arrow>
      {content}
    </Tooltip>
  ) : (
    content
  );
}

function Sidebar(props: any) {
  const { isSidebarExpanded, setIsSidebarExpanded } = props;
  const pathname = usePathname();
  const theme = useTheme();

  const isActive = (path: string) =>
    pathname === path || pathname?.split('/')[1] === path.split('/')[1];

  return (
    <Box
      component="aside"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#3f3f46',
        gap: 1,
      }}
    >
      {/* Header Section */}
      <Box sx={{ flexShrink: 0 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              ...(!isSidebarExpanded && { mx: 'auto' }),
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 36,
                height: 36,
                backgroundColor: theme.palette.primary.main,
                borderRadius: 1,
                color: theme.palette.common.white,
                fontWeight: 600,
                fontSize: '1.125rem',
              }}
            >
              T
            </Box>
            {isSidebarExpanded && (
              <Typography
                variant="h6"
                sx={{
                  color: theme.palette.common.white,
                  fontWeight: 600,
                }}
              >
                Tone App
              </Typography>
            )}
          </Box>
          {isSidebarExpanded && (
            <IconButton
              onClick={() => setIsSidebarExpanded(false)}
              sx={{
                width: 32,
                height: 32,
                padding: 1,
                borderRadius: 0.5,
                backgroundColor: theme.palette.grey[100],
                '&:hover': {
                  backgroundColor: theme.palette.grey[200],
                },
              }}
            >
              <ArrowLeftToLine size={18} style={{ color: theme.palette.grey[700] }} />
            </IconButton>
          )}
        </Box>
      </Box>

      <Divider sx={{ borderColor: '#736f6f', margin: '8px 0' }} />

      {/* Expand Button (Collapsed Only) */}
      {!isSidebarExpanded && (
        <>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              gap: 1,
            }}
          >
            <IconButton
              onClick={() => setIsSidebarExpanded(true)}
              sx={{
                width: 40,
                height: 40,
                padding: 1.5,
                borderRadius: 0.5,
                backgroundColor: '#f0f0f0',
                '&:hover': {
                  backgroundColor: theme.palette.grey[200],
                },
              }}
            >
              <ArrowRightToLine size={18} style={{ color: '#414651' }} />
            </IconButton>
          </Box>
          <Divider sx={{ borderColor: '#736f6f', margin: '8px 0' }} />
        </>
      )}

      {/* Scrollable Content */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
        }}
      >
        {/* Organization Section */}
        <Box sx={{ mb: 2 }}>
          <Organization isSidebarExpanded={isSidebarExpanded} />
        </Box>

        <Divider sx={{ borderColor: '#736f6f', margin: '8px 0' }} />

        {/* Navigation Menu */}
        <Box
          component="nav"
          sx={{
            display: 'flex',
            flexDirection: 'column',
            ...(!isSidebarExpanded ? { alignItems: 'center', gap: 1 } : { gap: 1 }),
          }}
        >
          {sidemenu.map((item: any) => (
            <SidebarItemMenu
              key={item.key}
              icon={item.icon}
              title={item.title}
              href={item.path}
              active={isActive(item.path)}
              isCollapsed={!isSidebarExpanded}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
}

export default Sidebar;
