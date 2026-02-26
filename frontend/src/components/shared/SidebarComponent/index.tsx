'use client';

import React from 'react';
import { Box, Drawer, useMediaQuery, useTheme } from '@mui/material';
import { SidebarContent } from './SidebarContent';
import { SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED } from '@/constants/sidebar';

interface SidebarComponentProps {
  isExpanded: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const SidebarComponent = ({
  isExpanded,
  onToggle,
  mobileOpen,
  onMobileClose,
}: SidebarComponentProps) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  if (isMobile) {
    return (
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          '& .MuiDrawer-paper': {
            width: SIDEBAR_WIDTH_EXPANDED,
            boxSizing: 'border-box',
          },
        }}
      >
        <SidebarContent
          isExpanded={true}
          onToggle={onToggle}
          isMobile={true}
          onMenuClick={onMobileClose}
        />
      </Drawer>
    );
  }

  const boxSx = {
    width: isExpanded ? SIDEBAR_WIDTH_EXPANDED : SIDEBAR_WIDTH_COLLAPSED,
    height: '100vh',
    position: 'fixed' as const,
    left: 0,
    top: 0,
    borderRight: '1px solid',
    borderColor: 'divider',
    transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    overflow: 'hidden',
  };

  return (
    <Box sx={boxSx}>
      <SidebarContent isExpanded={isExpanded} onToggle={onToggle} isMobile={false} />
    </Box>
  );
};

export { SidebarComponent as default };
