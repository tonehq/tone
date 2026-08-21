'use client';

import { RotateCcw, Save } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import {
  AppLoader,
  CheckboxField,
  CustomButton,
  SelectInput,
  TextInput,
} from '@/components/shared';
import {
  useEvalModelOptions,
  useEvalSettings,
  useUpdateEvalSettings,
} from '@/lib/api/evalSettings';
import type { EvalSettings } from '@/types/evalSettings';
import { EVAL_JUDGE_ENGINES, EVAL_METRIC_NAMES } from '@/types/evalSettings';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import { EVAL_FIELD_HINTS, HintIcon } from './evalFieldHints';

// Form state mirrors the API shape but every field is a string for the
// number inputs — coerced back to number on submit. Undefined = "not set,
// let the backend fall through to env / hardcoded default".
interface FormState {
  auto_run_enabled: boolean | undefined;
  generation_model: string;
  answer_model: string;
  judge_model: string;
  judge_engine: string;
  top_k: string;
  max_context_chars: string;
  metric_threshold: string;
  metrics_enabled: string[] | undefined;
}

const EMPTY_FORM: FormState = {
  auto_run_enabled: undefined,
  generation_model: '',
  answer_model: '',
  judge_model: '',
  judge_engine: '',
  top_k: '',
  max_context_chars: '',
  metric_threshold: '',
  metrics_enabled: undefined,
};

function formFromServer(server: EvalSettings): FormState {
  return {
    auto_run_enabled: server.auto_run_enabled,
    generation_model: server.generation_model ?? '',
    answer_model: server.answer_model ?? '',
    judge_model: server.judge_model ?? '',
    judge_engine: server.judge_engine ?? '',
    top_k: server.top_k != null ? String(server.top_k) : '',
    max_context_chars: server.max_context_chars != null ? String(server.max_context_chars) : '',
    metric_threshold: server.metric_threshold != null ? String(server.metric_threshold) : '',
    metrics_enabled: server.metrics_enabled,
  };
}

// Diff the current form against the last-known server state to decide which
// fields to send. Three outcomes per field:
//   1. Same as server → omit from the patch (avoid churn).
//   2. Non-empty user value → send that value (creates or updates the key).
//   3. Cleared by the user (was previously set on the server) → send `null`
//      so the backend DELETES the key and the resolver falls back to
//      env / hardcoded default. Sending nothing would leave the old
//      value in place, breaking the "revert to fallback" affordance.
// The backend validator + merge accept `null` for every field for exactly
// this purpose — see ``_validate_eval_settings_patch`` in auth_service.py.
type PatchValue<K extends keyof EvalSettings> = EvalSettings[K] | null;
type SettingsPatch = { [K in keyof EvalSettings]?: PatchValue<K> };

function trimmedOrEmpty(value: string): string {
  return value.trim();
}

function patchFromForm(form: FormState, server: EvalSettings): SettingsPatch {
  const patch: SettingsPatch = {};

  // Boolean — undefined means "user hasn't touched it", true/false are
  // explicit intents. There's no "clear" affordance for a checkbox.
  if (form.auto_run_enabled !== server.auto_run_enabled) {
    patch.auto_run_enabled = form.auto_run_enabled;
  }

  const strFields: [keyof FormState & keyof EvalSettings, string][] = [
    ['generation_model', trimmedOrEmpty(form.generation_model)],
    ['answer_model', trimmedOrEmpty(form.answer_model)],
    ['judge_model', trimmedOrEmpty(form.judge_model)],
    ['judge_engine', trimmedOrEmpty(form.judge_engine)],
  ];
  for (const [key, value] of strFields) {
    const current = (server[key] as string | undefined) ?? '';
    if (value === current) continue;
    (patch as Record<string, unknown>)[key] = value === '' ? null : value;
  }

  const numFields: [keyof FormState & keyof EvalSettings, string][] = [
    ['top_k', form.top_k],
    ['max_context_chars', form.max_context_chars],
    ['metric_threshold', form.metric_threshold],
  ];
  for (const [key, raw] of numFields) {
    const trimmed = raw.trim();
    const current = server[key] as number | undefined;
    if (trimmed === '') {
      if (current !== undefined) (patch as Record<string, unknown>)[key] = null;
      continue;
    }
    const n = Number(trimmed);
    if (!Number.isFinite(n)) continue;
    if (n !== current) (patch as Record<string, unknown>)[key] = n;
  }

  // Metrics — undefined = never touched; [] = cleared every checkbox → null;
  // otherwise send the list. Server rejects [] on write, which is why the
  // "empty means clear" contract is important here.
  const currentMetrics = server.metrics_enabled;
  const nextMetrics = form.metrics_enabled;
  if (nextMetrics !== undefined) {
    if (nextMetrics.length === 0) {
      if (currentMetrics && currentMetrics.length > 0) patch.metrics_enabled = null;
    } else if (
      !currentMetrics ||
      currentMetrics.length !== nextMetrics.length ||
      !currentMetrics.every((m, i) => m === nextMetrics[i])
    ) {
      patch.metrics_enabled = nextMetrics;
    }
  }

  return patch;
}

