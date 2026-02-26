'use client';

import { languages } from '@/data/mockAgents';
import type { ServiceProvider } from '@/services/providerService';
import {
  Box,
  CircularProgress,
  FormControl,
  FormControlLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Slider,
  Typography,
} from '@mui/material';
import type { AgentVoiceFormData } from './types';

interface VoiceTabProps {
  formData: AgentVoiceFormData;
  ttsProviders: ServiceProvider[];
  sttProviders: ServiceProvider[];
  providersLoading?: boolean;
  onFormChange: (partial: Partial<AgentVoiceFormData>) => void;
}

export default function VoiceTab({
  formData,
  ttsProviders,
  sttProviders,
  providersLoading,
  onFormChange,
}: VoiceTabProps) {
  const Row = ({ left, right }: { left: React.ReactNode; right: React.ReactNode }) => (
    <Box sx={{ display: 'flex', mb: 4 }}>
      <Box sx={{ width: '60%' }}>{left}</Box>
      <Box sx={{ width: '40%', display: 'flex', justifyContent: 'flex-start' }}>{right}</Box>
    </Box>
  );

  const ProviderSelect = ({
    value,
    providers,
    onChange,
  }: {
    value: number | null;
    providers: ServiceProvider[];
    onChange: (id: number | null) => void;
  }) => {
    if (providersLoading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 1 }}>
          <CircularProgress size={24} />
        </Box>
      );
    }
    return (
      <FormControl size="small" fullWidth>
        <Select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          displayEmpty
          renderValue={(v) => {
            if (!v) return <em>Select a provider</em>;
            return providers.find((p) => p.id === v)?.display_name ?? v;
          }}
        >
          {providers.map((p) => (
            <MenuItem key={p.id} value={p.id}>
              {p.display_name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  };

  return (
    <Box sx={{ py: 2 }}>
      {/* Language */}
      <Row
        left={
          <>
            <Typography variant="subtitle1" fontWeight={600}>
              Language
            </Typography>
            <Typography variant="body2" color="text.secondary">
              The language your agent understands.
            </Typography>
          </>
        }
        right={
          <FormControl size="small" fullWidth>
            <Select
              value={formData.language}
              onChange={(e) => onFormChange({ language: e.target.value })}
            >
              {languages.map((lang) => (
                <MenuItem key={lang.value} value={lang.value}>
                  {lang.flag} {lang.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        }
      />

      {/* Voice Provider (TTS) */}
      <Row
        left={
          <>
            <Typography variant="subtitle1" fontWeight={600}>
              Voice Provider
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Select the service used to generate your agent&apos;s voice.
            </Typography>
          </>
        }
        right={
          <ProviderSelect
            value={formData.voiceProvider}
            providers={ttsProviders}
            onChange={(id) => onFormChange({ voiceProvider: id })}
          />
        }
      />

      {/* STT Provider */}
      <Row
        left={
          <>
            <Typography variant="subtitle1" fontWeight={600}>
              STT Provider
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Select the service used to transcribe calls to text (Speech-to-Text).
            </Typography>
          </>
        }
        right={
          <ProviderSelect
            value={formData.sttProvider}
            providers={sttProviders}
            onChange={(id) => onFormChange({ sttProvider: id })}
          />
        }
      />

      {/* Voice Speed */}
      <Row
        left={
          <>
            <Typography variant="subtitle1" fontWeight={600}>
              Voice Speed
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Adjust how fast or slow your agent will talk.
            </Typography>
          </>
        }
        right={
          <Box sx={{ width: '100%' }}>
            <Slider
              value={formData.voiceSpeed}
              onChange={(_, value) => onFormChange({ voiceSpeed: value as number })}
              min={0}
              max={100}
              marks={[
                { value: 0, label: 'Slow' },
                { value: 50, label: 'Normal' },
                { value: 100, label: 'Fast' },
              ]}
              sx={{ color: '#8b5cf6' }}
            />
          </Box>
        }
      />

      {/* Patience Level */}
      <Row
        left={
          <>
            <Typography variant="subtitle1" fontWeight={600}>
              Patience Level
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Adjust the response speed. Low for rapid exchanges, high for more focused turns.
            </Typography>
          </>
        }
        right={
          <RadioGroup
            row
            value={formData.patienceLevel}
            onChange={(e) =>
              onFormChange({ patienceLevel: e.target.value as 'low' | 'medium' | 'high' })
            }
            sx={{ gap: 2 }}
          >
            {[
              { value: 'low', label: 'Low', desc: '~1 sec' },
              { value: 'medium', label: 'Medium', desc: '~3 sec' },
              { value: 'high', label: 'High', desc: '~5 sec' },
            ].map((item) => (
              <FormControlLabel
                key={item.value}
                value={item.value}
                control={<Radio sx={{ display: 'none' }} />}
                label={
                  <Box
                    sx={{
                      width: 105,
                      p: 2,
                      borderRadius: '5px',
                      border: '1px solid',
                      cursor: 'pointer',
                      borderColor: formData.patienceLevel === item.value ? '#a78bfa' : 'divider',
                      backgroundColor:
                        formData.patienceLevel === item.value
                          ? 'rgba(167, 139, 250, 0.12)'
                          : 'transparent',
                    }}
                  >
                    <Typography fontWeight={600}>{item.label}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.desc}
                    </Typography>
                  </Box>
                }
              />
            ))}
          </RadioGroup>
        }
      />

      {/* Speech Recognition */}
      <Row
        left={
          <>
            <Typography variant="subtitle1" fontWeight={600}>
              Speech Recognition
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Adjusts how quickly incoming speech is transcribed.
            </Typography>
          </>
        }
        right={
          <RadioGroup
            row
            value={formData.speechRecognition}
            onChange={(e) =>
              onFormChange({ speechRecognition: e.target.value as 'fast' | 'accurate' })
            }
            sx={{ gap: 2 }}
          >
            {[
              {
                value: 'fast',
                label: 'Faster',
                desc: 'Lower quality, suitable for most use cases',
              },
              {
                value: 'accurate',
                label: 'High Accuracy',
                desc: 'Slower, for high accuracy use cases',
              },
            ].map((item) => (
              <FormControlLabel
                key={item.value}
                value={item.value}
                control={<Radio sx={{ display: 'none' }} />}
                label={
                  <Box
                    sx={{
                      width: 170,
                      p: 1.5,
                      borderRadius: '5px',
                      border: '1px solid',
                      cursor: 'pointer',
                      borderColor:
                        formData.speechRecognition === item.value ? '#a78bfa' : 'divider',
                      backgroundColor:
                        formData.speechRecognition === item.value
                          ? 'rgba(167, 139, 250, 0.12)'
                          : 'transparent',
                    }}
                  >
                    <Typography fontWeight={600}>{item.label}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.desc}
                    </Typography>
                  </Box>
                }
              />
            ))}
          </RadioGroup>
        }
      />
    </Box>
  );
}
