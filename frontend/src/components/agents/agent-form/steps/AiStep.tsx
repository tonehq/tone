'use client';

import { Brain, Settings2 } from 'lucide-react';
import { useEffect, useMemo, useRef } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import DynamicProviderFields from '@/components/agents/agent-form/DynamicProviderFields';
import {
  reconcileSchemaValues,
  resetSchemaFields,
} from '@/components/agents/agent-form/reconcileSchemaValues';
import SectionCard from '@/components/agents/agent-form/SectionCard';
import { SelectInput, SliderField, TextInput } from '@/components/shared';
import { useLlmModels, useLlmProviderCatalog } from '@/lib/api/providerCatalog';
import { useQueryErrorToast } from '@/lib/api/useQueryErrorToast';
import type { MetaDataSchemaField } from '@/types/provider';
import type { AgentFormState } from '@/types/agent';

/** Keys in llm_settings that are structural (not schema fields). */
const LLM_STRUCTURAL_KEYS = new Set(['provider_id', 'model_id', 'model', 'is_s2s']);

export default function AiStep() {
  const { control, setValue, getValues } = useFormContext<AgentFormState>();

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

  // ─── providers catalog + LLM models (models depend on chosen provider) ────
  const {
    data: providers = [],
    isLoading: loadingProviders,
    error: providersError,
  } = useLlmProviderCatalog();
  const {
    data: llmModels = [],
    isFetching: loadingModels,
    error: modelsError,
  } = useLlmModels(llmProviderId);
  useQueryErrorToast(providersError);
  useQueryErrorToast(modelsError);

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

  // Reconcile saved schema field values against the CURRENT provider/model
  // schema whenever the user changes provider or model. Two things happen:
  // (a) keys no longer in the schema are cleared (e.g. GPT-5 doesn't accept
  // temperature/top_p), (b) numeric values are clamped to the new field's
  // [min, max] range (e.g. AWS Bedrock temperature=2 → clamp to 1 when
  // switching to Anthropic where the max is 1). Without the clamp the slider
  // renders at max but the raw form value is still out of range, so save
  // fails backend validation with the previous provider's leftover number.
  //
  // Skipped on the initial settle so the saved llm_settings isn't silently
  // mutated on load — that mutation would desync _formValues from
  // _defaultValues, and any later RHF deep-equality recheck (focus/blur,
  // version select, etc.) would flip isDirty true, triggering a spurious
  // "discard changes?" prompt despite zero user edits. shouldDirty: true
  // below because at that point it IS a user edit (changing provider/model).
  const prevSchemaRef = useRef<MetaDataSchemaField[] | null>(null);
  useEffect(() => {
    if (!llmSchema.length) {
      prevSchemaRef.current = null;
      return;
    }
    const prev = prevSchemaRef.current;
    prevSchemaRef.current = llmSchema;
    if (prev === null) return;

    const current = getValues('config.llm_settings' as never) as
      | Record<string, unknown>
      | undefined;
    if (!current) return;

    const changes = reconcileSchemaValues(
      current,
      llmSchema,
      LLM_STRUCTURAL_KEYS,
      selectedModelMetaData,
    );
    for (const [key, next] of Object.entries(changes)) {
      setValue(`config.llm_settings.${key}` as never, next as never, {
        shouldDirty: true,
      });
    }
  }, [llmSchema, selectedModelMetaData]);

  return (
    <div className="flex flex-col gap-4">
      <SectionCard
        icon={<Brain className="size-3.5" strokeWidth={2.25} />}
        tone="indigo"
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
            // Full reset on provider change: every schema-driven tuning field
            // (temperature/top_p/top_k/max_completion_tokens/…) is cleared
            // and provider_id + model_id are re-seeded in one atomic write.
            // Cross-provider carryover is unsafe — see resetSchemaFields.
            const current = getValues('config.llm_settings' as never) as
              | Record<string, unknown>
              | undefined;
            const kept = resetSchemaFields(current, LLM_STRUCTURAL_KEYS);
            setValue(
              'config.llm_settings' as never,
              { ...kept, provider_id: v || null, model_id: null } as never,
              { shouldDirty: true },
            );
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
          tone="slate"
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
