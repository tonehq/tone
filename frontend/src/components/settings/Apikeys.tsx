'use client';

import axiosInstance from '@/utils/axios';
import { Box, Tab, Tabs, Typography } from '@mui/material';
import { useEffect, useState } from 'react';
import ApiKeysTab from './ApiKeysTab';
import PublicKeysTab from './PublicKeysTab';

function TabPanel({
  children,
  value,
  index,
}: {
  children: React.ReactNode;
  value: number;
  index: number;
}) {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

export default function Apikeys() {
  const [tabValue, setTabValue] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchApiKeys = async () => {
      setIsLoading(true);
      try {
        const response = await axiosInstance.get('/generated-api-keys/list');
        console.log(response.data, 'response.data');
      } catch (error) {
        console.log(error, 'error');
      } finally {
        setIsLoading(false);
      }
    };
    fetchApiKeys();
  }, []);

  console.log(isLoading, 'isLoading');

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          API Keys
        </Typography>
      </Box>

      <Tabs
        value={tabValue}
        onChange={(_, v: number) => setTabValue(v)}
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          '& .MuiTab-root': { textTransform: 'none', fontWeight: 600 },
          '& .Mui-selected': { color: 'primary.main' },
        }}
      >
        <Tab label="API Keys" />
        <Tab label="Public Keys" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        <ApiKeysTab />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <PublicKeysTab />
      </TabPanel>
    </Box>
  );
}
