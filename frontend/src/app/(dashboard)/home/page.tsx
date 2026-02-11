'use client';

import { Box, Card, CardContent, Grid, Typography, useTheme } from '@mui/material';
import { BarChart3, Bot, Phone, Settings, Users, Zap } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  const theme = useTheme();

  const quickLinks = [
    {
      title: 'Agents',
      description: 'Create and manage your AI voice agents',
      icon: <Bot size={24} />,
      href: '/agents',
      color: '#8b5cf6',
    },
    {
      title: 'Phone Numbers',
      description: 'Manage your phone numbers for calls',
      icon: <Phone size={24} />,
      href: '/phone-numbers',
      color: '#10b981',
    },
    {
      title: 'Analytics',
      description: 'View performance metrics and insights',
      icon: <BarChart3 size={24} />,
      href: '/analytics',
      color: '#3b82f6',
    },
    {
      title: 'Actions',
      description: 'Configure automated actions and triggers',
      icon: <Zap size={24} />,
      href: '/actions',
      color: '#f59e0b',
    },
    {
      title: 'Team Members',
      description: 'Manage your team and invite new members',
      icon: <Users size={24} />,
      href: '/settings',
      color: '#ec4899',
    },
    {
      title: 'Settings',
      description: 'Configure your organization settings',
      icon: <Settings size={24} />,
      href: '/settings',
      color: '#6b7280',
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Welcome to Synthflow
        </Typography>
        <Typography variant="body1" sx={{ color: theme.palette.text.secondary }}>
          Build and deploy AI voice agents in minutes. Get started with the quick links below.
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {[
          { label: 'Total Agents', value: '6', change: '+2 this week' },
          { label: 'Active Calls', value: '0', change: 'Real-time' },
          { label: 'Minutes Used', value: '0', change: 'This month' },
          { label: 'Success Rate', value: '0%', change: 'Last 30 days' },
        ].map((stat) => (
          <Grid item xs={12} sm={6} md={3} key={stat.label}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary, mb: 1 }}>
                  {stat.label}
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
                  {stat.value}
                </Typography>
                <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                  {stat.change}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Quick Links */}
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
        Quick Links
      </Typography>

      <Grid container spacing={3}>
        {quickLinks.map((link) => (
          <Grid item xs={12} sm={6} md={4} key={link.title}>
            <Card
              component={Link}
              href={link.href}
              sx={{
                height: '100%',
                textDecoration: 'none',
                transition: 'all 0.2s',
                cursor: 'pointer',
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
                    mb: 1.5,
                  }}
                >
                  <Box
                    sx={{
                      width: 48,
                      height: 48,
                      borderRadius: '5px',
                      backgroundColor: `${link.color}15`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: link.color,
                    }}
                  >
                    {link.icon}
                  </Box>
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
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
