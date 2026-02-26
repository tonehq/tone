'use client';

import { Add } from '@mui/icons-material';
import { Box, Button, Paper, Typography } from '@mui/material';

export default function PhoneNumbersPage() {
  return (
    <Box sx={{ flex: 1, p: 2, borderRadius: '5px', height: 'calc(100vh - 16px)' }}>
      <Paper sx={{ height: '100%', borderRadius: '5px', overflow: 'hidden', p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            Phone Numbers
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            sx={{ bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } }}
          >
            Link a Phone Number to An Agent
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
