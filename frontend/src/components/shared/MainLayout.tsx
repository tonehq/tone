'use client';

import MenuIcon from '@mui/icons-material/Menu';
import { AppBar, Box, IconButton, Toolbar, useMediaQuery, useTheme } from '@mui/material';
import React, { useEffect, useRef, useState } from 'react';
import SidebarComponent from './SidebarComponent';
import { SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED } from '@/constants/sidebar';

interface MainLayoutProps {
  children: React.ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));

  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const hasSetTabletCollapsed = useRef(false);
  useEffect(() => {
    if (isTablet && !hasSetTabletCollapsed.current) {
      hasSetTabletCollapsed.current = true;
      setSidebarExpanded(false);
    }
  }, [isTablet]);

  const sidebarWidth = isMobile
    ? 0
    : sidebarExpanded
      ? SIDEBAR_WIDTH_EXPANDED
      : SIDEBAR_WIDTH_COLLAPSED;

  return (
    <Box sx={{ display: 'flex', width: '100%', minHeight: '100vh' }}>
      <SidebarComponent
        isExpanded={sidebarExpanded}
        onToggle={() => setSidebarExpanded((prev) => !prev)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {isMobile && (
        <AppBar
          position="fixed"
          sx={{
            width: '100%',
            ml: 0,
            backgroundColor: '#f9fafb',
            color: 'text.primary',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            zIndex: 1200,
          }}
        >
          <Toolbar sx={{ minHeight: { xs: 56 } }}>
            <IconButton
              color="inherit"
              aria-label="Open sidebar"
              onClick={() => setMobileOpen(true)}
              edge="start"
              sx={{ mr: 1 }}
            >
              <MenuIcon />
            </IconButton>
            <Box
              sx={{
                width: 32,
                height: 32,
                backgroundColor: 'primary.main',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '1.125rem',
                color: 'primary.contrastText',
              }}
            >
              T
            </Box>
            <Box component="span" sx={{ ml: 1.5, fontWeight: 700, fontSize: '1.125rem' }}>
              Tone
            </Box>
          </Toolbar>
        </AppBar>
      )}

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: isMobile ? '100%' : `calc(100% - ${sidebarWidth}px)`,
          minHeight: '100vh',
          marginLeft: isMobile ? 0 : `${sidebarWidth}px`,
          transition:
            'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1), width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          backgroundColor: 'background.default',
          pt: isMobile ? 7 : 0,
          overflow: 'auto',
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
