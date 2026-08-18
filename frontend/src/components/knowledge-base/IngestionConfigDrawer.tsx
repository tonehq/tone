'use client';

import { useEffect, useMemo, useState } from 'react';
import { Cog, Loader2, Save } from 'lucide-react';

import {
  CustomButton,
  CustomDrawer,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import OptionParamsModal from '@/components/knowledge-base/OptionParamsModal';
import {
  getCompatibilityHint,
  getEmbeddingModelMaxTokens,
  hasParams,
  type ParamSection,
} from '@/components/knowledge-base/optionParamSchemas';
import { useCreateIngestionConfig, useUpdateIngestionConfig } from '@/lib/api/ingestion-configs';
import { usePipelineOptions } from '@/lib/api/ingestion-runs';
import type { CreateIngestionConfigPayload, IngestionConfig } from '@/types/ingestionConfig';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface IngestionConfigDrawerProps {
  open: boolean;
  onClose: () => void;
  /** When set, the drawer opens in edit mode and prefills from this config. */
  config?: IngestionConfig | null;
}

interface FormState {
  name: string;
  description: string;
  parser: string;
  parser_config: Record<string, unknown> | null;
  tokeniser: string;
  tokeniser_config: Record<string, unknown> | null;
  embedding_provider: string;
  embedding_config: Record<string, unknown> | null;
  embedding_model: string;
  embedding_dimensions: string;
  vector_store: string;
  vector_store_ref: Record<string, unknown> | null;
}

const EMPTY_FORM: FormState = {
  name: '',
  description: '',
  parser: '',
  parser_config: null,
  tokeniser: '',
  tokeniser_config: null,
  embedding_provider: '',
  embedding_config: null,
  embedding_model: '',
  embedding_dimensions: '',
  vector_store: '',
  vector_store_ref: null,
};

function toOptions(values: string[]): { value: string; label: string }[] {
  return values.map((v) => ({ value: v, label: v }));
}

function formFromConfig(config: IngestionConfig): FormState {
  return {
    name: config.name ?? '',
    description: config.description ?? '',
    parser: config.parser,
    parser_config: config.parser_config ?? null,
    tokeniser: config.tokeniser,
    tokeniser_config: config.tokeniser_config ?? null,
    embedding_provider: config.embedding_provider,
    embedding_config: config.embedding_config ?? null,
    embedding_model: config.embedding_model,
    embedding_dimensions: String(config.embedding_dimensions),
    vector_store: config.vector_store,
    vector_store_ref: config.vector_store_ref ?? null,
  };
}

interface ParamsEditorState {
  section: ParamSection;
  option: string;
  title: string;
  initial: Record<string, unknown> | null;
  apply: (next: Record<string, unknown>) => void;
  // Cross-field context passed through to OptionParamsModal so a param
  // like tokeniser.max_tokens can validate against another field (the
  // picked embedding model). Optional — sections without cross-field
  // validation leave it undefined.
  contextValues?: { embeddingModel?: string };
}

export default function IngestionConfigDrawer({
  open,
  onClose,
  config,
}: IngestionConfigDrawerProps) {
  const isEdit = !!config;
  const { data: options, isLoading: optionsLoading } = usePipelineOptions(open);
  const createMutation = useCreateIngestionConfig();
  const updateMutation = useUpdateIngestionConfig();

  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [paramsEditor, setParamsEditor] = useState<ParamsEditorState | null>(null);

  useEffect(() => {
    if (!open) {
      setForm(EMPTY_FORM);
      setParamsEditor(null);
      return;
    }
    if (config) {
      setForm(formFromConfig(config));
      return;
    }
    if (!options) return;
    setForm((prev) => {
      const anyFilled =
        prev.parser ||
        prev.tokeniser ||
        prev.embedding_provider ||
        prev.embedding_model ||
        prev.embedding_dimensions ||
        prev.vector_store;
      if (anyFilled) return prev;
      return {
        ...EMPTY_FORM,
        parser: options.defaults.parser,
        tokeniser: options.defaults.tokeniser,
        embedding_provider: options.defaults.embedding_provider,
        embedding_model: options.defaults.embedding_model,
        embedding_dimensions: String(options.defaults.embedding_dimensions),
        vector_store: options.defaults.vector_store,
      };
    });
  }, [open, config, options]);

  const parserOptions = useMemo(() => toOptions(options?.parsers ?? []), [options]);
  const tokeniserOptions = useMemo(() => toOptions(options?.tokenisers ?? []), [options]);
  const embedderOptions = useMemo(() => toOptions(options?.embedders ?? []), [options]);
  const vectorStoreOptions = useMemo(() => toOptions(options?.vector_stores ?? []), [options]);

  const dimensionsNumber = Number(form.embedding_dimensions);
  const dimensionsValid =
    form.embedding_dimensions.trim() !== '' &&
    Number.isInteger(dimensionsNumber) &&
    dimensionsNumber > 0;

  const pending = createMutation.isPending || updateMutation.isPending;

  const canSubmit =
    form.name.trim().length > 0 &&
    !!form.parser &&
    !!form.tokeniser &&
    !!form.embedding_provider &&
    form.embedding_model.trim().length > 0 &&
    dimensionsValid &&
    !!form.vector_store &&
    !pending &&
    !optionsLoading;

  const openParamsFor = (section: ParamSection) => {
    if (section === 'parser') {
      setParamsEditor({
        section,
        option: form.parser,
        title: `Parser params — ${form.parser}`,
        initial: form.parser_config,
        apply: (next) =>
          setForm((f) => ({ ...f, parser_config: Object.keys(next).length ? next : null })),
      });
      return;
    }
    if (section === 'tokeniser') {
      setParamsEditor({
        section,
        option: form.tokeniser,
        title: `Tokeniser params — ${form.tokeniser}`,
        initial: form.tokeniser_config,
        contextValues: { embeddingModel: form.embedding_model },
        apply: (next) =>
          setForm((f) => ({ ...f, tokeniser_config: Object.keys(next).length ? next : null })),
      });
      return;
    }
    if (section === 'embedding') {
      setParamsEditor({
        section,
        option: form.embedding_provider,
        title: `Embedding params — ${form.embedding_provider}`,
        initial: form.embedding_config,
        apply: (next) =>
          setForm((f) => ({ ...f, embedding_config: Object.keys(next).length ? next : null })),
      });
      return;
    }
    if (section === 'vector_store') {
      setParamsEditor({
        section,
        option: form.vector_store,
        title: `Vector store params — ${form.vector_store}`,
        initial: form.vector_store_ref,
        apply: (next) =>
          setForm((f) => ({ ...f, vector_store_ref: Object.keys(next).length ? next : null })),
      });
    }
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    const payload: CreateIngestionConfigPayload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      parser: form.parser,
      parser_config: form.parser_config,
      tokeniser: form.tokeniser,
      tokeniser_config: form.tokeniser_config,
      embedding_provider: form.embedding_provider,
      embedding_model: form.embedding_model.trim(),
      embedding_dimensions: dimensionsNumber,
      embedding_config: form.embedding_config,
      vector_store: form.vector_store,
      vector_store_ref: form.vector_store_ref,
    };
    try {
      if (isEdit && config) {
        await updateMutation.mutateAsync({ id: config.id, payload });
        showToast.success('Config updated', 'Your ingestion config has been saved.');
      } else {
        await createMutation.mutateAsync(payload);
        showToast.success('Config created', 'Your ingestion config is ready to use.');
      }
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const paramsCount = (obj: Record<string, unknown> | null): number =>
    obj ? Object.keys(obj).length : 0;

  const configureButton = (
    section: ParamSection,
    option: string,
    params: Record<string, unknown> | null,
  ) => {
    const enabled = hasParams(section, option) && !pending;
    const count = paramsCount(params);
    return (
      // sm:mt-5 (20px) offsets past the SelectInput's Label — the shared
      // Label uses `text-sm leading-none` (14px) with `mb-1.5` (6px) below,
      // so 20px puts the button top exactly on the input trigger's top.
      // Paired with sm:items-start on the parent grid so a present
      // helperText below the input doesn't drag the button down.
      <div className="sm:mt-5">
        <CustomButton
          type="default"
          size="sm"
          disabled={!enabled}
          onClick={() => openParamsFor(section)}
          aria-label={`Configure params for ${option}`}
        >
          <Cog className="mr-1 size-3.5" />
          Configure{count > 0 ? ` (${count})` : ''}
        </CustomButton>
      </div>
    );
  };

  const footer = (
    <div className="flex w-full items-center justify-end gap-2">
      <CustomButton type="default" onClick={onClose} disabled={pending}>
        Cancel
      </CustomButton>
      <CustomButton type="primary" onClick={handleSubmit} disabled={!canSubmit} loading={pending}>
        <Save className="mr-1 size-4" />
        {isEdit ? 'Save changes' : 'Create config'}
      </CustomButton>
    </div>
  );

  return (
    <>
      <CustomDrawer
        open={open}
        onClose={pending ? () => {} : onClose}
        title={isEdit ? 'Edit ingestion config' : 'New ingestion config'}
        description="Save a reusable pipeline recipe (parser, tokeniser, embedder, vector store). Configure per-option params with the Configure buttons."
        side="right"
        width="sm:max-w-2xl"
        footer={footer}
      >
        {optionsLoading ? (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Loading pipeline options…
          </div>
        ) : (
          <div className="flex flex-col gap-5 py-2">
            <div className="grid grid-cols-1 gap-4">
              <TextInput
                name="name"
                label="Name"
                isRequired
                placeholder="e.g. Docling + PGVector 1536"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                disabled={pending}
              />
              <TextAreaField
                name="description"
                label="Description"
                placeholder="Optional notes about this recipe"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                disabled={pending}
                rows={2}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto] sm:items-start">
              <SelectInput
                name="parser"
                label="Parser"
                isRequired
                options={parserOptions}
                value={form.parser || undefined}
                onValueChange={(v) =>
                  setForm((f) => (v === f.parser ? f : { ...f, parser: v, parser_config: null }))
                }
                placeholder="Select a parser"
                disabled={pending}
                helperText={getCompatibilityHint('parser', form.parser)}
              />
              {configureButton('parser', form.parser, form.parser_config)}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto] sm:items-start">
              <SelectInput
                name="embedding_provider"
                label="Embedding provider"
                isRequired
                options={embedderOptions}
                value={form.embedding_provider || undefined}
                onValueChange={(v) =>
                  setForm((f) =>
                    v === f.embedding_provider
                      ? f
                      : { ...f, embedding_provider: v, embedding_config: null },
                  )
                }
                placeholder="Select a provider"
                disabled={pending}
              />
              {configureButton('embedding', form.embedding_provider, form.embedding_config)}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextInput
                name="embedding_model"
                label="Embedding model"
                isRequired
                placeholder="e.g. text-embedding-3-large"
                value={form.embedding_model}
                onChange={(e) => setForm((f) => ({ ...f, embedding_model: e.target.value }))}
                disabled={pending}
                helperText={
                  getEmbeddingModelMaxTokens(form.embedding_model) !== undefined
                    ? `Max input: ${getEmbeddingModelMaxTokens(form.embedding_model)} tokens`
                    : undefined
                }
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
                disabled={pending}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto] sm:items-start">
              <SelectInput
                name="tokeniser"
                label="Tokeniser"
                isRequired
                options={tokeniserOptions}
                value={form.tokeniser || undefined}
                onValueChange={(v) =>
                  setForm((f) =>
                    v === f.tokeniser ? f : { ...f, tokeniser: v, tokeniser_config: null },
                  )
                }
                placeholder="Select a tokeniser"
                disabled={pending}
                helperText={getCompatibilityHint('tokeniser', form.tokeniser)}
              />
              {configureButton('tokeniser', form.tokeniser, form.tokeniser_config)}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto] sm:items-start">
              <SelectInput
                name="vector_store"
                label="Vector store"
                isRequired
                options={vectorStoreOptions}
                value={form.vector_store || undefined}
                onValueChange={(v) =>
                  setForm((f) =>
                    v === f.vector_store ? f : { ...f, vector_store: v, vector_store_ref: null },
                  )
                }
                placeholder="Select a store"
                disabled={pending}
              />
              {configureButton('vector_store', form.vector_store, form.vector_store_ref)}
            </div>
          </div>
        )}
      </CustomDrawer>

      {paramsEditor && (
        <OptionParamsModal
          open={paramsEditor !== null}
          onClose={() => setParamsEditor(null)}
          section={paramsEditor.section}
          option={paramsEditor.option}
          initialValues={paramsEditor.initial}
          onSave={paramsEditor.apply}
          title={paramsEditor.title}
          contextValues={paramsEditor.contextValues}
        />
      )}
    </>
  );
}
