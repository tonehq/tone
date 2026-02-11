'use client';

import { AgentType, CreateAgentModalOption } from '@/types/agent';
import {
    ArrowBack as ArrowBackIcon,
    Close as CloseIcon,
    CallReceived as InboundIcon,
    CallMade as OutboundIcon,
} from '@mui/icons-material';
import {
    Box,
    Dialog,
    DialogContent,
    DialogTitle,
    Grid,
    IconButton,
    Paper,
    Typography,
    useTheme,
} from '@mui/material';
import { useRouter } from 'next/navigation';
import React from 'react';

interface CreateAgentModalProps {
  open: boolean;
  onClose: () => void;
}

const agentOptions: CreateAgentModalOption[] = [
  {
    type: 'outbound',
    title: 'Outbound',
    description: 'Automate calls within workflows using Zapier, REST API, or HighLevel',
    icon: <OutboundIcon sx={{ fontSize: 24, color: '#8b5cf6' }} />,
  },
  {
    type: 'inbound',
    title: 'Inbound',
    description: 'Manage incoming calls via phone, Zapier, REST API, or HighLevel',
    icon: <InboundIcon sx={{ fontSize: 24, color: '#8b5cf6' }} />,
  },
  // {
  //   type: 'widget',
  //   title: 'Widget',
  //   description: 'Create a widget and easily embed it anywhere in your app',
  //   icon: <WidgetIcon sx={{ fontSize: 24, color: '#8b5cf6' }} />,
  // },
  // {
  //   type: 'chat',
  //   title: 'Chat',
  //   description: 'Create a chat agent that you can deploy via embeddable widget or integrate with our API',
  //   icon: <ChatIcon sx={{ fontSize: 24, color: '#8b5cf6' }} />,
  // },
];

const CreateAgentModal: React.FC<CreateAgentModalProps> = ({ open, onClose }) => {
  const router = useRouter();
  const theme = useTheme();

  const handleSelectAgent = (type: AgentType) => {
    onClose();
    if (type === 'inbound' || type === 'outbound') {
      router.push(`/agents/create/${type}`);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: '5px',
          maxWidth: 640,
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          pb: 2,
        }}
      >
        <IconButton onClick={onClose} size="small" sx={{ color: theme.palette.text.secondary }}>
          <ArrowBackIcon fontSize="small" />
        </IconButton>
        <Typography variant="h6" component="span" sx={{ flexGrow: 1, fontWeight: 600 }}>
          Choose type of agent
        </Typography>
        <IconButton onClick={onClose} size="small" sx={{ color: theme.palette.text.secondary }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: 3, pb: 3 }}>
        <Grid container spacing={2}>
          {agentOptions.map((option) => (
            <Grid item xs={12} sm={6} key={option.type}>
              <Paper
                onClick={() => handleSelectAgent(option.type)}
                sx={{
                  p: 2.5,
                  mt: 2,
                  border: '1px solid #e2e8f0',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    borderColor: '#8b5cf6',
                    boxShadow: '0 4px 12px rgba(139, 92, 246, 0.15)',
                    transform: 'translateY(-2px)',
                  },
                }}
                elevation={0}
              >
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: '5px',
                      backgroundColor: 'rgba(139, 92, 246, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {option.icon}
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Typography
                      variant="subtitle1"
                      sx={{
                        fontWeight: 600,
                        color: theme.palette.text.primary,
                        mb: 0.5,
                      }}
                    >
                      {option.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        color: theme.palette.text.secondary,
                        lineHeight: 1.5,
                      }}
                    >
                      {option.description}
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </DialogContent>
    </Dialog>
  );
};

export default CreateAgentModal;
