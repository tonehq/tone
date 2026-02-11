'use client';

import { Add as AddIcon, Phone as PhoneIcon } from '@mui/icons-material';
import {
    Box,
    Button,
    List,
    ListItem,
    ListItemButton,
    ListItemText,
    Paper,
    Typography,
    useTheme,
} from '@mui/material';

export default function PhoneNumbersPage() {
  const theme = useTheme();

  return (
    <Box sx={{ display: 'flex', height: '100%' }}>
      {/* Left Sidebar */}
      <Box
        sx={{
          width: 240,
          backgroundColor: '#ffffff',
          borderRight: '1px solid #e2e8f0',
          p: 2,
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 3 }}>
          Phone Numbers
        </Typography>

        <List disablePadding>
          <ListItem disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              selected
              sx={{
                borderRadius: '5px',
                '&.Mui-selected': {
                  backgroundColor: 'rgba(139, 92, 246, 0.1)',
                  '&:hover': {
                    backgroundColor: 'rgba(139, 92, 246, 0.15)',
                  },
                },
              }}
            >
              <ListItemText
                primary="Active Numbers"
                primaryTypographyProps={{
                  fontWeight: 600,
                  color: '#8b5cf6',
                }}
              />
            </ListItemButton>
          </ListItem>
          <ListItem disablePadding>
            <ListItemButton sx={{ borderRadius: '5px' }}>
              <ListItemText
                primary="Addresses"
                primaryTypographyProps={{
                  color: theme.palette.text.primary,
                }}
              />
            </ListItemButton>
          </ListItem>
        </List>
      </Box>

      {/* Main Content */}
      <Box
        sx={{
          flex: 1,
          p: 4,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Paper
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '5px',
            border: '1px solid #e2e8f0',
            p: 4,
          }}
          elevation={0}
        >
          {/* Empty State */}
          <Box
            sx={{
              width: 80,
              height: 80,
              backgroundColor: '#f3f4f6',
              borderRadius: '5px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 3,
            }}
          >
            <PhoneIcon sx={{ fontSize: 40, color: '#9ca3af' }} />
          </Box>

          <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
            Phone Numbers
          </Typography>

          <Typography
            variant="body1"
            sx={{ color: theme.palette.text.secondary, textAlign: 'center', mb: 3 }}
          >
            Welcome to your phone numbers management page. Your numbers will appear here.
          </Typography>

          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            sx={{
              borderColor: '#e2e8f0',
              color: '#8b5cf6',
              '&:hover': {
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.05)',
              },
            }}
          >
            New Phone Number
          </Button>
        </Paper>
      </Box>
    </Box>
  );
}
