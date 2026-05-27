'use client';

import { Brain, Settings2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { SelectInput, SliderField, TextInput } from '@/components/shared';
import { listProviderCatalog, listProviderModels } from '@/services/servicesService';
import type { ProviderCatalogItem, ProviderModel } from '@/types/service';
import type { AgentFormState } from '@/types/agent';
import { handleApiError } from '@/utils/helpers';

export default function AiStep() {
  const { control, setValue } = useFormContext<AgentFormState>();

  const [providers, setProviders] = useState<ProviderCatalogItem[]>([]);
  const [llmModels, setLlmModels] = useState<ProviderModel[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);

  // LLM provider id and model id both live under `config.llm_settings`
  // (a JSONB column on the backend). We previously wrote provider id into
  // `config.knowledge_model_id`, but that column is a FK to `models.id`
  // (KB embedding model), not a provider — saving caused a FK violation
  // surfaced misleadingly as "Unique constraint violated.".
  const llmProviderId = useWatch({
    control,
    name: 'config.llm_settings.provider_id' as never,
  }) as string | null | undefined;
  const llmModelId = useWatch({
    control,
    name: 'config.llm_settings.model_id' as never,
  }) as string | null | undefined;

  // ─── providers catalog ────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoadingProviders(true);
    listProviderCatalog()
      .then((items) => {
        if (cancelled) return;
        setProviders(items);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingProviders(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ─── LLM models (depends on chosen provider) ──────────────────────────────
  useEffect(() => {
    if (!llmProviderId) {
      setLlmModels([]);
      return;
    }
    let cancelled = false;
    setLoadingModels(true);
    listProviderModels(llmProviderId, { service_type: 'llm', page: 1, page_size: 100 })
      .then((res) => {
        if (!cancelled) setLlmModels(res.rows.filter((m) => m.is_active));
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingModels(false);
      });
    return () => {
      cancelled = true;
    };
  }, [llmProviderId]);

  const llmProviderOptions = useMemo(
    () =>
      providers
        .filter((p) => p.kinds.includes('llm'))
        .map((p) => ({ value: p.id, label: p.display_name })),
    [providers],
  );

  const llmModelOptions = useMemo(
    () => llmModels.map((m) => ({ value: m.id, label: m.display_name || m.name })),
    [llmModels],
  );

  const showModelField = !!llmProviderId;
  const showSettings = !!llmProviderId;

  return (
    <div className="flex flex-col gap-4">
      <SectionCard
        icon={<Brain className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.indigo}
        title="Reasoning model"
        description="The LLM that drives the conversation and decides what the agent says."
      >
        {/* Step 1 — Provider */}
        <SelectInput
          name="config.llm_settings.provider_id"
          label="Provider"
          options={llmProviderOptions}
          loading={loadingProviders}
          value={llmProviderId ?? ''}
          onValueChange={(v) => {
            setValue('config.llm_settings.provider_id' as never, (v || null) as never, {
              shouldDirty: true,
            });
            // New provider → forget the previously-chosen model.
            setValue('config.llm_settings.model_id' as never, null as never, {
              shouldDirty: true,
            });
          }}
          placeholder="Select an LLM provider"
        />

        {/* Step 2 — Model (revealed after provider is set) */}
        {showModelField && (
          <SelectInput
            name="config.llm_settings.model_id"
            label="Model"
            options={llmModelOptions}
            loading={loadingModels}
            value={llmModelId ?? ''}
            onValueChange={(v) =>
              setValue('config.llm_settings.model_id' as never, (v || null) as never, {
                shouldDirty: true,
              })
            }
            placeholder="Select a model"
            helperText="Optional — the provider's default model is used when blank."
          />
        )}
      </SectionCard>

      {showSettings && (
        <SectionCard
          icon={<Settings2 className="size-3.5" strokeWidth={2.25} />}
          iconClassName={ACCENTS.slate}
          title="LLM settings"
          description="Fine-tune how the model answers."
        >
          <SliderField
            name="config.llm_settings.temperature"
            label="Temperature"
            control={control}
            min={0}
            max={2}
            step={0.1}
            showLabels
            helperText="Lower = more deterministic. Higher = more creative."
          />
          <TextInput
            name="config.llm_settings.max_tokens"
            label="Max tokens per response"
            control={control}
            type="number"
            placeholder="1024"
          />
          <TextInput
            name="config.conversation_history_token_limit"
            label="Conversation history token limit"
            control={control}
            type="number"
            placeholder="4096"
            helperText="How much of the running conversation to keep in the prompt window."
          />
        </SectionCard>
      )}
    </div>
  );
}
