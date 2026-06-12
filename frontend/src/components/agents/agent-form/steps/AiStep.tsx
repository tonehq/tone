'use client';

import { Brain, Settings2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import DynamicProviderFields from '@/components/agents/agent-form/DynamicProviderFields';
import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { SelectInput, SliderField, TextInput } from '@/components/shared';
import { listProviderCatalog, listProviderModels } from '@/services/servicesService';
import type { ProviderCatalogItem, ProviderModel } from '@/types/service';
import type { MetaDataSchemaField } from '@/types/provider';
import type { AgentFormState } from '@/types/agent';
import { handleApiError } from '@/utils/helpers';

/** Keys in llm_settings that are structural (not schema fields). */
const LLM_STRUCTURAL_KEYS = new Set(['provider_id', 'model_id', 'model', 'is_s2s']);

export default function AiStep() {
  const { control, setValue, getValues } = useFormContext<AgentFormState>();

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

  // Get meta_data_schema from the selected model (preferred) or fall back to provider
  const llmSchema = useMemo<MetaDataSchemaField[]>(() => {
    if (llmModelId) {
      const model = llmModels.find((m) => m.id === llmModelId);
      if (model?.meta_data_schema && model.meta_data_schema.length > 0) {
        return model.meta_data_schema;
      }
    }
    // Fallback: provider-level schema
    if (!llmProviderId) return [];
    const provider = providers.find((p) => p.id === llmProviderId);
    return provider?.meta_data_schema?.llm ?? [];
  }, [llmModelId, llmModels, llmProviderId, providers]);

  // Get model-level meta_data for the selected model (e.g. max_completion_tokens)
  const selectedModelMetaData = useMemo(() => {
    if (!llmModelId) return null;
    const model = llmModels.find((m) => m.id === llmModelId);
    return model?.meta_data ?? null;
  }, [llmModelId, llmModels]);

  // Clear stale schema field values when the user CHANGES the provider/model
  // (e.g. switching from GPT-4o to GPT-5 should remove temperature/top_p that
  // GPT-5 doesn't support). Skipped on the initial settle so the saved
  // llm_settings isn't silently mutated on load — that mutation would desync
  // _formValues from _defaultValues, and any later RHF deep-equality recheck
  // (focus/blur, version select, etc.) would flip isDirty true, triggering a
  // spurious "discard changes?" prompt despite zero user edits. shouldDirty:
  // true here because at this point it IS a user edit (changing the model).
  const prevAllowedKeysRef = useRef<Set<string> | null>(null);
  useEffect(() => {
    if (!llmSchema.length) {
      prevAllowedKeysRef.current = null;
      return;
    }
    const allowedKeys = new Set(llmSchema.map((f) => f.name));
    const prev = prevAllowedKeysRef.current;
    prevAllowedKeysRef.current = allowedKeys;
    if (prev === null) return;
    if (prev.size === allowedKeys.size && [...prev].every((k) => allowedKeys.has(k))) return;

    const current = getValues('config.llm_settings' as never) as
      | Record<string, unknown>
      | undefined;
    if (!current) return;
    for (const key of Object.keys(current)) {
      if (!LLM_STRUCTURAL_KEYS.has(key) && !allowedKeys.has(key)) {
        setValue(`config.llm_settings.${key}` as never, undefined as never, {
          shouldDirty: true,
        });
      }
    }
  }, [llmSchema]);

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
            control={control}
            rules={{ required: 'Please select a model' }}
            options={llmModelOptions}
            loading={loadingModels}
            value={llmModelId ?? ''}
            onValueChange={(v) =>
              setValue('config.llm_settings.model_id' as never, (v || null) as never, {
                shouldDirty: true,
              })
            }
            placeholder="Select a model"
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
          {llmSchema.length > 0 ? (
            <DynamicProviderFields
              fields={llmSchema}
              basePath="config.llm_settings"
              modelMetaData={selectedModelMetaData}
            />
          ) : (
            <>
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
                name="config.llm_settings.max_completion_tokens"
                label="Max completion tokens"
                control={control}
                type="number"
                placeholder="1024"
              />
            </>
          )}
        </SectionCard>
      )}
    </div>
  );
}
