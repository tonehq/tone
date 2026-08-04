'use client';

import { useEffect, useMemo, useState } from 'react';
import { Loader2, Play } from 'lucide-react';

import { CustomButton, CustomModal, SelectInput, TextInput } from '@/components/shared';
import { useCreateCustomIngestionRun, usePipelineOptions } from '@/lib/api/ingestion-runs';
import type { CreateIngestionRunPayload } from '@/types/pipelineOptions';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface NewIngestionRunModalProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
}

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

export default function NewIngestionRunModal({
  open,
  onClose,
  uploadId,
}: NewIngestionRunModalProps) {
  const { data: options, isLoading: optionsLoading } = usePipelineOptions(open);
  const createMutation = useCreateCustomIngestionRun(uploadId);

  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  // Prefill from server-provided defaults once the options land AND the modal
  // is open. Reset when the modal closes so a stale draft never bleeds into
  // the next open — matches the reset pattern used by ManualEvalsModal.
  useEffect(() => {
    if (!open) {
      setForm(EMPTY_FORM);
      return;
    }
    if (!options) return;
    setForm((prev) => {
      // Only fill fields the user hasn't already touched (all empty on first
      // open; on subsequent renders the object identity stability keeps user
      // edits intact).
      if (
        prev.parser ||
        prev.tokeniser ||
        prev.embedding_provider ||
        prev.embedding_model ||
        prev.embedding_dimensions ||
        prev.vector_store
      ) {
        return prev;
      }
      return {
        parser: options.defaults.parser,
        tokeniser: options.defaults.tokeniser,
        embedding_provider: options.defaults.embedding_provider,
        embedding_model: options.defaults.embedding_model,
        embedding_dimensions: String(options.defaults.embedding_dimensions),
        vector_store: options.defaults.vector_store,
      };
    });
  }, [open, options]);

  const parserOptions = useMemo(() => toOptions(options?.parsers ?? []), [options]);
  const tokeniserOptions = useMemo(() => toOptions(options?.tokenisers ?? []), [options]);
  const embedderOptions = useMemo(() => toOptions(options?.embedders ?? []), [options]);
  const vectorStoreOptions = useMemo(() => toOptions(options?.vector_stores ?? []), [options]);

  const dimensionsNumber = Number(form.embedding_dimensions);
  const dimensionsValid =
    form.embedding_dimensions.trim() !== '' &&
    Number.isInteger(dimensionsNumber) &&
    dimensionsNumber > 0;

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
    const payload: CreateIngestionRunPayload = {
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
        <div className="grid grid-cols-1 gap-4 py-2 sm:grid-cols-2">
          <SelectInput
            name="parser"
            label="Parser"
            isRequired
            options={parserOptions}
            value={form.parser || undefined}
            onValueChange={(v) => setForm((f) => ({ ...f, parser: v }))}
            placeholder="Select a parser"
            disabled={createMutation.isPending}
          />
          <SelectInput
            name="tokeniser"
            label="Tokeniser"
            isRequired
            options={tokeniserOptions}
            value={form.tokeniser || undefined}
            onValueChange={(v) => setForm((f) => ({ ...f, tokeniser: v }))}
            placeholder="Select a tokeniser"
            disabled={createMutation.isPending}
          />
          <SelectInput
            name="embedding_provider"
            label="Embedding provider"
            isRequired
            options={embedderOptions}
            value={form.embedding_provider || undefined}
            onValueChange={(v) => setForm((f) => ({ ...f, embedding_provider: v }))}
            placeholder="Select a provider"
            disabled={createMutation.isPending}
          />
          <TextInput
            name="embedding_model"
            label="Embedding model"
            isRequired
            placeholder="e.g. text-embedding-3-large"
            value={form.embedding_model}
            onChange={(e) => setForm((f) => ({ ...f, embedding_model: e.target.value }))}
            disabled={createMutation.isPending}
          />
          <TextInput
            name="embedding_dimensions"
            label="Embedding dimensions"
            isRequired
            type="number"
            min={1}
            placeholder="e.g. 3072"
            value={form.embedding_dimensions}
            onChange={(e) => setForm((f) => ({ ...f, embedding_dimensions: e.target.value }))}
            error={form.embedding_dimensions.trim() !== '' && !dimensionsValid}
            helperText={
              form.embedding_dimensions.trim() !== '' && !dimensionsValid
                ? 'Must be a positive integer.'
                : undefined
            }
            disabled={createMutation.isPending}
          />
          <SelectInput
            name="vector_store"
            label="Vector store"
            isRequired
            options={vectorStoreOptions}
            value={form.vector_store || undefined}
            onValueChange={(v) => setForm((f) => ({ ...f, vector_store: v }))}
            placeholder="Select a store"
            disabled={createMutation.isPending}
          />
        </div>
      )}
    </CustomModal>
  );
}
