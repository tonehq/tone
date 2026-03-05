'use client';

import { CustomButton, SelectInput } from '@/components/shared';
import { Slider } from '@/components/ui/slider';
import { languages } from '@/data/mockAgents';
import { getVoicesByProvider, type VoiceItem } from '@/services/voiceService';
import type { ServiceProvider } from '@/types/provider';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { type ReactNode, useEffect, useMemo, useState } from 'react';
import DynamicProviderFields from './DynamicProviderFields';
import type { AgentVoiceFormData } from './types';

interface VoiceTabProps {
  formData: AgentVoiceFormData;
  ttsProviders: ServiceProvider[];
  sttProviders: ServiceProvider[];
  providersLoading?: boolean;
  onFormChange: (partial: Partial<AgentVoiceFormData>) => void;
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

export default function VoiceTab({
  formData,
  ttsProviders,
  sttProviders,
  providersLoading,
  onFormChange,
}: VoiceTabProps) {
  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(false);

  const ttsOptions = ttsProviders.map((p) => ({ value: String(p.id), label: p.display_name }));
  const sttOptions = sttProviders.map((p) => ({ value: String(p.id), label: p.display_name }));

  const selectedTtsProvider = useMemo(
    () => ttsProviders.find((p) => p.id === formData.voiceProvider) ?? null,
    [ttsProviders, formData.voiceProvider],
  );
  const selectedSttProvider = useMemo(
    () => sttProviders.find((p) => p.id === formData.sttProvider) ?? null,
    [sttProviders, formData.sttProvider],
  );

  // Fetch voices when TTS provider changes
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

  // Build language options from voices API response, enrich with flag/label from static list
  const availableLanguageOptions = useMemo(() => {
    const langMap = new Map(languages.map((l) => [l.value, l]));
    const uniqueLangs = [...new Set(voices.map((v) => v.language))].sort();
    return uniqueLangs.map((code) => {
      const known = langMap.get(code);
      return {
        value: code,
        label: known ? `${known.flag} ${known.label}` : code,
      };
    });
  }, [voices]);

  // Filter voices by selected language
  const filteredVoiceOptions = useMemo(() => {
    if (!formData.language) return voices;
    return voices.filter((v) => v.language === formData.language);
  }, [voices, formData.language]);

  const voiceOptions = filteredVoiceOptions.map((v) => ({
    value: v.voice_id,
    label: v.name,
  }));

  // Language options with flags for STT
  const sttLanguageOptions = languages.map((lang) => ({
    value: lang.value,
    label: `${lang.flag} ${lang.label}`,
  }));

  return (
    <div className="space-y-0 py-4">
      {/* Voice Provider (TTS) */}
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

      {/* Language (shown after TTS provider is selected and voices are loaded) */}
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

      {/* Voice select (filtered by language) */}
      {formData.voiceProvider != null && formData.language && (
        <FormRow label="Voice" description="Choose a voice for your agent.">
          <SelectInput
            name="voiceId"
            value={
              formData.ttsMetaData.voice_id != null ? String(formData.ttsMetaData.voice_id) : ''
            }
            onValueChange={(v) => {
              onFormChange({
                ttsMetaData: { ...formData.ttsMetaData, voice_id: v || null },
              });
            }}
            options={voiceOptions}
            placeholder="Select a voice"
            loading={voicesLoading}
            position="popper"
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

      {/* STT Provider */}
      <FormRow
        label="STT Provider"
        description="Select the service used to transcribe calls to text (Speech-to-Text)."
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

      {/* STT Language */}
      {formData.sttProvider != null && (
        <FormRow label="Language" description="The language your agent understands.">
          <SelectInput
            name="sttLanguage"
            value={
              formData.sttMetaData.language != null ? String(formData.sttMetaData.language) : ''
            }
            onValueChange={(v) => {
              onFormChange({
                sttMetaData: { ...formData.sttMetaData, language: v || null },
              });
            }}
            options={sttLanguageOptions}
            placeholder="Select a language"
          />
        </FormRow>
      )}

      {selectedSttProvider?.meta_data_schema?.length ? (
        <DynamicProviderFields
          schema={selectedSttProvider.meta_data_schema.filter((f) => f.name !== 'language')}
          values={formData.sttMetaData}
          onChange={(metaData) => onFormChange({ sttMetaData: metaData })}
        />
      ) : null}

      {/* Voice Speed */}
      <FormRow label="Voice Speed" description="Adjust how fast or slow your agent will talk.">
        <div className="w-full px-1">
          <Slider
            value={[formData.voiceSpeed]}
            onValueChange={([v]) => onFormChange({ voiceSpeed: v })}
            min={0}
            max={100}
            step={1}
          />
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>Slow</span>
            <span>Normal</span>
            <span>Fast</span>
          </div>
        </div>
      </FormRow>

      {/* Patience Level */}
      <FormRow
        label="Patience Level"
        description="Adjust the response speed. Low for rapid exchanges, high for more focused turns."
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

      {/* Speech Recognition */}
      <FormRow
        label="Speech Recognition"
        description="Adjusts how quickly incoming speech is transcribed."
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
    </div>
  );
}
