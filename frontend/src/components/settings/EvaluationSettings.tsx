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
import type { EvalSettings, LlmEvalOrgSettings, RagEvalOrgSettings } from '@/types/evalSettings';
import {
  AGENT_LLM_EVAL_METRIC_NAMES,
  EVAL_JUDGE_ENGINES,
  EVAL_METRIC_NAMES,
} from '@/types/evalSettings';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import { EVAL_FIELD_HINTS, HintIcon } from './evalFieldHints';

// Form state mirrors the API shape but every field is a string for the
// number inputs — coerced back to number on submit. Undefined = "not set,
// let the backend fall through to env / hardcoded default".
interface FormState {
  // RAG (rag_evals) — Level-1 knobs
  auto_run_enabled: boolean | undefined;
  generation_model: string;
  answer_model: string;
  judge_model: string;
  judge_engine: string;
  top_k: string;
  max_context_chars: string;
  metric_threshold: string;
  metrics_enabled: string[] | undefined;
  // Agent-LLM (llm_evals) — Level-2 knobs. Each field is INDEPENDENT of the
  // RAG side (including its own auto_run_enabled). String-typed for number
  // fields so an empty input clears the override — same "empty = fall
  // through" contract as the RAG fields above.
  agent_llm_auto_run_enabled: boolean | undefined;
  agent_llm_judge_model: string;
  agent_llm_judge_engine: string;
  agent_llm_metric_threshold: string;
  agent_llm_metrics_enabled: string[] | undefined;
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
  agent_llm_auto_run_enabled: undefined,
  agent_llm_judge_model: '',
  agent_llm_judge_engine: '',
  agent_llm_metric_threshold: '',
  agent_llm_metrics_enabled: undefined,
};

function formFromServer(server: EvalSettings): FormState {
  const rag: RagEvalOrgSettings = server.rag_evals ?? {};
  const llm: LlmEvalOrgSettings = server.llm_evals ?? {};
  return {
    auto_run_enabled: rag.auto_run_enabled,
    generation_model: rag.generation_model ?? '',
    answer_model: rag.answer_model ?? '',
    judge_model: rag.judge_model ?? '',
    judge_engine: rag.judge_engine ?? '',
    top_k: rag.top_k != null ? String(rag.top_k) : '',
    max_context_chars: rag.max_context_chars != null ? String(rag.max_context_chars) : '',
    metric_threshold: rag.metric_threshold != null ? String(rag.metric_threshold) : '',
    metrics_enabled: rag.metrics_enabled,
    agent_llm_auto_run_enabled: llm.auto_run_enabled,
    agent_llm_judge_model: llm.judge_model ?? '',
    agent_llm_judge_engine: llm.judge_engine ?? '',
    agent_llm_metric_threshold: llm.metric_threshold != null ? String(llm.metric_threshold) : '',
    agent_llm_metrics_enabled: llm.metrics_enabled,
  };
}

// Diff the current form against the last-known server state to decide which
// fields to send. Three outcomes per field:
//   1. Same as server → omit from the sub-patch (avoid churn).
//   2. Non-empty user value → send that value (creates or updates the key).
//   3. Cleared by the user (was previously set on the server) → send `null`
//      so the backend DELETES the key and the resolver falls back to
//      env / hardcoded default. Sending nothing would leave the old
//      value in place, breaking the "revert to fallback" affordance.
// The backend validator + merge accept `null` for every field for exactly
// this purpose — see ``_validate_eval_settings_patch`` in auth_service.py.

type SlotPatch<T> = { [K in keyof T]?: T[K] | null };
type RagPatch = SlotPatch<RagEvalOrgSettings>;
type LlmPatch = SlotPatch<LlmEvalOrgSettings>;
interface SettingsPatch {
  rag_evals?: RagPatch;
  llm_evals?: LlmPatch;
}

function trimmedOrEmpty(value: string): string {
  return value.trim();
}

