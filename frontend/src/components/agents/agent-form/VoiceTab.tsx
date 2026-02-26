'use client';

import { SelectInput } from '@/components/shared';
import { Slider } from '@/components/ui/slider';
import { languages } from '@/data/mockAgents';
import { cn } from '@/lib/utils';
import type { ServiceProvider } from '@/types/provider';
import type { ReactNode } from 'react';
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
  const languageOptions = languages.map((lang) => ({
    value: lang.value,
    label: `${lang.flag} ${lang.label}`,
  }));

  const ttsOptions = ttsProviders.map((p) => ({ value: String(p.id), label: p.display_name }));
  const sttOptions = sttProviders.map((p) => ({ value: String(p.id), label: p.display_name }));

  return (
    <div className="space-y-0 py-4">
      {/* Language */}
      <FormRow label="Language" description="The language your agent understands.">
        <SelectInput
          name="language"
          value={formData.language}
          onValueChange={(v) => onFormChange({ language: v })}
          options={languageOptions}
          placeholder="Select a language"
        />
      </FormRow>

      {/* Voice Provider (TTS) */}
      <FormRow
        label="Voice Provider"
        description="Select the service used to generate your agent's voice."
      >
        <SelectInput
          name="voiceProvider"
          value={formData.voiceProvider != null ? String(formData.voiceProvider) : ''}
          onValueChange={(v) => onFormChange({ voiceProvider: v ? Number(v) : null })}
          options={ttsOptions}
          placeholder="Select a provider"
          loading={providersLoading}
        />
      </FormRow>

      {/* STT Provider */}
      <FormRow
        label="STT Provider"
        description="Select the service used to transcribe calls to text (Speech-to-Text)."
      >
        <SelectInput
          name="sttProvider"
          value={formData.sttProvider != null ? String(formData.sttProvider) : ''}
          onValueChange={(v) => onFormChange({ sttProvider: v ? Number(v) : null })}
          options={sttOptions}
          placeholder="Select a provider"
          loading={providersLoading}
        />
      </FormRow>

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
              <button
                key={item.value}
                type="button"
                role="radio"
                aria-checked={isActive}
                className={cn(
                  'w-[105px] rounded-md border p-2 text-left transition-colors',
                  isActive
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-muted-foreground/50',
                )}
                onClick={() => onFormChange({ patienceLevel: item.value })}
              >
                <span className="block text-sm font-semibold text-foreground">{item.label}</span>
                <span className="block text-xs text-muted-foreground">{item.desc}</span>
              </button>
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
              <button
                key={item.value}
                type="button"
                role="radio"
                aria-checked={isActive}
                className={cn(
                  'w-[170px] rounded-md border p-3 text-left transition-colors',
                  isActive
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-muted-foreground/50',
                )}
                onClick={() => onFormChange({ speechRecognition: item.value })}
              >
                <span className="block text-sm font-semibold text-foreground">{item.label}</span>
                <span className="block text-xs text-muted-foreground">{item.desc}</span>
              </button>
            );
          })}
        </div>
      </FormRow>
    </div>
  );
}
