'use client';

import { Box, Switch, Typography, useTheme } from '@mui/material';
import type { AgentCallConfigFormData } from './types';

interface CallConfigurationTabProps {
  formData: AgentCallConfigFormData;
  onFormChange: (partial: Partial<AgentCallConfigFormData>) => void;
}

const switchSx = {
  '& .MuiSwitch-switchBase.Mui-checked': { color: '#8b5cf6' },
  '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { backgroundColor: '#8b5cf6' },
};

export default function CallConfigurationTab({ formData, onFormChange }: CallConfigurationTabProps) {
  const theme = useTheme();

  return (
    <Box sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Call Recording
          </Typography>
          <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
            Enable recording of all calls for review.
          </Typography>
        </Box>
        <Switch
          checked={formData.callRecording}
          onChange={(e) => onFormChange({ callRecording: e.target.checked })}
          sx={switchSx}
        />
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Call Transcription
          </Typography>
          <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
            Automatically transcribe all calls to text.
          </Typography>
        </Box>
        <Switch
          checked={formData.callTranscription}
          onChange={(e) => onFormChange({ callTranscription: e.target.checked })}
          sx={switchSx}
        />
      </Box>
    </Box>
  );
}
