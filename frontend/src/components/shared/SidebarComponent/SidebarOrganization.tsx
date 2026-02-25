'use client';

import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import { Avatar, Box, Tooltip, Typography } from '@mui/material';
import { SIDEBAR_HOVER_ACTIVE } from './constant';

const WORKSPACE_LABEL = 'My Workspace';

export interface SidebarOrganizationProps {
  isExpanded: boolean;
}

export function SidebarOrganization({ isExpanded }: SidebarOrganizationProps) {
  if (isExpanded) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          p: 1,
          borderRadius: '5px',
          cursor: 'pointer',
          '&:hover': { backgroundColor: SIDEBAR_HOVER_ACTIVE },
        }}
      >
        <Avatar sx={{ width: 36, height: 36 }}>M</Avatar>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {WORKSPACE_LABEL}
        </Typography>
        <KeyboardArrowDownIcon fontSize="small" />
      </Box>
    );
  }

  return (
    <Tooltip title={WORKSPACE_LABEL} placement="right" arrow>
      <Avatar
        sx={{
          width: 32,
          height: 32,
          mx: 'auto',
          cursor: 'pointer',
        }}
      >
        M
      </Avatar>
    </Tooltip>
  );
}
