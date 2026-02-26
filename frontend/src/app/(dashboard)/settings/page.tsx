'use client';

import Apikeys from '@/components/settings/Apikeys';
import Integrations from '@/components/settings/Integrations';
import {
  Avatar,
  Box,
  Button,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Paper,
  Switch,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import { Search, Trash2, UserPlus } from 'lucide-react';
import { useState } from 'react';

export default function SettingsPage() {
  const theme = useTheme();
  const [allowAccessRequests, setAllowAccessRequests] = useState(true);
  const [autoVerifySameDomain, setAutoVerifySameDomain] = useState(false);
  const [activeSidebar] = useState('Integrations');

  const members = [
    { id: 1, name: 'Karthik', email: 'karthik@productfusion.co', role: 'Owner', avatar: 'K' },
  ];

  return (
    <Box sx={{ py: 1.5, px: 2 }}>
      {/* <SidebarComponent
          activeSidebar={activeSidebar}
          setActiveSidebar={setActiveSidebar}
          settingsSidebar={settingsSidebar}
        /> */}

      <Box sx={{ flex: 1, borderRadius: '5px', height: 'calc(100vh - 24px)' }}>
        <Paper sx={{ height: '100%', borderRadius: '5px', overflow: 'hidden' }}>
          {activeSidebar === 'Members' && (
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
                      borderRadius: '5px',
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
                          borderRadius: '5px',
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
          )}

          {activeSidebar === 'Organization' && (
            <Box sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                Access Settings
              </Typography>

              <Box
                sx={{
                  backgroundColor: '#f9fafb',
                  borderRadius: '5px',
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
                            Automatically approve access requests from users with the same email
                            domain
                          </Typography>
                        </Box>
                      }
                      sx={{ alignItems: 'flex-start', ml: 0 }}
                    />
                  </Box>
                )}
              </Box>
            </Box>
          )}

          {activeSidebar === 'API Key' && <Apikeys />}

          {activeSidebar === 'Integrations' && <Integrations />}
        </Paper>
      </Box>
    </Box>
  );
}
