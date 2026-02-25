'use client';

import { Box, IconButton, Typography } from '@mui/material';
import { PanelLeft, PanelRight } from 'lucide-react';

export interface SidebarHeaderProps {
  isExpanded: boolean;
  onToggle: () => void;
  isMobile?: boolean;
}

export function SidebarHeader({ isExpanded, onToggle, isMobile = false }: SidebarHeaderProps) {
  return (
    <Box
      sx={{
        p: 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: isExpanded ? 'space-between' : 'center',
        minHeight: 56,
      }}
    >
      {isExpanded && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              bgcolor: 'primary.main',
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              color: 'white',
            }}
          >
            T
          </Box>
          <Typography fontWeight={700}>Tone</Typography>
        </Box>
      )}

      {!isMobile && (
        <IconButton size="small" onClick={onToggle}>
          {!isExpanded ? (
            <PanelRight color="white" size={20} />
          ) : (
            <PanelLeft color="white" size={20} />
          )}
        </IconButton>
      )}
    </Box>
  );
}
