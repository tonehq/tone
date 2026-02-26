'use client';

import ProfileMenu from '@/components/shared/userMenu';
import { Box, Divider } from '@mui/material';
import { SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED } from '@/constants/sidebar';
import { SidebarHeader } from './SidebarHeader';
import { SidebarNav } from './SidebarNav';
import { SidebarOrganization } from './SidebarOrganization';

export interface SidebarContentProps {
  isExpanded: boolean;
  onToggle: () => void;
  isMobile?: boolean;
  onMenuClick?: () => void;
}

export function SidebarContent({
  isExpanded,
  onToggle,
  isMobile = false,
  onMenuClick,
}: SidebarContentProps) {
  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        width: isExpanded ? SIDEBAR_WIDTH_EXPANDED : SIDEBAR_WIDTH_COLLAPSED,
        transition: 'width 0.3s',
        background: 'linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%)',
        overflow: 'hidden',
        color: 'white',
        borderRadius: '5px',
      }}
    >
      <SidebarHeader isExpanded={isExpanded} onToggle={onToggle} isMobile={isMobile} />

      <Divider sx={{ mx: 1, color: '#f5f5f5' }} />

      <Box sx={{ p: 1 }}>
        <SidebarOrganization isExpanded={isExpanded} />
      </Box>

      <Divider sx={{ mx: 1, color: '#f5f5f5' }} />

      <SidebarNav isExpanded={isExpanded} onMenuClick={isMobile ? onMenuClick : undefined} />

      <Divider sx={{ mx: 1, color: '#f5f5f5' }} />

      <Box sx={{ p: 1 }}>
        <ProfileMenu isExpanded={isExpanded} />
      </Box>
    </Box>
  );
}
