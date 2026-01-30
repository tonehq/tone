import { useEffect, useState } from 'react';

import { Box, FormControlLabel, Switch, Typography, useTheme } from '@mui/material';

import axios from '@/utils/axios';
import { showToast } from '@/utils/showToast';

interface OrgSettings {
  allow_access_requests: boolean;
  auto_verify_same_domain: boolean;
}

const OrganizationSettingsTab = () => {
  const theme = useTheme();
  const [settings, setSettings] = useState<OrgSettings>({
    allow_access_requests: false,
    auto_verify_same_domain: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await axios.get('/api/v1/organization/settings');
      setSettings({
        allow_access_requests: res.data?.allow_access_requests || false,
        auto_verify_same_domain: res.data?.auto_verify_same_domain || false,
      });
    } catch {
      setSettings({
        allow_access_requests: false,
        auto_verify_same_domain: false,
      });
    } finally {
      setLoading(false);
    }
  };

  const updateSettings = async (newSettings: Partial<OrgSettings>) => {
    try {
      await axios.put('/api/v1/organization/settings', newSettings);
      setSettings((prev) => ({ ...prev, ...newSettings }));
      showToast({
        status: 'success',
        message: 'Settings updated successfully',
        variant: 'message',
      });
    } catch {
      showToast({
        status: 'error',
        message: 'Failed to update settings',
        variant: 'message',
      });
    }
  };

  const handleAllowAccessRequestsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.checked;
    updateSettings({
      allow_access_requests: newValue,
      auto_verify_same_domain: newValue ? settings.auto_verify_same_domain : false,
    });
  };

  const handleAutoVerifyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateSettings({ auto_verify_same_domain: e.target.checked });
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Loading settings...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
        Access Settings
      </Typography>

      <Box
        sx={{
          backgroundColor: theme.palette.background.paper,
          borderRadius: 2,
          border: `1px solid ${theme.palette.divider}`,
          p: 3,
        }}
      >
        <Box sx={{ mb: 3 }}>
          <FormControlLabel
            control={
              <Switch
                checked={settings.allow_access_requests}
                onChange={handleAllowAccessRequestsChange}
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

        {settings.allow_access_requests && (
          <Box sx={{ ml: 4, borderLeft: `2px solid ${theme.palette.divider}`, pl: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.auto_verify_same_domain}
                  onChange={handleAutoVerifyChange}
                  color="primary"
                />
              }
              label={
                <Box>
                  <Typography variant="body1" sx={{ fontWeight: 500 }}>
                    Auto-approve users with same email domain
                  </Typography>
                  <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                    Automatically approve access requests from users with the same email domain as
                    the organization owner
                  </Typography>
                </Box>
              }
              sx={{ alignItems: 'flex-start', ml: 0 }}
            />
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default OrganizationSettingsTab;
