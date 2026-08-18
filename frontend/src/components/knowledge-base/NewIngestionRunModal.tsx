'use client';

import { useEffect, useMemo, useState } from 'react';
import { Loader2, Play } from 'lucide-react';

import { CustomButton, CustomModal, SelectInput, TextInput } from '@/components/shared';
import {
  EMBEDDING_MODEL_CHOICES,
  getEmbeddingModelDefaultDimensions,
} from '@/components/knowledge-base/optionParamSchemas';
import { useIngestionConfigs } from '@/lib/api/ingestion-configs';
import { useCreateCustomIngestionRun, usePipelineOptions } from '@/lib/api/ingestion-runs';
import type { IngestionConfig } from '@/types/ingestionConfig';
import type { CreateIngestionRunPayload } from '@/types/pipelineOptions';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface NewIngestionRunModalProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
}

// Sentinel selection value for the "no saved config" option in the Config
// dropdown. Keeps every field editable and posts the individual field payload
// so the pre-config behavior is preserved 1:1.
const CUSTOM_SENTINEL = '__custom__';

interface FormState {
  parser: string;
  tokeniser: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: string;
  vector_store: string;
}

const EMPTY_FORM: FormState = {
  parser: '',
  tokeniser: '',
  embedding_provider: '',
  embedding_model: '',
  embedding_dimensions: '',
  vector_store: '',
};

function toOptions(values: string[]): { value: string; label: string }[] {
  return values.map((v) => ({ value: v, label: v }));
}

function formFromConfig(cfg: IngestionConfig): FormState {
  return {
    parser: cfg.parser,
    tokeniser: cfg.tokeniser,
    embedding_provider: cfg.embedding_provider,
    embedding_model: cfg.embedding_model,
    embedding_dimensions: String(cfg.embedding_dimensions),
    vector_store: cfg.vector_store,
  };
}

