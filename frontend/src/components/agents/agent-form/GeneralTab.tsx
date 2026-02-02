'use client';

import { Form } from '@/components/Shared/FormComponent';
import { aiModels } from '@/data/mockAgents';
import {
  Box,
  Button,
  Chip,
  FormControl,
  MenuItem,
  Select,
  Switch,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import { KeyboardEvent, ReactNode, useState } from 'react';
import type { AgentGeneralFormData } from './types';

interface GeneralTabProps {
  formData: AgentGeneralFormData;
  onFormChange: (partial: Partial<AgentGeneralFormData>) => void;
  onDeleteAgent: () => void;
  onFormSubmit?: (values: AgentGeneralFormData) => void;
}

/* ------------------------------------------------------------------ */
/* Reusable 60% / 40% Form Row */
/* ------------------------------------------------------------------ */
function FormRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        mb: 4,
      }}
    >
      {/* Left - 60% */}
      <Box sx={{ flex: '0 0 60%' }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {label}
        </Typography>
        {description && (
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        )}
      </Box>

      {/* Right - 40% */}
      <Box sx={{ flex: '0 0 40%' }}>{children}</Box>
    </Box>
  );
}

export default function GeneralTab({
  formData,
  onFormChange,
  onDeleteAgent,
  onFormSubmit,
}: GeneralTabProps) {
  const theme = useTheme();
  const [vocabularyInput, setVocabularyInput] = useState('');
  const [filterWordsInput, setFilterWordsInput] = useState('');

  const handleFinish = (values: Record<string, string>) => {
    const customVocabulary = parseJsonArray(values.customVocabulary);
    const filterWords = parseJsonArray(values.filterWords);
    const useRealisticFillerWords = values.useRealisticFillerWords === 'true';

    const next: Partial<AgentGeneralFormData> = {
      name: values.name ?? formData.name,
      aiModel: values.aiModel ?? formData.aiModel,
      customVocabulary: customVocabulary ?? formData.customVocabulary,
      filterWords: filterWords ?? formData.filterWords,
      useRealisticFillerWords:
        useRealisticFillerWords ?? formData.useRealisticFillerWords,
    };

    onFormChange(next);
    onFormSubmit?.({ ...formData, ...next });
  };

  function parseJsonArray(str?: string): string[] | undefined {
    if (!str) return undefined;
    try {
      const parsed = JSON.parse(str);
      return Array.isArray(parsed) ? parsed : undefined;
    } catch {
      return undefined;
    }
  }

  const addVocabulary = () => {
    const trimmed = vocabularyInput.trim();
    if (trimmed && !formData.customVocabulary.includes(trimmed)) {
      onFormChange({
        customVocabulary: [...formData.customVocabulary, trimmed],
      });
      setVocabularyInput('');
    }
  };

  const addFilterWord = () => {
    const trimmed = filterWordsInput.trim();
    if (trimmed && !formData.filterWords.includes(trimmed)) {
      onFormChange({
        filterWords: [...formData.filterWords, trimmed],
      });
      setFilterWordsInput('');
    }
  };

  return (
    <Form onFinish={handleFinish} layout="vertical" autoComplete="off">
      {/* Hidden inputs for submit */}
      <input
        type="hidden"
        name="customVocabulary"
        value={JSON.stringify(formData.customVocabulary)}
        readOnly
      />
      <input
        type="hidden"
        name="filterWords"
        value={JSON.stringify(formData.filterWords)}
        readOnly
      />
      <input
        type="hidden"
        name="useRealisticFillerWords"
        value={String(formData.useRealisticFillerWords)}
        readOnly
      />

      <FormRow
        label="Agent Name"
        description="What name will your agent go by."
      >
        <TextField
          value={formData.name}
          onChange={(e) => onFormChange({ name: e.target.value })}
          size="small"
          fullWidth
        />
      </FormRow>

      <FormRow
        label="Agent Description"
        description="Provide a brief summary explaining your agent’s purpose."
      >
        <TextField
          value={formData.description}
          onChange={(e) => onFormChange({ description: e.target.value })}
          size="small"
          multiline
          minRows={3}
          fullWidth
        />
      </FormRow>

      <FormRow
        label="AI Model"
        description="Opt for speed or depth to suit your agent's role."
      >
        <FormControl size="small" fullWidth>
          <Select
            value={formData.aiModel}
            onChange={(e) => onFormChange({ aiModel: e.target.value })}
            renderValue={(v) =>
              aiModels.find((m) => m.value === v)?.label ?? v
            }
          >
            {aiModels.map((model) => (
              <MenuItem key={model.value} value={model.value}>
                {model.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </FormRow>

      <FormRow
        label="First Message"
        description="Initial message sent when the conversation starts."
      >
        <TextField
          value={formData.first_message}
          onChange={(e) => onFormChange({ first_message: e.target.value })}
          size="small"
          multiline
          minRows={3}
          fullWidth
        />
      </FormRow>

      <FormRow
        label="End Call Message"
        description="Message sent at the end of a conversation."
      >
        <TextField
          value={formData.end_call_message}
          onChange={(e) => onFormChange({ end_call_message: e.target.value })}
          size="small"
          multiline
          minRows={3}
          fullWidth
        />
      </FormRow>

      <FormRow
        label="Custom Vocabulary"
        description="Add business terms to improve accuracy."
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              value={vocabularyInput}
              onChange={(e) => setVocabularyInput(e.target.value)}
              onKeyDown={(e: KeyboardEvent<HTMLInputElement>) =>
                e.key === 'Enter' && (e.preventDefault(), addVocabulary())
              }
              size="small"
              fullWidth
            />
            <Button variant="outlined" onClick={addVocabulary}>
              Enter
            </Button>
          </Box>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {formData.customVocabulary.map((word) => (
              <Chip
                key={word}
                label={word}
                size="small"
                onDelete={() =>
                  onFormChange({
                    customVocabulary: formData.customVocabulary.filter(
                      (w) => w !== word
                    ),
                  })
                }
              />
            ))}
          </Box>
        </Box>
      </FormRow>

      <FormRow
        label="Filter Words"
        description="Words the agent should not speak."
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              value={filterWordsInput}
              onChange={(e) => setFilterWordsInput(e.target.value)}
              onKeyDown={(e: KeyboardEvent<HTMLInputElement>) =>
                e.key === 'Enter' && (e.preventDefault(), addFilterWord())
              }
              size="small"
              fullWidth
            />
            <Button variant="outlined" onClick={addFilterWord}>
              Enter
            </Button>
          </Box>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {formData.filterWords.map((word) => (
              <Chip
                key={word}
                label={word}
                size="small"
                onDelete={() =>
                  onFormChange({
                    filterWords: formData.filterWords.filter(
                      (w) => w !== word
                    ),
                  })
                }
              />
            ))}
          </Box>
        </Box>
      </FormRow>

      <FormRow
        label="Use Realistic Filler Words"
        description="Include natural filler words like ‘uh’ and ‘um’."
      >
        <Switch
          checked={formData.useRealisticFillerWords}
          onChange={(e) =>
            onFormChange({ useRealisticFillerWords: e.target.checked })
          }
        />
      </FormRow>

      <FormRow
        label="Delete Agent"
        description="Deleting an agent removes all associated data."
      >
        <Button variant="contained" color="error" onClick={onDeleteAgent}>
          Delete Agent
        </Button>
      </FormRow>
    </Form>
  );
}
