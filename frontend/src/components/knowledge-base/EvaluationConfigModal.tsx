'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  CheckboxField,
  CustomModal,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import {
  useCreateEvaluationConfig,
  useEvalModelOptions,
  useUpdateEvaluationConfig,
} from '@/lib/api/evaluationConfigs';
import type { EvaluationConfig } from '@/types/evaluationConfig';
import { buildEvalModelOptions } from '@/utils/evalFormat';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import {
  EMPTY_CONFIG_FORM,
  EVAL_JUDGE_ENGINES,
  EVAL_METRIC_NAMES,
  type EvalConfigFormState,
} from './evalConfigConstants';

interface EvaluationConfigModalProps {
  open: boolean;
  onClose: () => void;
  config: EvaluationConfig | null; // null = create
}

function formFromConfig(config: EvaluationConfig): EvalConfigFormState {
  return {
    name: config.name,
    description: config.description ?? '',
    judge_model: config.judge_model,
    judge_engine: config.judge_engine,
    judge_prompt: config.judge_prompt ?? '',
    metrics_enabled: config.metrics_enabled ?? [],
    metric_threshold: String(config.metric_threshold ?? 0.7),
    is_default: config.is_default,
  };
}

export default function EvaluationConfigModal({
  open,
  onClose,
  config,
}: EvaluationConfigModalProps) {
  const isEdit = config !== null;
  const [form, setForm] = useState<EvalConfigFormState>(EMPTY_CONFIG_FORM);
  const { data: modelCatalog } = useEvalModelOptions();
  const createMutation = useCreateEvaluationConfig();
  const updateMutation = useUpdateEvaluationConfig();

  useEffect(() => {
    if (open) setForm(config ? formFromConfig(config) : EMPTY_CONFIG_FORM);
  }, [open, config]);

  const modelOptions = useMemo(
    () => buildEvalModelOptions(modelCatalog?.models, form.judge_model),
    [modelCatalog, form.judge_model],
  );

  const engineOptions = useMemo(() => EVAL_JUDGE_ENGINES.map((v) => ({ value: v, label: v })), []);

  const toggleMetric = (name: string, checked: boolean) => {
    setForm((f) => {
      const current = new Set(f.metrics_enabled);
      if (checked) current.add(name);
      else current.delete(name);
      return { ...f, metrics_enabled: Array.from(current) };
    });
  };

  const saving = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = async () => {
    const threshold = Number(form.metric_threshold);
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      judge_model: form.judge_model.trim(),
      judge_engine: form.judge_engine,
      judge_prompt: form.judge_prompt.trim() || null,
      metrics_enabled: form.metrics_enabled,
      metric_threshold: Number.isFinite(threshold) ? threshold : undefined,
      is_default: form.is_default,
    };
    try {
      if (isEdit && config) {
        await updateMutation.mutateAsync({ configId: config.id, payload });
        showToast.success('Config updated', 'Your evaluation config was saved.');
      } else {
        await createMutation.mutateAsync(payload);
        showToast.success('Config created', 'Your evaluation config is ready to run.');
      }
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit evaluation config' : 'New evaluation config'}
      description="A judge recipe — model, optional custom rubric prompt, and metrics — used to re-grade a frozen eval run."
      confirmText={isEdit ? 'Save' : 'Create'}
      confirmLoading={saving}
      confirmDisabled={!form.name.trim() || !form.judge_model.trim()}
      onConfirm={handleSubmit}
      width="sm:max-w-2xl"
    >
      <div className="flex flex-col gap-4">
        <TextInput
          name="name"
          label="Name"
          isRequired
          placeholder="e.g. Strict GPT-4o judge"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          disabled={saving}
        />
        <TextAreaField
          name="description"
          label="Description"
          placeholder="Optional — what this judge setup is for."
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          disabled={saving}
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <SelectInput
            name="judge_model"
            label="Judge model"
            isRequired
            placeholder="Select a model"
            options={modelOptions}
            value={form.judge_model || undefined}
            onValueChange={(v) => setForm((f) => ({ ...f, judge_model: v }))}
            disabled={saving}
          />
          <SelectInput
            name="judge_engine"
            label="Judge engine"
            options={engineOptions}
            value={form.judge_engine}
            onValueChange={(v) => setForm((f) => ({ ...f, judge_engine: v }))}
            disabled={saving}
          />
        </div>
        <TextInput
          name="metric_threshold"
          label="Pass threshold"
          type="number"
          step="0.05"
          min={0.05}
          max={1}
          placeholder="0.7"
          value={form.metric_threshold}
          onChange={(e) => setForm((f) => ({ ...f, metric_threshold: e.target.value }))}
          disabled={saving}
        />
        <div>
          <div className="mb-2 text-sm font-medium text-foreground">Metrics</div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {EVAL_METRIC_NAMES.map((name) => (
              <CheckboxField
                key={name}
                id={`config-metric-${name}`}
                label={name}
                checked={form.metrics_enabled.includes(name)}
                onCheckedChange={(checked) => toggleMetric(name, checked === true)}
                disabled={saving}
              />
            ))}
          </div>
        </div>
        <TextAreaField
          name="judge_prompt"
          label="Custom rubric prompt"
          helperText="Optional. Free-text criteria the judge grades against (runs as the 'correctness' metric). Leave blank to use the built-in metrics only."
          autoResize
          placeholder="e.g. Award a high score only when the answer is fully grounded in the retrieved context and directly answers the question."
          value={form.judge_prompt}
          onChange={(e) => setForm((f) => ({ ...f, judge_prompt: e.target.value }))}
          disabled={saving}
        />
        <CheckboxField
          id="config-is-default"
          label="Set as default judge"
          helperText="Marks this config as the recommended judge (pre-selected when running)."
          checked={form.is_default}
          onCheckedChange={(checked) => setForm((f) => ({ ...f, is_default: checked === true }))}
          disabled={saving}
        />
      </div>
    </CustomModal>
  );
}
