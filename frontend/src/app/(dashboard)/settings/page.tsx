'use client';

import { useState } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Avatar,
  Divider,
  useTheme,
  InputAdornment,
  IconButton,
} from '@mui/material';
import { Home, Search, UserPlus, Trash2 } from 'lucide-react';
import Link from 'next/link';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export default function SettingsPage() {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [allowAccessRequests, setAllowAccessRequests] = useState(true);
  const [autoVerifySameDomain, setAutoVerifySameDomain] = useState(false);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const members = [
    { id: 1, name: 'Karthik', email: 'karthik@productfusion.co', role: 'Owner', avatar: 'K' },
  ];

  return (
    <Box sx={{ p: 3 }}>
      {/* Breadcrumb */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <Link href="/home" style={{ color: theme.palette.text.secondary }}>
          <Home size={14} />
        </Link>
        <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
          /
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          Settings
        </Typography>
      </Box>

      {/* Header */}
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 3 }}>
        Settings
      </Typography>

      {/* Main Content */}
      <Paper sx={{ borderRadius: '12px', overflow: 'hidden' }}>
        {/* Tabs */}
        <Box sx={{ borderBottom: '1px solid', borderColor: 'divider', px: 3 }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab label="Members" />
            <Tab label="Organization" />
          </Tabs>
        </Box>

        {/* Members Tab */}
        <TabPanel value={activeTab} index={0}>
          <Box sx={{ p: 3 }}>
            {/* Search and Invite */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
              <TextField
                placeholder="Search members..."
                size="small"
                sx={{ width: 300 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search size={18} color={theme.palette.text.secondary} />
                    </InputAdornment>
                  ),
                }}
              />
              <Button
                variant="contained"
                startIcon={<UserPlus size={18} />}
                sx={{
                  backgroundColor: theme.palette.primary.main,
                  '&:hover': { backgroundColor: theme.palette.primary.dark },
                }}
              >
                Invite user
              </Button>
            </Box>

            {/* Members List */}
            <Box>
              {members.map((member) => (
                <Box
                  key={member.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 2,
                    borderRadius: '8px',
                    '&:hover': { backgroundColor: '#f9fafb' },
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Avatar
                      sx={{
                        width: 40,
                        height: 40,
                        backgroundColor: '#f59e0b',
                        fontWeight: 600,
                      }}
                    >
                      {member.avatar}
                    </Avatar>
                    <Box>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        {member.name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                        {member.email}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        px: 2,
                        py: 0.5,
                        borderRadius: '16px',
                        backgroundColor: '#f3f4f6',
                        fontWeight: 500,
                      }}
                    >
                      {member.role}
                    </Typography>
                    <IconButton size="small" disabled>
                      <Trash2 size={18} />
                    </IconButton>
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        </TabPanel>

        {/* Organization Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Access Settings
            </Typography>

            <Box
              sx={{
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                border: '1px solid',
                borderColor: 'divider',
                p: 3,
              }}
            >
              <Box sx={{ mb: 3 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={allowAccessRequests}
                      onChange={(e) => setAllowAccessRequests(e.target.checked)}
                      color="primary"
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        Allow users to request access
                      </Typography>
                      <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                        When enabled, users can request to join your organization during signup
                      </Typography>
                    </Box>
                  }
                  sx={{ alignItems: 'flex-start', ml: 0 }}
                />
              </Box>

              {allowAccessRequests && (
                <Box sx={{ ml: 4, borderLeft: '2px solid', borderColor: 'divider', pl: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={autoVerifySameDomain}
                        onChange={(e) => setAutoVerifySameDomain(e.target.checked)}
                        color="primary"
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>
                          Auto-approve users with same email domain
                        </Typography>
                        <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                          Automatically approve access requests from users with the same email domain
                        </Typography>
                      </Box>
                    }
                    sx={{ alignItems: 'flex-start', ml: 0 }}
                  />
                </Box>
              )}
            </Box>
          </Box>
        </TabPanel>
      </Paper>
    </Box>
  );
}