// Compute the diff for one slot (rag or llm). Returns undefined when nothing
// changed → the caller omits the slot from the outer patch entirely (so
// touching only the LLM fields sends `{llm_evals: {...}}` without
// clobbering unchanged RAG state on the server).
function diffRagSlot(form: FormState, serverRag: RagEvalOrgSettings): RagPatch | undefined {
  const patch: Record<string, unknown> = {};

  // Boolean — three states:
  //   undefined = "user hasn't touched it" (Reset resets to this)
  //   true / false = explicit intent
  // If server has a value and the form is now undefined (Reset), we must
  // send `null` to CLEAR the key on the backend — `undefined` would be
  // stripped by JSON.stringify and the server would silently keep the
  // old value.
  if (form.auto_run_enabled !== serverRag.auto_run_enabled) {
    patch.auto_run_enabled = form.auto_run_enabled === undefined ? null : form.auto_run_enabled;
  }

  const strFields: [keyof RagEvalOrgSettings & string, string][] = [
    ['generation_model', trimmedOrEmpty(form.generation_model)],
    ['answer_model', trimmedOrEmpty(form.answer_model)],
    ['judge_model', trimmedOrEmpty(form.judge_model)],
    ['judge_engine', trimmedOrEmpty(form.judge_engine)],
  ];
  for (const [key, value] of strFields) {
    const current = (serverRag[key] as string | undefined) ?? '';
    if (value === current) continue;
    patch[key] = value === '' ? null : value;
  }

  const numFields: [keyof RagEvalOrgSettings & string, string][] = [
    ['top_k', form.top_k],
    ['max_context_chars', form.max_context_chars],
    ['metric_threshold', form.metric_threshold],
  ];
  for (const [key, raw] of numFields) {
    const trimmed = raw.trim();
    const current = serverRag[key] as number | undefined;
    if (trimmed === '') {
      if (current !== undefined) patch[key] = null;
      continue;
    }
    const n = Number(trimmed);
    if (!Number.isFinite(n)) continue;
    if (n !== current) patch[key] = n;
  }

  const currentMetrics = serverRag.metrics_enabled;
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

  return Object.keys(patch).length > 0 ? (patch as RagPatch) : undefined;
}

function diffLlmSlot(form: FormState, serverLlm: LlmEvalOrgSettings): LlmPatch | undefined {
  const patch: Record<string, unknown> = {};

  // See diffRagSlot for the null-vs-undefined rationale on booleans.
  if (form.agent_llm_auto_run_enabled !== serverLlm.auto_run_enabled) {
    patch.auto_run_enabled =
      form.agent_llm_auto_run_enabled === undefined ? null : form.agent_llm_auto_run_enabled;
  }

  const strFields: [keyof LlmEvalOrgSettings & string, string][] = [
    ['judge_model', trimmedOrEmpty(form.agent_llm_judge_model)],
    ['judge_engine', trimmedOrEmpty(form.agent_llm_judge_engine)],
  ];
  for (const [key, value] of strFields) {
    const current = (serverLlm[key] as string | undefined) ?? '';
    if (value === current) continue;
    patch[key] = value === '' ? null : value;
  }

  const thresholdRaw = form.agent_llm_metric_threshold.trim();
  const serverThreshold = serverLlm.metric_threshold;
  if (thresholdRaw === '') {
    if (serverThreshold !== undefined) patch.metric_threshold = null;
  } else {
    const n = Number(thresholdRaw);
    if (Number.isFinite(n) && n !== serverThreshold) patch.metric_threshold = n;
  }

  const serverMetrics = serverLlm.metrics_enabled;
  const nextMetrics = form.agent_llm_metrics_enabled;
  if (nextMetrics !== undefined) {
    if (nextMetrics.length === 0) {
      if (serverMetrics && serverMetrics.length > 0) patch.metrics_enabled = null;
    } else if (
      !serverMetrics ||
      serverMetrics.length !== nextMetrics.length ||
      !serverMetrics.every((m, i) => m === nextMetrics[i])
    ) {
      patch.metrics_enabled = nextMetrics;
    }
  }

  return Object.keys(patch).length > 0 ? (patch as LlmPatch) : undefined;
}

