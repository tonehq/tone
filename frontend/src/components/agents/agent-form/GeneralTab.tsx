'use client';

import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { CustomButton, SelectInput, TextAreaField, TextInput } from '@/components/shared';
import { Form } from '@/components/shared/Form';
import type { ServiceProvider } from '@/types/provider';
import { X } from 'lucide-react';
import { KeyboardEvent, ReactNode, useState } from 'react';
import type { AgentGeneralFormData } from './types';

interface GeneralTabProps {
  formData: AgentGeneralFormData;
  llmProviders: ServiceProvider[];
  providersLoading?: boolean;
  onFormChange: (partial: Partial<AgentGeneralFormData>) => void;
  onDeleteAgent: () => void;
  onFormSubmit?: (values: AgentGeneralFormData) => void;
}

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
    <div className="mb-6 flex items-start justify-between gap-6">
      <div className="flex-[0_0_55%]">
        <h3 className="text-sm font-semibold text-foreground">{label}</h3>
        {description && (
          <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex-[0_0_40%]">{children}</div>
    </div>
  );
}

function parseJsonArray(str?: string): string[] | undefined {
  if (!str) return undefined;
  try {
    const parsed = JSON.parse(str);
    return Array.isArray(parsed) ? parsed : undefined;
  } catch {
    return undefined;
  }
}

export default function GeneralTab({
  formData,
  llmProviders,
  providersLoading,
  onFormChange,
  onDeleteAgent,
  onFormSubmit,
}: GeneralTabProps) {
  const [vocabularyInput, setVocabularyInput] = useState('');
  const [filterWordsInput, setFilterWordsInput] = useState('');

  const handleFinish = (values: Record<string, string>) => {
    const customVocabulary = parseJsonArray(values.customVocabulary);
    const filterWords = parseJsonArray(values.filterWords);
    const useRealisticFillerWords = values.useRealisticFillerWords === 'true';

    const next: Partial<AgentGeneralFormData> = {
      name: values.name ?? formData.name,
      aiModel: values.aiModel ? Number(values.aiModel) : formData.aiModel,
      customVocabulary: customVocabulary ?? formData.customVocabulary,
      filterWords: filterWords ?? formData.filterWords,
      useRealisticFillerWords: useRealisticFillerWords ?? formData.useRealisticFillerWords,
    };

    onFormChange(next);
    onFormSubmit?.({ ...formData, ...next });
  };

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

      <FormRow label="Agent Name" description="What name will your agent go by.">
        <TextInput
          name="name"
          value={formData.name}
          onChange={(e) => onFormChange({ name: e.target.value })}
        />
      </FormRow>

      <FormRow
        label="Agent Description"
        description="Provide a brief summary explaining your agent's purpose."
      >
        <TextAreaField
          name="description"
          value={formData.description}
          onChange={(e) => onFormChange({ description: e.target.value })}
          rows={3}
        />
      </FormRow>

      <FormRow label="AI Model" description="Opt for speed or depth to suit your agent's role.">
        <SelectInput
          name="aiModel"
          value={formData.aiModel != null ? String(formData.aiModel) : ''}
          onValueChange={(v) => onFormChange({ aiModel: v ? Number(v) : null })}
          placeholder="Select a provider"
          options={llmProviders.map((p) => ({ value: String(p.id), label: p.display_name }))}
          loading={providersLoading}
        />
      </FormRow>

      <FormRow
        label="First Message"
        description="Initial message sent when the conversation starts."
      >
        <TextAreaField
          name="first_message"
          value={formData.first_message}
          onChange={(e) => onFormChange({ first_message: e.target.value })}
          rows={3}
        />
      </FormRow>

      <FormRow label="End Call Message" description="Message sent at the end of a conversation.">
        <TextAreaField
          name="end_call_message"
          value={formData.end_call_message}
          onChange={(e) => onFormChange({ end_call_message: e.target.value })}
          rows={3}
        />
      </FormRow>

      <FormRow label="Custom Vocabulary" description="Add business terms to improve accuracy.">
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <TextInput
              name="vocabularyInput"
              value={vocabularyInput}
              onChange={(e) => setVocabularyInput(e.target.value)}
              onKeyDown={(e: KeyboardEvent<HTMLInputElement>) =>
                e.key === 'Enter' && (e.preventDefault(), addVocabulary())
              }
            />
            <CustomButton type="default" onClick={addVocabulary}>
              Enter
            </CustomButton>
          </div>

          <div className="flex flex-wrap gap-1">
            {formData.customVocabulary.map((word) => (
              <Badge key={word} variant="secondary" className="gap-1 pr-1">
                {word}
                <CustomButton
                  type="text"
                  htmlType="button"
                  onClick={() =>
                    onFormChange({
                      customVocabulary: formData.customVocabulary.filter((w) => w !== word),
                    })
                  }
                  className="size-5 rounded-full p-0 hover:bg-muted-foreground/20"
                >
                  <X className="size-3" />
                </CustomButton>
              </Badge>
            ))}
          </div>
        </div>
      </FormRow>

      <FormRow label="Filter Words" description="Words the agent should not speak.">
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <TextInput
              name="filterWordsInput"
              value={filterWordsInput}
              onChange={(e) => setFilterWordsInput(e.target.value)}
              onKeyDown={(e: KeyboardEvent<HTMLInputElement>) =>
                e.key === 'Enter' && (e.preventDefault(), addFilterWord())
              }
            />
            <CustomButton type="default" onClick={addFilterWord}>
              Enter
            </CustomButton>
          </div>

          <div className="flex flex-wrap gap-1">
            {formData.filterWords.map((word) => (
              <Badge key={word} variant="secondary" className="gap-1 pr-1">
                {word}
                <CustomButton
                  type="text"
                  htmlType="button"
                  onClick={() =>
                    onFormChange({
                      filterWords: formData.filterWords.filter((w) => w !== word),
                    })
                  }
                  className="size-5 rounded-full p-0 hover:bg-muted-foreground/20"
                >
                  <X className="size-3" />
                </CustomButton>
              </Badge>
            ))}
          </div>
        </div>
      </FormRow>

      <FormRow
        label="Use Realistic Filler Words"
        description="Include natural filler words like 'uh' and 'um'."
      >
        <Switch
          checked={formData.useRealisticFillerWords}
          onCheckedChange={(checked) => onFormChange({ useRealisticFillerWords: checked })}
        />
      </FormRow>

      <FormRow label="Delete Agent" description="Deleting an agent removes all associated data.">
        <CustomButton type="danger" onClick={onDeleteAgent}>
          Delete Agent
        </CustomButton>
      </FormRow>
    </Form>
  );
}
