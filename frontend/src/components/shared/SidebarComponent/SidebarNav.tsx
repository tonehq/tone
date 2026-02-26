'use client';

import { Box, Typography } from '@mui/material';
import { usePathname } from 'next/navigation';
import { SidebarItemMenu } from './SidebarItemMenu';
import { sidebarSections, type SidebarMenuItem } from './constant';

export interface SidebarNavProps {
  isExpanded: boolean;
  onMenuClick?: () => void;
}

export function SidebarNav({ isExpanded, onMenuClick }: SidebarNavProps) {
  const pathname = usePathname();
  const isActive = (path: string) => pathname === path || pathname?.startsWith(`${path}/`);

  return (
    <Box
      sx={{
        flex: 1,
        overflowY: 'auto',
        py: 2,
        color: 'white',
        px: isExpanded ? 1.5 : 1,
      }}
    >
      {sidebarSections.map((section) => (
        <Box key={section.heading} sx={{ mb: 2 }}>
          {isExpanded && (
            <Typography
              variant="caption"
              sx={{
                px: 0.5,
                color: 'white',
                fontWeight: 600,
                letterSpacing: 1,
              }}
            >
              {section.heading}
            </Typography>
          )}

          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: 0.5,
              mt: 1,
              ...(isExpanded ? {} : { alignItems: 'center' }),
            }}
          >
            {section.items.map((item: SidebarMenuItem) => (
              <SidebarItemMenu
                key={item.key}
                item={item}
                active={isActive(item.path)}
                isCollapsed={!isExpanded}
                onClick={onMenuClick}
              />
            ))}
          </Box>
        </Box>
      ))}
    </Box>
  );
}