export default function EvaluationSettings() {
  const { data: serverSettings, isLoading } = useEvalSettings();
  const updateMutation = useUpdateEvalSettings();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  // Seed the form once server data arrives (or when a save round-trips).
  useEffect(() => {
    if (serverSettings) {
      setForm(formFromServer(serverSettings));
    }
  }, [serverSettings]);

  const judgeEngineOptions = useMemo(
    () => EVAL_JUDGE_ENGINES.map((v) => ({ value: v, label: v })),
    [],
  );

  // Populate the generation / answer dropdowns from the backend catalog
  // (OpenAI + Gemini LLM models). We ALWAYS prepend a "Use default" row so
  // the user can revert a previously-picked model back to the env fallback —
  // Radix Select can't hold value='' and has no clear affordance, so we use
  // a sentinel and translate it back to '' on write. We ALSO surface the
  // server-persisted value (not the live form value) as a "(unavailable)"
  // row when it isn't in the catalog, so an admin-disabled model is never
  // silently dropped from the options list when the user clicks around.
  const USE_DEFAULT_SENTINEL = '__use_default__';
  const { data: modelCatalog } = useEvalModelOptions();
  const buildModelOptions = (serverValue: string | undefined) => {
    const opts: { value: string; label: string }[] = [
      { value: USE_DEFAULT_SENTINEL, label: 'Use default (env fallback)' },
      ...(modelCatalog?.models ?? []).map((m) => ({
        value: m.name,
        label: `${m.display_name} — ${m.provider_display_name}`,
      })),
    ];
    if (serverValue && !opts.some((o) => o.value === serverValue)) {
      opts.splice(1, 0, { value: serverValue, label: `${serverValue} (unavailable)` });
    }
    return opts;
  };
  const generationModelOptions = useMemo(
    () => buildModelOptions(serverSettings?.generation_model),
    [modelCatalog, serverSettings?.generation_model],
  );
  const answerModelOptions = useMemo(
    () => buildModelOptions(serverSettings?.answer_model),
    [modelCatalog, serverSettings?.answer_model],
  );

  // Translate the Radix-safe sentinel back to '' on write so patchFromForm's
  // "clear → null → env fallback" contract still applies to these dropdowns.
  const onModelSelect = (field: 'generation_model' | 'answer_model', value: string) => {
    const next = value === USE_DEFAULT_SENTINEL ? '' : value;
    setForm((f) => ({ ...f, [field]: next }));
  };
  // Trigger-side value: mirror '' → sentinel so the selected row lights up
  // as "Use default" instead of showing an empty trigger.
  const modelSelectValue = (v: string) => (v ? v : USE_DEFAULT_SENTINEL);

  const enabledMetrics = form.metrics_enabled ?? [];
  const toggleMetric = (name: string, checked: boolean) => {
    setForm((f) => {
      const current = new Set(f.metrics_enabled ?? []);
      if (checked) current.add(name);
      else current.delete(name);
      return { ...f, metrics_enabled: Array.from(current) };
    });
  };

  const handleSave = async () => {
    try {
      const patch = patchFromForm(form, serverSettings ?? {});
      if (Object.keys(patch).length === 0) {
        showToast.success('Eval settings saved', 'No changes to apply.');
        return;
      }
      await updateMutation.mutateAsync(patch);
      showToast.success('Eval settings saved', 'New values apply to the next eval run.');
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleReset = () => {
    // Local reset only — the user still has to click Save to persist. This
    // matches the "empty patch = fall through" contract on the backend: an
    // empty form submits `{}`, which the resolver then interprets per-field.
    setForm(EMPTY_FORM);
  };

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center p-4">
        <AppLoader />
      </div>
    );
  }

  const saving = updateMutation.isPending;

  return (
    <div className="w-full">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Evaluations</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure the models, retrieval, and pass thresholds used to score RAG answers. Unset
            fields fall back to the environment default.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CustomButton
            type="default"
            icon={<RotateCcw className="size-4" />}
            onClick={handleReset}
            disabled={saving}
          >
            Reset
          </CustomButton>
          <CustomButton
            type="primary"
            icon={<Save className="size-4" />}
            onClick={handleSave}
            loading={saving}
          >
            Save
          </CustomButton>
        </div>
      </div>

      <div className="flex flex-col gap-8">
        {/* General ─────────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground">General</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Global behavior for every RAG eval run in this organization.
          </p>
          <div className="mt-4 flex flex-col gap-4">
            <CheckboxField
              id="auto_run_enabled"
              label="Auto-run evals after every ingestion"
              helperText={EVAL_FIELD_HINTS.auto_run_enabled}
              checked={form.auto_run_enabled === true}
              onCheckedChange={(checked) =>
                setForm((f) => ({ ...f, auto_run_enabled: checked === true }))
              }
              disabled={saving}
            />
            <SelectInput
              name="judge_engine"
              label="Judge engine"
              labelHint={<HintIcon text={EVAL_FIELD_HINTS.judge_engine} />}
              placeholder="Use default"
              options={judgeEngineOptions}
              value={form.judge_engine || undefined}
              onValueChange={(v) => setForm((f) => ({ ...f, judge_engine: v }))}
              disabled={saving}
            />
          </div>
        </section>

        {/* Models ──────────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground">Models</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Which LLMs generate, answer, and score. Leave blank to inherit the env default.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <SelectInput
              name="generation_model"
              label="Generation model"
              labelHint={<HintIcon text={EVAL_FIELD_HINTS.generation_model} />}
              placeholder="Use default"
              options={generationModelOptions}
              value={modelSelectValue(form.generation_model)}
              onValueChange={(v) => onModelSelect('generation_model', v)}
              disabled={saving}
            />
            <SelectInput
              name="answer_model"
              label="Answer model"
              labelHint={<HintIcon text={EVAL_FIELD_HINTS.answer_model} />}
              placeholder="Use default"
              options={answerModelOptions}
              value={modelSelectValue(form.answer_model)}
              onValueChange={(v) => onModelSelect('answer_model', v)}
              disabled={saving}
            />
            <TextInput
              name="judge_model"
              label="Judge model"
              labelHint={<HintIcon text={EVAL_FIELD_HINTS.judge_model} />}
              placeholder="e.g. gpt-4o"
              value={form.judge_model}
              onChange={(e) => setForm((f) => ({ ...f, judge_model: e.target.value }))}
              disabled={saving}
            />
          </div>
        </section>

        {/* Retrieval ───────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground">Retrieval</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Controls the context handed to the answer model at scoring time.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextInput
              name="top_k"
              label="Top K chunks"
              labelHint={<HintIcon text={EVAL_FIELD_HINTS.top_k} />}
              type="number"
              min={1}
              max={50}
              placeholder="Default 8"
              value={form.top_k}
              onChange={(e) => setForm((f) => ({ ...f, top_k: e.target.value }))}
              disabled={saving}
            />
            <TextInput
              name="max_context_chars"
              label="Max context chars"
              labelHint={<HintIcon text={EVAL_FIELD_HINTS.max_context_chars} />}
              type="number"
              min={1}
              placeholder="Default 60000"
              value={form.max_context_chars}
              onChange={(e) => setForm((f) => ({ ...f, max_context_chars: e.target.value }))}
              disabled={saving}
            />
          </div>
        </section>

        {/* Scoring ─────────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground">Scoring</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Which metrics run per question and the pass bar applied to each.
          </p>
          <div className="mt-4 flex flex-col gap-4">
            <TextInput
              name="metric_threshold"
              label="Pass threshold"
              labelHint={<HintIcon text={EVAL_FIELD_HINTS.metric_threshold} />}
              type="number"
              step="0.05"
              min={0}
              max={1}
              placeholder="Default 0.7"
              value={form.metric_threshold}
              onChange={(e) => setForm((f) => ({ ...f, metric_threshold: e.target.value }))}
              disabled={saving}
            />
            <div>
              <div className="mb-2 inline-flex items-center gap-1 text-sm font-medium text-foreground">
                Metrics enabled
                <HintIcon text={EVAL_FIELD_HINTS.metrics_enabled} />
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {EVAL_METRIC_NAMES.map((name) => (
                  <CheckboxField
                    key={name}
                    id={`metric-${name}`}
                    label={name}
                    checked={enabledMetrics.includes(name)}
                    onCheckedChange={(checked) => toggleMetric(name, checked === true)}
                    disabled={saving}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
