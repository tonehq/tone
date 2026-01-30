'use client';

import { Box, Card, CardContent, Typography, useTheme } from '@mui/material';
import { Settings, Users } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  const theme = useTheme();

  const quickLinks = [
    {
      title: 'Team Members',
      description: 'Manage your team and invite new members',
      icon: <Users size={24} />,
      href: '/settings',
    },
    {
      title: 'Settings',
      description: 'Configure your organization settings',
      icon: <Settings size={24} />,
      href: '/settings',
    },
  ];

  return (
    <Box>
      <Box sx={{ p: 3 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
            Welcome to Tone
          </Typography>
          <Typography variant="body1" sx={{ color: theme.palette.text.secondary }}>
            Manage your organization efficiently with powerful tools for team collaboration.
          </Typography>
        </Box>

        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
          Quick Links
        </Typography>

        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          {quickLinks.map((link) => (
            <Card
              key={link.title}
              component={Link}
              href={link.href}
              sx={{
                width: 280,
                textDecoration: 'none',
                transition: 'all 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: theme.shadows[4],
                },
              }}
            >
              <CardContent>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    mb: 1,
                    color: theme.palette.primary.main,
                  }}
                >
                  {link.icon}
                  <Typography
                    variant="h6"
                    sx={{ fontWeight: 600, color: theme.palette.text.primary }}
                  >
                    {link.title}
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                  {link.description}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>
    </Box>
  );
}
