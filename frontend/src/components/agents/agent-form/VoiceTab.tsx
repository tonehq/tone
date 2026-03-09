'use client';

import { CustomButton, SelectInput } from '@/components/shared';
import { Slider } from '@/components/ui/slider';
import { languages } from '@/data/mockAgents';
import { getVoicesByProvider, type VoiceItem } from '@/services/voiceService';
import type { ServiceProvider } from '@/types/provider';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { toSelectOptions } from '@/utils/selectUtils';
import { Gauge, Mic, Volume2 } from 'lucide-react';
import { type ReactNode, useEffect, useMemo, useState } from 'react';
import DynamicProviderFields from './DynamicProviderFields';
import type { AgentVoiceFormData } from './types';
import VoiceSelect from './VoiceSelect';

interface VoiceTabProps {
  formData: AgentVoiceFormData;
  ttsProviders: ServiceProvider[];
  sttProviders: ServiceProvider[];
  providersLoading?: boolean;
  onFormChange: (partial: Partial<AgentVoiceFormData>) => void;
}

function SectionCard({
  icon,
  title,
  description,
  children,
}: {
  icon: ReactNode;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-background shadow-sm">
      <div className="flex items-center gap-3 border-b border-border/60 px-5 py-3.5">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
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
  children,
  isLast = false,
}: {
  label: string;
  description?: string;
  children: ReactNode;
  isLast?: boolean;
}) {
  return (
    <div
      className={`flex items-start justify-between gap-6 py-4 ${!isLast ? 'border-b border-border/40' : ''}`}
    >
      <div className="flex-[0_0_50%]">
        <h3 className="text-[13px] font-medium text-foreground">{label}</h3>
        {description && (
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex-[0_0_45%]">{children}</div>
    </div>
  );
}

export default function VoiceTab({
  formData,
  ttsProviders,
  sttProviders,
  providersLoading,
  onFormChange,
}: VoiceTabProps) {
  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(false);

  const ttsOptions = toSelectOptions(ttsProviders, { valueKey: 'id', labelKey: 'display_name' });
  const sttOptions = toSelectOptions(sttProviders, { valueKey: 'id', labelKey: 'display_name' });

  const selectedTtsProvider = useMemo(
    () => ttsProviders.find((p) => p.id === formData.voiceProvider) ?? null,
    [ttsProviders, formData.voiceProvider],
  );
  const selectedSttProvider = useMemo(
    () => sttProviders.find((p) => p.id === formData.sttProvider) ?? null,
    [sttProviders, formData.sttProvider],
  );

  useEffect(() => {
    if (!formData.voiceProvider) {
      setVoices([]);
      return;
    }
    let cancelled = false;
    setVoicesLoading(true);
    getVoicesByProvider(formData.voiceProvider)
      .then((data) => {
        if (!cancelled) {
          setVoices(data.voices ?? []);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setVoices([]);
          handleApiError(error);
        }
      })
      .finally(() => {
        if (!cancelled) setVoicesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [formData.voiceProvider]);

  const availableLanguageOptions = useMemo(() => {
    const langMap = new Map(languages.map((l) => [l.value, l]));
    const uniqueLangs = [...new Set(voices.map((v) => v.language))].sort();
    const langItems = uniqueLangs.map((code) => {
      const known = langMap.get(code);
      return { code, name: known ? known.label : code, flag: known?.flag ?? '' };
    });
    return toSelectOptions(langItems, {
      valueKey: 'code',
      labelKey: 'name',
      labelFormatter: (item) => (item.flag ? `${item.flag} ${item.name}` : String(item.name)),
    });
  }, [voices]);

  const filteredVoiceOptions = useMemo(() => {
    if (!formData.language) return voices;
    return voices.filter((v) => v.language === formData.language);
  }, [voices, formData.language]);

  const _sttLanguageOptions = toSelectOptions(languages, {
    valueKey: 'value',
    labelKey: 'label',
    labelFormatter: (lang) => `${lang.flag} ${lang.label}`,
  });

  return (
    <div className="space-y-5">
      {/* Text-to-Speech Section */}
      <SectionCard
        icon={<Volume2 size={16} className="text-primary" />}
        title="Text-to-Speech"
        description="Configure how your agent's voice sounds."
      >
        <FormRow
          label="Voice Provider"
          description="Select the service used to generate your agent's voice."
        >
          <SelectInput
            name="voiceProvider"
            value={formData.voiceProvider != null ? String(formData.voiceProvider) : ''}
            onValueChange={(v) => {
              const newId = v ? Number(v) : null;
              onFormChange({ voiceProvider: newId, ttsMetaData: {}, language: '' });
            }}
            options={ttsOptions}
            placeholder="Select a provider"
            loading={providersLoading}
          />
        </FormRow>

        {formData.voiceProvider != null && (
          <FormRow label="Language" description="Select a language to filter available voices.">
            <SelectInput
              name="voiceLanguage"
              value={formData.language}
              onValueChange={(v) => {
                onFormChange({
                  language: v,
                  ttsMetaData: { ...formData.ttsMetaData, voice_id: null },
                });
              }}
              options={availableLanguageOptions}
              placeholder="Select a language"
              loading={voicesLoading}
            />
          </FormRow>
        )}

        {formData.voiceProvider != null && formData.language && (
          <FormRow label="Voice" description="Choose a voice for your agent.">
            <VoiceSelect
              name="voiceId"
              voices={filteredVoiceOptions}
              value={
                formData.ttsMetaData.voice_id != null ? String(formData.ttsMetaData.voice_id) : ''
              }
              onValueChange={(v) => {
                onFormChange({
                  ttsMetaData: { ...formData.ttsMetaData, voice_id: v || null },
                });
              }}
              placeholder="Select a voice"
              loading={voicesLoading}
            />
          </FormRow>
        )}

        {selectedTtsProvider?.meta_data_schema?.length ? (
          <DynamicProviderFields
            schema={selectedTtsProvider.meta_data_schema.filter(
              (f) => f.name !== 'language' && f.name !== 'speed',
            )}
            values={formData.ttsMetaData}
            onChange={(metaData) => onFormChange({ ttsMetaData: metaData })}
          />
        ) : null}

        <FormRow
          label="Voice Speed"
          description="Adjust how fast or slow your agent will talk."
          isLast
        >
          <div className="w-full px-1">
            <Slider
              value={[formData.voiceSpeed]}
              onValueChange={([v]) => onFormChange({ voiceSpeed: v })}
              min={0}
              max={100}
              step={1}
            />
            <div className="mt-1.5 flex justify-between text-[11px] text-muted-foreground">
              <span>Slow</span>
              <span>Normal</span>
              <span>Fast</span>
            </div>
          </div>
        </FormRow>
      </SectionCard>

      {/* Speech-to-Text Section */}
      <SectionCard
        icon={<Mic size={16} className="text-primary" />}
        title="Speech-to-Text"
        description="Configure how your agent transcribes speech."
      >
        <FormRow
          label="STT Provider"
          description="Select the service used to transcribe calls to text."
        >
          <SelectInput
            name="sttProvider"
            value={formData.sttProvider != null ? String(formData.sttProvider) : ''}
            onValueChange={(v) => {
              const newId = v ? Number(v) : null;
              onFormChange({ sttProvider: newId, sttMetaData: {} });
            }}
            options={sttOptions}
            placeholder="Select a provider"
            loading={providersLoading}
          />
        </FormRow>

        {selectedSttProvider?.meta_data_schema?.length ? (
          <DynamicProviderFields
            schema={selectedSttProvider.meta_data_schema.filter((f) => f.name !== 'language')}
            values={formData.sttMetaData}
            onChange={(metaData) => onFormChange({ sttMetaData: metaData })}
          />
        ) : null}

        <FormRow
          label="Speech Recognition"
          description="Adjusts how quickly incoming speech is transcribed."
          isLast
        >
          <div className="flex gap-2" role="radiogroup" aria-label="Speech Recognition">
            {[
              {
                value: 'fast' as const,
                label: 'Faster',
                desc: 'Lower quality, suitable for most use cases',
              },
              {
                value: 'accurate' as const,
                label: 'High Accuracy',
                desc: 'Slower, for high accuracy use cases',
              },
            ].map((item) => {
              const isActive = formData.speechRecognition === item.value;
              return (
                <CustomButton
                  key={item.value}
                  type="default"
                  htmlType="button"
                  role="radio"
                  aria-checked={isActive}
                  className={cn(
                    '!flex-col !h-auto !w-[170px] !items-start rounded-md border p-3 text-left transition-colors',
                    isActive
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-muted-foreground/50',
                  )}
                  onClick={() => onFormChange({ speechRecognition: item.value })}
                >
                  <span className="block text-sm font-semibold text-foreground">{item.label}</span>
                  <span className="block text-xs text-muted-foreground text-wrap">{item.desc}</span>
                </CustomButton>
              );
            })}
          </div>
        </FormRow>
      </SectionCard>

      {/* Response Timing Section */}
      <SectionCard
        icon={<Gauge size={16} className="text-primary" />}
        title="Response Timing"
        description="Control how quickly your agent responds."
      >
        <FormRow
          label="Patience Level"
          description="Adjust the response speed. Low for rapid exchanges, high for more focused turns."
          isLast
        >
          <div className="flex gap-2" role="radiogroup" aria-label="Patience Level">
            {[
              { value: 'low' as const, label: 'Low', desc: '~1 sec' },
              { value: 'medium' as const, label: 'Medium', desc: '~3 sec' },
              { value: 'high' as const, label: 'High', desc: '~5 sec' },
            ].map((item) => {
              const isActive = formData.patienceLevel === item.value;
              return (
                <CustomButton
                  key={item.value}
                  type="default"
                  htmlType="button"
                  role="radio"
                  aria-checked={isActive}
                  className={cn(
                    'flex !flex-col h-auto w-[105px] !items-start rounded-md border p-2 text-left transition-colors',
                    isActive
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-muted-foreground/50',
                  )}
                  onClick={() => onFormChange({ patienceLevel: item.value })}
                >
                  <span className="block text-sm font-semibold text-foreground">{item.label}</span>
                  <span className="block text-xs text-muted-foreground">{item.desc}</span>
                </CustomButton>
              );
            })}
          </div>
        </FormRow>
      </SectionCard>
    </div>
  );
}