function patchFromForm(form: FormState, server: EvalSettings): SettingsPatch {
  const patch: SettingsPatch = {};
  const rag = diffRagSlot(form, server.rag_evals ?? {});
  const llm = diffLlmSlot(form, server.llm_evals ?? {});
  if (rag !== undefined) patch.rag_evals = rag;
  if (llm !== undefined) patch.llm_evals = llm;
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
    () => buildModelOptions(serverSettings?.rag_evals?.generation_model),
    [modelCatalog, serverSettings?.rag_evals?.generation_model],
  );
  const answerModelOptions = useMemo(
    () => buildModelOptions(serverSettings?.rag_evals?.answer_model),
    [modelCatalog, serverSettings?.rag_evals?.answer_model],
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

  const agentLlmEnabledMetrics = form.agent_llm_metrics_enabled ?? [];
  const toggleAgentLlmMetric = (name: string, checked: boolean) => {
    setForm((f) => {
      const current = new Set(f.agent_llm_metrics_enabled ?? []);
      if (checked) current.add(name);
      else current.delete(name);
      return { ...f, agent_llm_metrics_enabled: Array.from(current) };
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
          <h1 className="font-display text-[1.75rem] font-semibold tracking-[-0.03em] text-foreground">
            Evaluations
          </h1>
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
              // Backend enforces (0, 1]; a literal 0 hits a 422. Set min to
              // the smallest allowed value so browsers block 0 client-side
              // and the user gets a hint instead of a confusing server error.
              min={0.05}
              max={1}
              placeholder="Default 0.7 (blank = fall back to env default)"
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

        {/* Agent LLM Evals (Level-2) ───────────────────────── */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground">Agent LLM Evals</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Level-2 evals score the agent&apos;s actual LLM output against your scenarios (LLM Evals
            tab on each agent). These knobs are org-wide defaults; a scenario can still override
            them per-run. Independent of the RAG settings above — including its own auto-run toggle.
          </p>
          <div className="mt-4 flex flex-col gap-4">
            {/*
              Disabled by design: the backend accepts + persists
              ``llm_evals.auto_run_enabled``, but no code path reads it yet
              (no ingestion-complete hook, no agent-publish hook). Rendering
              this as a live checkbox would let admins think they've enabled
              something. Re-enable when the auto-trigger ships.
            */}
            <CheckboxField
              id="agent_llm_auto_run_enabled"
              label="Auto-run agent LLM evals (coming soon)"
              helperText="Automated trigger not wired yet. Use Run Eval on the agent's LLM Evals tab for now."
              checked={form.agent_llm_auto_run_enabled === true}
              onCheckedChange={() => {
                /* intentionally no-op — see comment above */
              }}
              disabled
            />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextInput
              name="agent_llm_judge_model"
              label="Judge model"
              placeholder="e.g. gpt-4o (blank = env default)"
              value={form.agent_llm_judge_model}
              onChange={(e) => setForm((f) => ({ ...f, agent_llm_judge_model: e.target.value }))}
              disabled={saving}
            />
            <SelectInput
              name="agent_llm_judge_engine"
              label="Judge engine"
              placeholder="Use default"
              options={judgeEngineOptions}
              value={form.agent_llm_judge_engine || undefined}
              onValueChange={(v) => setForm((f) => ({ ...f, agent_llm_judge_engine: v }))}
              disabled={saving}
            />
            <TextInput
              name="agent_llm_metric_threshold"
              label="Pass threshold"
              type="number"
              step="0.05"
              // See RAG threshold above — backend rejects 0; min prevents
              // the user typing a value the server will 422 on.
              min={0.05}
              max={1}
              placeholder="Default 0.7 (blank = fall back to env default)"
              value={form.agent_llm_metric_threshold}
              onChange={(e) =>
                setForm((f) => ({ ...f, agent_llm_metric_threshold: e.target.value }))
              }
              disabled={saving}
            />
          </div>
          <div className="mt-4">
            <div className="mb-2 text-sm font-medium text-foreground">Metrics enabled</div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {AGENT_LLM_EVAL_METRIC_NAMES.map((name) => (
                <CheckboxField
                  key={name}
                  id={`agent-llm-metric-${name}`}
                  label={name}
                  checked={agentLlmEnabledMetrics.includes(name)}
                  onCheckedChange={(checked) => toggleAgentLlmMetric(name, checked === true)}
                  disabled={saving}
                />
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
