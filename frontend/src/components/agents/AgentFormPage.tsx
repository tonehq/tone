'use client';

import { loadableProvidersAtom } from '@/atoms/ProviderAtom';
import { CallConfigurationTab, GeneralTab, VoiceTab } from '@/components/agents/agent-form';
import {
  apiAgentToFormState,
  defaultFormState,
  formStateToUpsertPayload,
  type AgentFormState,
} from '@/components/agents/agent-form/agentFormUtils';
import PromptPage from '@/components/agents/agent-form/promptPage';
import { deleteAgent, getAgent, upsertAgent } from '@/services/agentsService';
import {
  ArrowBack as ArrowBackIcon,
  Phone as PhoneIcon,
  Save as SaveIcon,
  Settings as SettingsIcon,
  VolumeUp as VoiceIcon,
} from '@mui/icons-material';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Snackbar,
  Tab,
  Tabs,
  Typography,
  useTheme,
} from '@mui/material';
import { useAtom } from 'jotai';
import { startCase } from 'lodash';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

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

interface AgentFormPageProps {
  agentType: 'inbound' | 'outbound';
  agentId?: string;
}

export default function AgentFormPage({ agentType, agentId }: AgentFormPageProps) {
  const router = useRouter();
  const theme = useTheme();
  const isEditMode = !!agentId;

  const [providersLoadable] = useAtom(loadableProvidersAtom);
  const [activeTab, setActiveTab] = useState(0);
  const [currentMenu, setCurrentMenu] = useState('configure');
  const [formData, setFormData] = useState<AgentFormState>(() => defaultFormState(agentType));
  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({ open: false, message: '', severity: 'success' });

  const providers = providersLoadable.state === 'hasData' ? providersLoadable.data : [];
  const providersLoading = providersLoadable.state === 'loading';
  const llmProviders = providers.filter((p) => p.provider_type === 'llm');
  const ttsProviders = providers.filter((p) => p.provider_type === 'tts');
  const sttProviders = providers.filter((p) => p.provider_type === 'stt');

  const loadAgentData = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    try {
      const agent = await getAgent(agentId);
      if (agent) {
        setFormData(apiAgentToFormState(agent, agentType));
      } else {
        setSnackbar({ open: true, message: 'Agent not found', severity: 'error' });
      }
    } catch {
      setSnackbar({ open: true, message: 'Failed to load agent', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [agentId, agentType]);

  useEffect(() => {
    if (isEditMode) {
      loadAgentData();
    }
  }, [isEditMode, loadAgentData]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleFormChange = <T extends object>(partial: T) => {
    setFormData((prev) => ({ ...prev, ...partial }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = formStateToUpsertPayload(
        formData,
        agentType,
        isEditMode ? Number(agentId) : undefined,
      );
      await upsertAgent(payload);
      setSnackbar({
        open: true,
        message: isEditMode ? 'Agent saved successfully' : 'Agent created successfully',
        severity: 'success',
      });
      if (!isEditMode) {
        router.push('/agents');
      }
    } catch {
      setSnackbar({
        open: true,
        message: isEditMode
          ? 'Failed to save agent. Please try again.'
          : 'Failed to create agent. Please try again.',
        severity: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAgent = async () => {
    if (
      typeof window !== 'undefined' &&
      window.confirm(
        'Deleting an agent will erase personalized data, voice profiles, and integrations. Are you sure?',
      )
    ) {
      if (isEditMode) {
        try {
          await deleteAgent(Number(agentId));
          router.push('/agents');
        } catch {
          setSnackbar({ open: true, message: 'Failed to delete agent', severity: 'error' });
        }
      } else {
        router.push('/agents');
      }
    }
  };

  const chipColor = agentType === 'inbound' ? '#10b981' : '#8b5cf6';
  const chipBg = agentType === 'inbound' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(139, 92, 246, 0.1)';

  if (loading) {
    return (
      <Box
        sx={{
          p: 3,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <CircularProgress size={40} />
      </Box>
    );
  }

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
                label={agentType === 'inbound' ? 'Inbound' : 'Outbound'}
                size="small"
                sx={{
                  backgroundColor: chipBg,
                  color: chipColor,
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
          {['configure', 'prompt', 'deployments'].map((item) => {
            const isActive = item === currentMenu;
            return (
              <Box
                key={item}
                sx={{
                  py: 1.5,
                  px: 2,
                  cursor: 'pointer',
                  borderRadius: 1,
                  mx: 1,
                  backgroundColor: isActive ? '#e5e7eb' : 'transparent',
                  color: isActive ? '#000' : theme.palette.text.secondary,
                  transition: 'background-color 0.2s, color 0.2s',
                  '&:hover': {
                    backgroundColor: '#e5e7eb',
                    color: '#000',
                  },
                }}
                onClick={() => setCurrentMenu(item)}
              >
                <Typography variant="body2" sx={{ fontWeight: 600, color: 'inherit' }}>
                  {startCase(item)}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ flex: 1 }}>
        <Alert
          severity="info"
          sx={{ borderRadius: 0, backgroundColor: '#f3f4f6', border: 'none' }}
          action={
            !isEditMode ? (
              <Button variant="outlined" size="small" sx={{ borderColor: '#e2e8f0' }}>
                Assign number
              </Button>
            ) : undefined
          }
        >
          {isEditMode ? (
            <>
              <strong>Edit agent</strong> Changes are saved when you click Save.
            </>
          ) : (
            <>
              <strong>Important</strong> Your agent doesn&apos;t have a phone number and can&apos;t{' '}
              {agentType === 'inbound' ? 'receive' : 'make'} calls.
            </>
          )}
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
            startIcon={saving ? <CircularProgress size={18} color="inherit" /> : <SaveIcon />}
            onClick={handleSave}
            disabled={saving}
            sx={{ backgroundColor: '#8b5cf6', '&:hover': { backgroundColor: '#7c3aed' } }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
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
                  llmProviders={llmProviders}
                  providersLoading={providersLoading}
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
                  ttsProviders={ttsProviders}
                  sttProviders={sttProviders}
                  providersLoading={providersLoading}
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
              formData={{ voicePrompting: formData.voicePrompting }}
              onFormChange={handleFormChange}
            />
          </Box>
        )}
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
