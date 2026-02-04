'use client';

import { CallConfigurationTab, GeneralTab, VoiceTab } from '@/components/agents/agent-form';
import PromptPage from '@/components/agents/agent-form/promptPage';
import {
  ArrowBack as ArrowBackIcon,
  Phone as PhoneIcon,
  Save as SaveIcon,
  Settings as SettingsIcon,
  VolumeUp as VoiceIcon,
} from '@mui/icons-material';
import { Alert, Avatar, Box, Button, Chip, Tab, Tabs, Typography, useTheme } from '@mui/material';
import { startCase } from 'lodash';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export default function CreateInboundAgentPage() {
  const router = useRouter();
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [currentMenu, setCurrentMenu] = useState('configure');
  const [formData, setFormData] = useState({
    name: 'My Inbound Assistant',
    description: 'Description',
    aiModel: 'gpt-4.1',
    end_call_message: 'something end',
    first_message: 'first message something',
    customVocabulary: [] as string[],
    filterWords: [] as string[],
    language: 'en',
    voiceProvider: 'elevenlabs',
    sttProvider: 'deepgram',
    patienceLevel: 'low',
    speechRecognition: 'fast',
    voiceSpeed: 50,
    voiceVolume: 100,
    interruptionSensitivity: 2,
    voicePrompting: 'slowly and at good volume',
    useRealisticFillerWords: false,
    callRecording: false,
    callTranscription: false,
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleFormChange = <T extends object>(partial: T) => {
    setFormData((prev) => ({ ...prev, ...partial }));
  };

  const handleSave = () => {
    console.log('Saving agent:', formData);
    // router.push('/agents');
  };

  const handleDeleteAgent = () => {
    if (
      typeof window !== 'undefined' &&
      window.confirm(
        'Deleting an agent will erase personalized data, voice profiles, and integrations. Are you sure?',
      )
    ) {
      router.push('/agents');
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* Left Sidebar */}
      <Box
        sx={{
          width: 280,
          backgroundColor: '#ffffff',
          borderRight: '1px solid #e2e8f0',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Box sx={{ p: 2 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => router.push('/agents')}
            sx={{ color: theme.palette.text.secondary }}
          >
            Back to Agents
          </Button>
        </Box>

        <Box sx={{ p: 2, borderBottom: '1px solid #e2e8f0' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Avatar sx={{ width: 48, height: 48, backgroundColor: '#f3f4f6' }} />
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {formData.name}
              </Typography>
              <Chip
                label="Inbound"
                size="small"
                sx={{
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  color: '#10b981',
                  fontWeight: 500,
                }}
              />
            </Box>
          </Box>
        </Box>

        <Box sx={{ p: 2 }}>
          <Button
            variant="contained"
            fullWidth
            startIcon={<PhoneIcon />}
            sx={{ backgroundColor: '#8b5cf6', '&:hover': { backgroundColor: '#7c3aed' } }}
          >
            Test Agent
          </Button>
        </Box>

        <Box sx={{ flex: 1, py: 2 }}>
          {['configure', 'prompt', 'deployments'].map((item) => (
            <Box
              key={item}
              sx={{
                py: 1.5,
                px: 2,
                cursor: 'pointer',
                backgroundColor: item === currentMenu ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                color: item === currentMenu ? '#8b5cf6' : theme.palette.text.primary,
                fontWeight: 600,
              }}
              onClick={() => setCurrentMenu(item)}
            >
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {startCase(item)}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ flex: 1 }}>
        <Alert
          severity="info"
          sx={{ borderRadius: 0, backgroundColor: '#f3f4f6', border: 'none' }}
          action={
            <Button variant="outlined" size="small" sx={{ borderColor: '#e2e8f0' }}>
              Assign number
            </Button>
          }
        >
          <strong>Important</strong> Your agent doesn&apos;t have a phone number and can&apos;t
          receive calls.
        </Alert>

        <Box
          sx={{
            p: 3,
            background: '#fff',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {startCase(currentMenu)}
          </Typography>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            sx={{ backgroundColor: '#8b5cf6', '&:hover': { backgroundColor: '#7c3aed' } }}
          >
            Save Changes
          </Button>
        </Box>

        {currentMenu === 'configure' && (
          <Box>
            <Box sx={{ px: 3 }}>
              <Tabs
                value={activeTab}
                onChange={handleTabChange}
                sx={{
                  borderBottom: '1px solid #e2e8f0',
                  '& .MuiTab-root': {
                    marginRight: '16px',
                    minHeight: 48,
                    textTransform: 'none',
                  },
                }}
              >
                <Tab
                  icon={<SettingsIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="General"
                />
                <Tab
                  icon={<VoiceIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="Voice"
                />
                <Tab
                  icon={<PhoneIcon sx={{ fontSize: 18 }} />}
                  iconPosition="start"
                  label="Call Configuration"
                />
              </Tabs>
            </Box>

            <Box sx={{ p: 3, background: 'white', height: '73vh', overflow: 'auto' }}>
              <TabPanel value={activeTab} index={0}>
                <GeneralTab
                  formData={{
                    name: formData.name,
                    description: formData.description,
                    aiModel: formData.aiModel,
                    end_call_message: formData.end_call_message,
                    first_message: formData.first_message,
                    customVocabulary: formData.customVocabulary,
                    filterWords: formData.filterWords,
                    useRealisticFillerWords: formData.useRealisticFillerWords,
                  }}
                  onFormChange={handleFormChange}
                  onDeleteAgent={handleDeleteAgent}
                />
              </TabPanel>

              <TabPanel value={activeTab} index={1}>
                <VoiceTab
                  formData={{
                    language: formData.language,
                    voiceSpeed: formData.voiceSpeed,
                    voiceProvider: formData.voiceProvider,
                    sttProvider: formData.sttProvider,
                    patienceLevel: formData.patienceLevel as 'low' | 'medium' | 'high',
                    speechRecognition: formData.speechRecognition as 'fast' | 'accurate',
                  }}
                  onFormChange={handleFormChange}
                />
              </TabPanel>

              <TabPanel value={activeTab} index={2}>
                <CallConfigurationTab
                  formData={{
                    callRecording: formData.callRecording,
                    callTranscription: formData.callTranscription,
                  }}
                  onFormChange={handleFormChange}
                />
              </TabPanel>
            </Box>
          </Box>
        )}
        {currentMenu === 'prompt' && (
          <Box>
            <PromptPage
              formData={{
                voicePrompting: formData.voicePrompting,
              }}
              onFormChange={handleFormChange}
            />
          </Box>
        )}
      </Box>
    </Box>
  );
}
