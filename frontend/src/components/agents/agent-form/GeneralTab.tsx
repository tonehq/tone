'use client';

import {
  CustomButton,
  FormTextInput,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import { Form } from '@/components/shared/Form';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import type { ServiceProvider } from '@/types/provider';
import { toSelectOptions } from '@/utils/selectUtils';
import { Bot, Brain, MessageSquare, Settings2, Trash2, X } from 'lucide-react';
import { KeyboardEvent, ReactNode, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import DynamicProviderFields, { type DynamicProviderFieldsHandle } from './DynamicProviderFields';
import type { AgentGeneralFormData } from './types';

export interface GeneralTabHandle {
  trigger: () => Promise<boolean>;
}

interface GeneralTabProps {
  formData: AgentGeneralFormData;
  llmProviders: ServiceProvider[];
  providersLoading?: boolean;
  onFormChange: (partial: Partial<AgentGeneralFormData>) => void;
  onDeleteAgent: () => void;
  onFormSubmit?: (values: AgentGeneralFormData) => void;
  onLlmValidityChange?: (handle: DynamicProviderFieldsHandle) => void;
  onGeneralValidityChange?: (handle: GeneralTabHandle) => void;
}

function SectionCard({
  icon,
  title,
  description,
  children,
  variant = 'default',
}: {
  icon: ReactNode;
  title: string;
  description?: string;
  children: ReactNode;
  variant?: 'default' | 'danger';
}) {
  return (
    <div className="rounded-xl border border-border bg-background shadow-sm">
      <div className="flex items-center gap-3 border-b border-border/60 px-5 py-3.5">
        <div
          className={
            variant === 'danger'
              ? 'flex size-8 shrink-0 items-center justify-center rounded-lg bg-destructive/10'
              : 'flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10'
          }
        >
          {icon}
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          {description && (
            <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}

function FormRow({
  label,
  description,
  required,
  error,
  children,
  isLast = false,
}: {
  label: string;
  description?: string;
  required?: boolean;
  error?: string;
  children: ReactNode;
  isLast?: boolean;
}) {
  return (
    <div
      className={`flex items-start justify-between gap-6 py-4 ${!isLast ? 'border-b border-border/40' : ''}`}
    >
      <div className="flex-[0_0_50%]">
        <h3 className="text-[13px] font-medium text-foreground">
          {label}
          {required && <span className="ml-0.5 text-destructive">*</span>}
        </h3>
        {description && (
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex-[0_0_45%]">
        {children}
        {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
      </div>
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
  onLlmValidityChange,
  onGeneralValidityChange,
}: GeneralTabProps) {
  const [vocabularyInput, setVocabularyInput] = useState('');
  const [filterWordsInput, setFilterWordsInput] = useState('');

  const { control, trigger } = useForm({
    mode: 'onChange',
    values: { name: formData.name },
  });

  useEffect(() => {
    onGeneralValidityChange?.({ trigger });
  }, [onGeneralValidityChange, trigger]);

  const selectedLlmProvider = useMemo(
    () => llmProviders.find((p) => p.id === formData.aiModel) ?? null,
    [llmProviders, formData.aiModel],
  );

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

      <div className="space-y-5">
        {/* Identity Section */}
        <SectionCard
          icon={<Bot size={16} className="text-primary" />}
          title="Agent Identity"
          description="Basic information about your agent."
        >
          <FormRow label="Agent Name" description="What name will your agent go by." required>
            <FormTextInput
              name="name"
              control={control}
              rules={{ required: 'Please enter a name for your agent' }}
              onValueChange={(v) => onFormChange({ name: v })}
            />
          </FormRow>

          <FormRow
            label="Agent Description"
            description="Provide a brief summary explaining your agent's purpose."
            isLast
          >
            <TextAreaField
              name="description"
              value={formData.description}
              onChange={(e) => onFormChange({ description: e.target.value })}
              rows={3}
            />
          </FormRow>
        </SectionCard>

        {/* AI Configuration Section */}
        <SectionCard
          icon={<Brain size={16} className="text-primary" />}
          title="AI Configuration"
          description="Choose the AI model powering your agent."
        >
          <FormRow label="AI Model" description="Opt for speed or depth to suit your agent's role.">
            <SelectInput
              name="aiModel"
              value={formData.aiModel != null ? String(formData.aiModel) : ''}
              onValueChange={(v) => {
                const newId = v ? Number(v) : null;
                onFormChange({ aiModel: newId, llmMetaData: {} });
              }}
              placeholder="Select a provider"
              options={toSelectOptions(llmProviders, {
                valueKey: 'id',
                labelKey: 'display_name',
              })}
              loading={providersLoading}
            />
          </FormRow>

          {selectedLlmProvider?.models?.length ? (
            <FormRow label="Model" description="Choose a model for your agent.">
              <SelectInput
                name="llmModel"
                value={formData.llmMetaData.model != null ? String(formData.llmMetaData.model) : ''}
                onValueChange={(v) => {
                  onFormChange({
                    llmMetaData: { ...formData.llmMetaData, model: v || null },
                  });
                }}
                options={toSelectOptions(selectedLlmProvider.models, {
                  valueKey: 'name',
                  labelKey: 'name',
                  valueFormatter: (m) => (m.meta_data as Record<string, string>)?.model ?? m.name,
                })}
                placeholder="Select a model"
                position="popper"
              />
            </FormRow>
          ) : null}

          {selectedLlmProvider?.meta_data_schema?.length ? (
            <DynamicProviderFields
              schema={selectedLlmProvider.meta_data_schema}
              values={formData.llmMetaData}
              onChange={(metaData) => onFormChange({ llmMetaData: metaData })}
              onValidityChange={onLlmValidityChange}
            />
          ) : null}

          <FormRow
            label="Use Realistic Filler Words"
            description="Include natural filler words like 'uh' and 'um'."
            isLast
          >
            <Switch
              checked={formData.useRealisticFillerWords}
              onCheckedChange={(checked) => onFormChange({ useRealisticFillerWords: checked })}
            />
          </FormRow>
        </SectionCard>

        {/* Messages Section */}
        <SectionCard
          icon={<MessageSquare size={16} className="text-primary" />}
          title="Messages"
          description="Configure the opening and closing messages."
        >
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

          <FormRow
            label="End Call Message"
            description="Message sent at the end of a conversation."
            isLast
          >
            <TextAreaField
              name="end_call_message"
              value={formData.end_call_message}
              onChange={(e) => onFormChange({ end_call_message: e.target.value })}
              rows={3}
            />
          </FormRow>
        </SectionCard>

        {/* Advanced Section */}
        <SectionCard
          icon={<Settings2 size={16} className="text-primary" />}
          title="Advanced Settings"
          description="Fine-tune vocabulary and word filters."
        >
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
                  Add
                </CustomButton>
              </div>

              {formData.customVocabulary.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
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
              )}
            </div>
          </FormRow>

          <FormRow label="Filter Words" description="Words the agent should not speak." isLast>
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
                  Add
                </CustomButton>
              </div>

              {formData.filterWords.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
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
              )}
            </div>
          </FormRow>
        </SectionCard>

        {/* Danger Zone */}
        <SectionCard
          icon={<Trash2 size={16} className="text-destructive" />}
          title="Danger Zone"
          description="Irreversible actions for this agent."
          variant="danger"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-[13px] font-medium text-foreground">Delete Agent</h3>
              <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                Permanently remove this agent and all associated data.
              </p>
            </div>
            <CustomButton type="danger" onClick={onDeleteAgent}>
              Delete Agent
            </CustomButton>
          </div>
        </SectionCard>
      </div>
    </Form>
  );
}
