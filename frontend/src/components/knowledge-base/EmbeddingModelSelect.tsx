'use client';

import { SelectInput, TextInput } from '@/components/shared';
import { HintIcon, INGESTION_FIELD_HINTS } from '@/components/knowledge-base/ingestionFieldHints';
import {
  EMBEDDING_MODEL_CHOICES,
  getEmbeddingModelDefaultDimensions,
  getEmbeddingModelMaxTokens,
} from '@/components/knowledge-base/optionParamSchemas';

interface EmbeddingModelSelectProps {
  model: string;
  dimensions: string;
  /**
   * Called with BOTH fields on any change so the parent can merge in one
   * `setForm`. Selecting a model auto-fills its default dimensions.
   */
  onChange: (next: { embedding_model: string; embedding_dimensions: string }) => void;
  disabled?: boolean;
  /** Show the "Max input: N tokens" helper under the model select. */
  showMaxTokensHint?: boolean;
}

/**
 * The embedding-model select + read-only dimensions pair, shared by
 * NewIngestionRunModal and IngestionConfigDrawer. Returns two form fields as a
 * fragment so each caller places them inside its own grid — preserving each
 * screen's existing layout.
 */
export default function EmbeddingModelSelect({
  model,
  dimensions,
  onChange,
  disabled = false,
  showMaxTokensHint = false,
}: EmbeddingModelSelectProps) {
  const dimsNumber = Number(dimensions);
  const dimensionsValid =
    dimensions.trim() !== '' && Number.isInteger(dimsNumber) && dimsNumber > 0;

  // If an edited config carries a legacy model that's no longer in the curated
  // list, keep it selectable so the form can still open and save without
  // silently switching models.
  const modelOptions =
    model && !EMBEDDING_MODEL_CHOICES.some((m) => m.value === model)
      ? [...EMBEDDING_MODEL_CHOICES, { value: model, label: `${model} (legacy)` }]
      : EMBEDDING_MODEL_CHOICES;

  const maxTokens = getEmbeddingModelMaxTokens(model);

  return (
    <>
      <SelectInput
        name="embedding_model"
        label="Embedding model"
        labelHint={<HintIcon text={INGESTION_FIELD_HINTS.embedding_model} />}
        isRequired
        options={modelOptions}
        value={model || undefined}
        onValueChange={(v) => {
          if (v === model) return;
          const dims = getEmbeddingModelDefaultDimensions(v);
          onChange({
            embedding_model: v,
            embedding_dimensions: dims != null ? String(dims) : dimensions,
          });
        }}
        placeholder="Select an embedding model"
        disabled={disabled}
        helperText={
          showMaxTokensHint && maxTokens !== undefined
            ? `Max input: ${maxTokens} tokens`
            : undefined
        }
      />
      <TextInput
        name="embedding_dimensions"
        label="Embedding dimensions"
        labelHint={<HintIcon text={INGESTION_FIELD_HINTS.embedding_dimensions} />}
        isRequired
        type="number"
        min={1}
        placeholder="Auto-set by model"
        value={dimensions}
        onChange={(e) => onChange({ embedding_model: model, embedding_dimensions: e.target.value })}
        error={dimensions.trim() !== '' && !dimensionsValid}
        helperText={
          dimensions.trim() !== '' && !dimensionsValid
            ? 'Must be a positive integer.'
            : 'Determined by the selected embedding model.'
        }
        disabled={disabled}
        readOnly
      />
    </>
  );
}
