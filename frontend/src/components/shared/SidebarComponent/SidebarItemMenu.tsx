'use client';

import { Box, Tooltip, Typography } from '@mui/material';
import Link from 'next/link';
import { SIDEBAR_HOVER_ACTIVE } from '@/constants/sidebar';
import type { SidebarMenuItem } from '@/types/sidebar';

export interface SidebarItemMenuProps {
  item: SidebarMenuItem;
  active: boolean;
  isCollapsed: boolean;
  onClick?: () => void;
}

const ICON_SIZE = 22;

export function SidebarItemMenu({ item, active, isCollapsed, onClick }: SidebarItemMenuProps) {
  const { icon: Icon, path, title } = item;

  const content = (
    <Box
      component={Link}
      href={path}
      onClick={onClick}
      sx={{
        display: 'flex',
        alignItems: 'center',
        borderRadius: 1,
        textDecoration: 'none',
        color: 'white',
        cursor: 'pointer',
        transition: 'background-color 0.2s',
        ...(isCollapsed
          ? {
              justifyContent: 'center',
              width: 40,
              height: 40,
              mx: 'auto',
            }
          : {
              px: 2,
              py: 1.25,
              gap: 1.5,
            }),
        ...(active && {
          backgroundColor: SIDEBAR_HOVER_ACTIVE,
        }),
        '&:hover': {
          backgroundColor: SIDEBAR_HOVER_ACTIVE,
          color: 'black',
        },
      }}
    >
      <Icon size={ICON_SIZE} color={active ? 'black' : 'white'} />
      {!isCollapsed && (
        <Typography
          variant="body2"
          sx={{
            fontWeight: 400,
            color: active ? 'text.primary' : 'white',
            '&:hover': {
              color: 'black',
              fontWeight: 400,
            },
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
