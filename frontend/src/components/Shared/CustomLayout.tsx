import React, { ReactNode } from 'react';

import { Box } from '@mui/material';

interface CustomLayoutProps {
  sidebarContent: ReactNode;
  children: ReactNode;
  siderWidth?: number | string;
  layoutStyle?: React.CSSProperties;
  siderStyle?: React.CSSProperties;
}

const CustomLayout: React.FC<CustomLayoutProps> = ({
  sidebarContent,
  children,
  siderWidth = 200,
  layoutStyle,
  siderStyle,
}) => (
  <Box
    sx={{
      width: '100%',
      height: '100%',
      padding: 2,
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'row',
      gap: 2,
      ...layoutStyle,
    }}
  >
    <Box
      sx={{
        width: siderWidth,
        borderRadius: 2,
        padding: 2,
        color: 'white',
        height: '100%',
        backgroundColor: '#3f3f46',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        ...siderStyle,
      }}
    >
      {sidebarContent}
    </Box>
    <Box
      sx={{
        flex: 1,
        height: '100%',
        overflow: 'auto',
        boxSizing: 'border-box',
      }}
    >
      {children}
    </Box>
  </Box>
);

export default CustomLayout;