export default function NewIngestionRunModal({
  open,
  onClose,
  uploadId,
}: NewIngestionRunModalProps) {
  const { data: options, isLoading: optionsLoading } = usePipelineOptions(open);
  // 200 matches the backend page_size ceiling (see ListIngestionConfigsRequest
  // + apply_search_sort_pagination clamp). Beyond that, the picker would need
  // a searchable/paginated variant — cross that bridge when we get there.
  const { data: configsPage, isLoading: configsLoading } = useIngestionConfigs({
    page_no: 1,
    page_size: 200,
    is_active_only: true,
    sort_by: 'updated_at',
    sort_order: 'desc',
  });
  const createMutation = useCreateCustomIngestionRun(uploadId);

  const savedConfigs = useMemo(() => configsPage?.data ?? [], [configsPage]);

  const [configId, setConfigId] = useState<string>(CUSTOM_SENTINEL);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const configOptions = useMemo(
    () => [
      { value: CUSTOM_SENTINEL, label: 'Custom (one-off)' },
      ...savedConfigs.map((c) => ({ value: c.id, label: c.name })),
    ],
    [savedConfigs],
  );

  const selectedConfig = useMemo(
    () => (configId !== CUSTOM_SENTINEL ? savedConfigs.find((c) => c.id === configId) : undefined),
    [configId, savedConfigs],
  );

  // Reset the modal every open: select "Custom" and clear the form so
  // subsequent field prefill (from server defaults) runs cleanly.
  useEffect(() => {
    if (!open) {
      setConfigId(CUSTOM_SENTINEL);
      setForm(EMPTY_FORM);
      return;
    }
  }, [open]);

  // Deterministic re-seed: whenever configId changes (or options first arrive
  // for the current selection), fully rewrite the form from the source of
  // truth — a saved config's fields for a real id, server defaults for
  // CUSTOM. No `anyFilled` short-circuit — switching saved → Custom must
  // always return the fields to defaults so the user never submits a stale
  // recipe. `savedConfigs` is intentionally NOT a dep so TanStack cache
  // refetches don't wipe in-progress edits.
  useEffect(() => {
    if (!open) return;
    const picked =
      configId !== CUSTOM_SENTINEL ? savedConfigs.find((c) => c.id === configId) : undefined;
    if (picked) {
      setForm(formFromConfig(picked));
      return;
    }
    if (!options) return;
    setForm({
      parser: options.defaults.parser,
      tokeniser: options.defaults.tokeniser,
      embedding_provider: options.defaults.embedding_provider,
      embedding_model: options.defaults.embedding_model,
      embedding_dimensions: String(options.defaults.embedding_dimensions),
      vector_store: options.defaults.vector_store,
    });

    // read at effect time; excluded from deps to avoid wiping user edits on
    // background refetches.
  }, [open, options, configId]);

  const parserOptions = useMemo(() => toOptions(options?.parsers ?? []), [options]);
  const tokeniserOptions = useMemo(() => toOptions(options?.tokenisers ?? []), [options]);
  const embedderOptions = useMemo(() => toOptions(options?.embedders ?? []), [options]);
  const vectorStoreOptions = useMemo(() => toOptions(options?.vector_stores ?? []), [options]);

  const dimensionsNumber = Number(form.embedding_dimensions);
  const dimensionsValid =
    form.embedding_dimensions.trim() !== '' &&
    Number.isInteger(dimensionsNumber) &&
    dimensionsNumber > 0;

  const usingSavedConfig = !!selectedConfig;
  const fieldsDisabled = createMutation.isPending || usingSavedConfig;

  const canSubmit =
    !!form.parser &&
    !!form.tokeniser &&
    !!form.embedding_provider &&
    form.embedding_model.trim().length > 0 &&
    dimensionsValid &&
    !!form.vector_store &&
    !createMutation.isPending &&
    !optionsLoading;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    const payload: CreateIngestionRunPayload = usingSavedConfig
      ? { ingestion_config_id: selectedConfig!.id }
      : {
          parser: form.parser,
          tokeniser: form.tokeniser,
          embedding_provider: form.embedding_provider,
          embedding_model: form.embedding_model.trim(),
          embedding_dimensions: dimensionsNumber,
          vector_store: form.vector_store,
        };
    try {
      await createMutation.mutateAsync(payload);
      showToast.success(
        'Ingestion queued',
        'Ingestion is running in the background. It typically takes 5-10 minutes to complete.',
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const footer = (
    <div className="flex w-full items-center justify-end gap-2">
      <CustomButton type="default" onClick={onClose} disabled={createMutation.isPending}>
        Cancel
      </CustomButton>
      <CustomButton
        type="primary"
        onClick={handleSubmit}
        disabled={!canSubmit}
        loading={createMutation.isPending}
      >
        <Play className="mr-1 size-4" />
        Start ingestion
      </CustomButton>
    </div>
  );

  return (
    <CustomModal
      open={open}
      onClose={createMutation.isPending ? () => {} : onClose}
      title="New ingestion run"
      description="Kick off a new ingestion pipeline for this document. Previous runs are preserved — you can compare recipes side-by-side."
      width="sm:max-w-2xl"
      footer={footer}
    >
      {optionsLoading ? (
        <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Loading pipeline options…
        </div>
      ) : (
        <div className="flex flex-col gap-4 py-2">
          <SelectInput
            name="config"
            label="Config"
            options={configOptions}
            value={configId}
            onValueChange={setConfigId}
            placeholder="Select a saved config or use Custom"
            disabled={createMutation.isPending || configsLoading}
            helperText={
              usingSavedConfig
                ? 'Fields below are locked to this config. Pick "Custom (one-off)" to edit.'
                : 'Pick a saved config to reuse a recipe, or fill the fields for a one-off run.'
            }
          />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectInput
              name="parser"
              label="Parser"
              isRequired
              options={parserOptions}
              value={form.parser || undefined}
              onValueChange={(v) => setForm((f) => ({ ...f, parser: v }))}
              placeholder="Select a parser"
              disabled={fieldsDisabled}
            />
            <SelectInput
              name="tokeniser"
              label="Tokeniser"
              isRequired
              options={tokeniserOptions}
              value={form.tokeniser || undefined}
              onValueChange={(v) => setForm((f) => ({ ...f, tokeniser: v }))}
              placeholder="Select a tokeniser"
              disabled={fieldsDisabled}
            />
            <SelectInput
              name="embedding_provider"
              label="Embedding provider"
              isRequired
              options={embedderOptions}
              value={form.embedding_provider || undefined}
              onValueChange={(v) => setForm((f) => ({ ...f, embedding_provider: v }))}
              placeholder="Select a provider"
              disabled={fieldsDisabled}
            />
            <SelectInput
              name="embedding_model"
              label="Embedding model"
              isRequired
              options={
                form.embedding_model &&
                !EMBEDDING_MODEL_CHOICES.some((m) => m.value === form.embedding_model)
                  ? [
                      ...EMBEDDING_MODEL_CHOICES,
                      { value: form.embedding_model, label: `${form.embedding_model} (legacy)` },
                    ]
                  : EMBEDDING_MODEL_CHOICES
              }
              value={form.embedding_model || undefined}
              onValueChange={(v) =>
                setForm((f) => {
                  if (v === f.embedding_model) return f;
                  const dims = getEmbeddingModelDefaultDimensions(v);
                  return {
                    ...f,
                    embedding_model: v,
                    embedding_dimensions: dims != null ? String(dims) : f.embedding_dimensions,
                  };
                })
              }
              placeholder="Select an embedding model"
              disabled={fieldsDisabled}
            />
            <TextInput
              name="embedding_dimensions"
              label="Embedding dimensions"
              isRequired
              type="number"
              min={1}
              placeholder="Auto-set by model"
              value={form.embedding_dimensions}
              onChange={(e) => setForm((f) => ({ ...f, embedding_dimensions: e.target.value }))}
              error={form.embedding_dimensions.trim() !== '' && !dimensionsValid}
              helperText={
                form.embedding_dimensions.trim() !== '' && !dimensionsValid
                  ? 'Must be a positive integer.'
                  : 'Determined by the selected embedding model.'
              }
              disabled={fieldsDisabled}
              readOnly
            />
            <SelectInput
              name="vector_store"
              label="Vector store"
              isRequired
              options={vectorStoreOptions}
              value={form.vector_store || undefined}
              onValueChange={(v) => setForm((f) => ({ ...f, vector_store: v }))}
              placeholder="Select a store"
              disabled={fieldsDisabled}
            />
          </div>
        </div>
      )}
    </CustomModal>
  );
}
