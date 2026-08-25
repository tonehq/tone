'use client';

import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Gauge,
  MinusCircle,
  Pencil,
  Play,
  Sparkles,
  Trash2,
  Upload,
  Wrench,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import SectionCard from '@/components/agents/agent-form/SectionCard';
import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import {
  CustomButton,
  CustomDrawer,
  CustomModal,
  SearchBar,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import {
  useAgentLlmEvalRunDetail,
  useAgentLlmEvalRuns,
  useAgentLlmEvalScenarios,
  useCreateAgentLlmEvalScenario,
  useDeleteAgentLlmEvalScenario,
  useGenerateAgentLlmEvalScenarios,
  useTriggerAgentLlmEvalRun,
  useUpdateAgentLlmEvalScenario,
  useUploadAgentLlmEvalScenariosCsv,
} from '@/lib/api/agentLlmEvals';
import type {
  AgentLlmEvalRunSummary,
  AgentLlmEvalScenario,
  AgentLlmEvalScoredScenario,
  AgentLlmEvalVerdict,
  ScenarioInput,
  ScenarioPatch,
} from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

// ── Shared verdict chip ─────────────────────────────────────────────────

const VERDICT_STYLES: Record<
  AgentLlmEvalVerdict,
  { label: string; className: string; icon: React.ReactNode }
> = {
  PASS: {
    label: 'Pass',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  PARTIAL: {
    label: 'Partial',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <MinusCircle className="size-3" />,
  },
  FAIL: {
    label: 'Fail',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

function VerdictChip({ verdict }: { verdict: AgentLlmEvalVerdict | null | undefined }) {
  const key = (verdict as AgentLlmEvalVerdict) ?? 'FAIL';
  const s = VERDICT_STYLES[key] ?? VERDICT_STYLES.FAIL;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        s.className,
      )}
    >
      {s.icon}
      {verdict ? s.label : '—'}
    </span>
  );
}

// ── Main step ───────────────────────────────────────────────────────────

export default function LlmEvalsStep({ agentId }: { agentId: string | null }) {
  // Create mode: agent isn't saved yet. Render an empty state instead of
  // hiding the section entirely, so users discover the feature and know
  // exactly what to do first.
  if (!agentId) {
    return <LlmEvalsSaveFirstEmptyState />;
  }
  return <LlmEvalsStepBody agentId={agentId} />;
}

function LlmEvalsSaveFirstEmptyState() {
  return (
    <SectionCard
      icon={<Gauge className="size-4" />}
      iconClassName="bg-violet-500/10 text-violet-700 dark:text-violet-400 ring-violet-500/20"
      title="LLM Evals"
      description="Score this agent's LLM output against your scenarios."
    >
      <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-6 text-center">
        <p className="text-sm font-medium text-foreground">Save the agent first</p>
        <p className="mx-auto mt-1 max-w-md text-[13px] text-muted-foreground">
          LLM evals score this agent&apos;s actual system prompt + LLM configuration. Fill in the
          Prompt and Setup (AI model / provider) sections, click{' '}
          <span className="font-medium text-foreground">Create agent</span>, then come back here to
          add scenarios and run your first eval.
        </p>
      </div>
    </SectionCard>
  );
}

function LlmEvalsStepBody({ agentId }: { agentId: string }) {
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<AgentLlmEvalScenario | null>(null);
  const [openCreate, setOpenCreate] = useState(false);
  const [openRun, setOpenRun] = useState(false);
  const [openGenerate, setOpenGenerate] = useState(false);
  const [openRunId, setOpenRunId] = useState<string | null>(null);
  // Delete confirm is routed through the shared ``ConfirmDeleteModal``
  // (Radix-based) so it matches the rest of the app's destructive-action
  // dialogs — instead of a browser-native ``window.confirm``.
  const [pendingDelete, setPendingDelete] = useState<AgentLlmEvalScenario | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const scenariosQuery = useAgentLlmEvalScenarios(agentId, {
    search: search || undefined,
    page_size: 200,
  });
  const runsQuery = useAgentLlmEvalRuns(agentId);
  const uploadCsv = useUploadAgentLlmEvalScenariosCsv(agentId);
  const deleteScenario = useDeleteAgentLlmEvalScenario(agentId);

  const scenarios = scenariosQuery.data?.items ?? [];
  const runs = runsQuery.data ?? [];
  const scenarioCount = scenariosQuery.data?.total ?? scenarios.length;

  const handleCsvPick = async (file: File | null) => {
    if (!file) return;
    try {
      const result = await uploadCsv.mutateAsync(file);
      showToast.success(
        'CSV imported',
        `${result.created} scenario${result.created === 1 ? '' : 's'} added.`,
      );
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleDelete = (scenario: AgentLlmEvalScenario) => {
    setPendingDelete(scenario);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteScenario.mutateAsync(pendingDelete.id);
      showToast.success('Scenario deleted');
      setPendingDelete(null);
    } catch (error) {
      handleApiError(error);
      // Keep the modal open on failure so the user can see the error toast
      // and retry without losing their selection.
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <SectionCard
        icon={<Gauge className="size-4" />}
        iconClassName="bg-violet-500/10 text-violet-700 dark:text-violet-400 ring-violet-500/20"
        title="LLM Evals"
        description="Score this agent's LLM output against your scenarios."
        action={
          <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
            {scenarioCount} scenario{scenarioCount === 1 ? '' : 's'}
          </span>
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          <div className="min-w-[200px] flex-1">
            <SearchBar
              value={search}
              onChange={(v) => setSearch(v)}
              placeholder="Search scenarios…"
            />
          </div>
          <CustomButton
            type="default"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadCsv.isPending}
            icon={<Upload className="size-4" />}
          >
            {uploadCsv.isPending ? 'Uploading…' : 'Import CSV'}
          </CustomButton>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              handleCsvPick(f);
              e.target.value = '';
            }}
          />
          <CustomButton
            type="default"
            onClick={() => setOpenGenerate(true)}
            icon={<Sparkles className="size-4" />}
          >
            Auto-generate
          </CustomButton>
          <CustomButton
            type="default"
            onClick={() => {
              setEditing(null);
              setOpenCreate(true);
            }}
          >
            New Scenario
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={() => setOpenRun(true)}
            disabled={scenarios.length === 0}
            icon={<Play className="size-4" />}
          >
            Run Eval
          </CustomButton>
        </div>

        <ScenariosTable
          scenarios={scenarios}
          isLoading={scenariosQuery.isLoading}
          onEdit={(s) => {
            setEditing(s);
            setOpenCreate(true);
          }}
          onDelete={handleDelete}
        />
      </SectionCard>

      <SectionCard
        icon={<Play className="size-4" />}
        iconClassName="bg-sky-500/10 text-sky-700 dark:text-sky-400 ring-sky-500/20"
        title="Run history"
        description="Every eval batch for this agent, newest first."
        action={
          <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
            {runs.length} run{runs.length === 1 ? '' : 's'}
          </span>
        }
      >
        <RunsTable runs={runs} isLoading={runsQuery.isLoading} onOpen={setOpenRunId} />
      </SectionCard>

      <ScenarioFormModal
        open={openCreate}
        onClose={() => setOpenCreate(false)}
        agentId={agentId}
        scenario={editing}
      />
      <RunEvalModal
        open={openRun}
        onClose={() => setOpenRun(false)}
        agentId={agentId}
        scenarios={scenarios}
      />
      <GenerateScenariosModal
        open={openGenerate}
        onClose={() => setOpenGenerate(false)}
        agentId={agentId}
      />
      <AgentLlmEvalResultsDrawer
        agentId={agentId}
        runId={openRunId}
        open={!!openRunId}
        onClose={() => setOpenRunId(null)}
      />
      <ConfirmDeleteModal
        open={!!pendingDelete}
        onClose={() => {
          if (!deleteScenario.isPending) setPendingDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Delete scenario"
        description="This can’t be undone. Historical eval results for this scenario keep their own snapshot and are not removed."
        impact={
          pendingDelete ? (
            <p className="text-sm text-foreground">
              You’re about to delete{' '}
              <span className="font-medium">{pendingDelete.scenario_key}</span>.
            </p>
          ) : null
        }
        loading={deleteScenario.isPending}
      />
    </div>
  );
}

// ── Scenarios table ─────────────────────────────────────────────────────

function ScenariosTable({
  scenarios,
  isLoading,
  onEdit,
  onDelete,
}: {
  scenarios: AgentLlmEvalScenario[];
  isLoading: boolean;
  onEdit: (s: AgentLlmEvalScenario) => void;
  onDelete: (s: AgentLlmEvalScenario) => void;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading scenarios…
      </div>
    );
  }
  if (scenarios.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        No scenarios yet. Create one, import a CSV, or use Auto-generate.
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Scenario</th>
            <th className="px-3 py-2 text-left">Prompt</th>
            {/* Fixed-width tags + source columns so the Prompt column can
                grow into the leftover space without squeezing them to a
                sliver (which caused tag chips to wrap vertically). */}
            <th className="w-[220px] px-3 py-2 text-left">Tags</th>
            <th className="w-[100px] px-3 py-2 text-left">Source</th>
            <th className="w-[80px] px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => (
            <tr key={s.id} className="border-t border-border/60">
              <td className="px-3 py-2 align-top font-medium text-foreground">{s.scenario_key}</td>
              <td className="w-full px-3 py-2 align-top text-muted-foreground">
                <span
                  className="line-clamp-2 block max-w-[700px] xl:max-w-[900px]"
                  title={s.prompt}
                >
                  {s.prompt}
                </span>
              </td>
              <td className="w-[220px] px-3 py-2 align-top">
                <div className="flex flex-wrap gap-1">
                  {/* Tool-aware chip (Phase 2) — surfaces scenarios whose
                      generator pre-labeled the expected tool call so an
                      operator can see at a glance which rows will run the
                      deterministic ``tool_selection`` metric. */}
                  {s.expected_tools && s.expected_tools.length > 0 ? (
                    <span
                      title={s.expected_tools
                        .map((t) => t.name)
                        .filter(Boolean)
                        .join(', ')}
                      className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary ring-1 ring-primary/20"
                    >
                      <Wrench className="size-2.5" />
                      tool
                    </span>
                  ) : null}
                  {(s.tags ?? []).map((t) => (
                    <span
                      key={t}
                      title={t}
                      className="max-w-[200px] truncate rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-3 py-2 align-top">
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {s.source}
                </span>
              </td>
              <td className="px-3 py-2 align-top">
                <div className="flex items-center justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => onEdit(s)}
                    className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Edit scenario"
                  >
                    <Pencil className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(s)}
                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    aria-label="Delete scenario"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Runs table ──────────────────────────────────────────────────────────

function RunsTable({
  runs,
  isLoading,
  onOpen,
}: {
  runs: AgentLlmEvalRunSummary[];
  isLoading: boolean;
  onOpen: (runId: string) => void;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading runs…
      </div>
    );
  }
  if (runs.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        No runs yet. Click Run Eval to score this agent.
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Run</th>
            <th className="px-3 py-2 text-left">Started</th>
            <th className="px-3 py-2 text-left">Judge</th>
            <th className="px-3 py-2 text-left">Answer Model</th>
            <th className="px-3 py-2 text-left">Triggered</th>
            <th className="px-3 py-2 text-left">Result</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => {
            const summary = r.summary as Record<string, number> | Record<string, never>;
            const total = (summary.total as number) ?? 0;
            const pass = (summary.pass as number) ?? 0;
            const fail = (summary.fail as number) ?? 0;
            const partial = (summary.partial as number) ?? 0;
            const passRate = (summary.pass_rate as number) ?? 0;
            return (
              <tr
                key={r.run_id}
                className="cursor-pointer border-t border-border/60 hover:bg-muted/30"
                onClick={() => onOpen(r.run_id)}
              >
                <td className="px-3 py-2 font-medium text-foreground">#{r.run_number}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {r.started_at ? formatDate(r.started_at) : '—'}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{r.judge_model ?? '—'}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {r.llm_model ?? '—'}
                  {r.llm_provider && (
                    <span className="ml-1 text-[11px] text-muted-foreground/70">
                      · {r.llm_provider}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{r.triggered_by}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="tabular-nums text-foreground">
                      <span className="text-emerald-600">{pass}</span>
                      {partial > 0 && (
                        <>
                          {' / '}
                          <span className="text-amber-600">{partial}</span>
                        </>
                      )}
                      {fail > 0 && (
                        <>
                          {' / '}
                          <span className="text-destructive">{fail}</span>
                        </>
                      )}
                      <span className="text-muted-foreground"> of {total}</span>
                    </span>
                    <span className="text-[11px] tabular-nums text-muted-foreground">
                      {Math.round(passRate * 100)}%
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2 text-right text-muted-foreground">
                  <ChevronRight className="ml-auto size-4" />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Scenario create/edit modal ──────────────────────────────────────────

function ScenarioFormModal({
  open,
  onClose,
  agentId,
  scenario,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenario: AgentLlmEvalScenario | null;
}) {
  const isEdit = !!scenario;
  const create = useCreateAgentLlmEvalScenario(agentId);
  const update = useUpdateAgentLlmEvalScenario(agentId);

  const [key, setKey] = useState('');
  const [prompt, setPrompt] = useState('');
  const [expected, setExpected] = useState('');
  const [persona, setPersona] = useState('');
  const [instruction, setInstruction] = useState('');
  const [tags, setTags] = useState('');

  useEffect(() => {
    if (!open) return;
    setKey(scenario?.scenario_key ?? '');
    setPrompt(scenario?.prompt ?? '');
    setExpected(scenario?.expected_answer ?? '');
    setPersona(scenario?.persona_criteria ?? '');
    setInstruction(scenario?.instruction_criteria ?? '');
    setTags((scenario?.tags ?? []).join(', '));
  }, [open, scenario]);

  const submit = async () => {
    const parsedTags = tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      if (isEdit && scenario) {
        // Only send fields the user actually changed — otherwise a
        // concurrent edit (another tab / user) gets silently reverted.
        // Tags need a stringified-set compare because the DB stores them
        // as a JSONB array whose order we shouldn't rely on for equality.
        const originalTags = (scenario.tags ?? []).slice().sort().join(',');
        const nextTags = parsedTags.slice().sort().join(',');
        const patch: ScenarioPatch = {
          scenario_key: key !== scenario.scenario_key ? key : undefined,
          prompt: prompt !== scenario.prompt ? prompt : undefined,
          expected_answer: expected !== (scenario.expected_answer ?? '') ? expected : undefined,
          persona_criteria: persona !== (scenario.persona_criteria ?? '') ? persona : undefined,
          instruction_criteria:
            instruction !== (scenario.instruction_criteria ?? '') ? instruction : undefined,
          tags: nextTags !== originalTags ? parsedTags : undefined,
        };
        await update.mutateAsync({ scenarioId: scenario.id, patch });
        showToast.success('Scenario updated');
      } else {
        const input: ScenarioInput = {
          scenario_key: key,
          prompt,
          expected_answer: expected || null,
          persona_criteria: persona || null,
          instruction_criteria: instruction || null,
          tags: parsedTags.length ? parsedTags : null,
        };
        await create.mutateAsync(input);
        showToast.success('Scenario created');
      }
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const pending = create.isPending || update.isPending;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit scenario' : 'New scenario'}
      description="A prompt + optional expected answer or judging criteria."
      width="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={pending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            disabled={pending || !key.trim() || !prompt.trim()}
            loading={pending}
          >
            {isEdit ? 'Save changes' : 'Create scenario'}
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <TextInput
          name="scenario_key"
          label="Scenario key"
          placeholder="e.g. simple_room_booking"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          isRequired
        />
        <TextAreaField
          name="prompt"
          label="Prompt"
          placeholder="The user message the agent should respond to"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          isRequired
        />
        <TextAreaField
          name="expected_answer"
          label="Expected answer (optional)"
          placeholder="Used by the correctness metric"
          value={expected}
          onChange={(e) => setExpected(e.target.value)}
          rows={3}
        />
        <TextAreaField
          name="persona_criteria"
          label="Persona criteria (optional)"
          placeholder="How the agent should sound (empathetic, professional, etc.)"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          rows={2}
        />
        <TextAreaField
          name="instruction_criteria"
          label="Instruction criteria (optional)"
          placeholder="What the agent must / must not do"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={2}
        />
        <TextInput
          name="tags"
          label="Tags"
          placeholder="Comma-separated (e.g. booking, happy_path)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
      </div>
    </CustomModal>
  );
}

// ── Run eval modal ──────────────────────────────────────────────────────

function RunEvalModal({
  open,
  onClose,
  agentId,
  scenarios,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenarios: AgentLlmEvalScenario[];
}) {
  const trigger = useTriggerAgentLlmEvalRun(agentId);
  const [judge, setJudge] = useState('');
  const [scope, setScope] = useState<'all' | 'tags'>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const tagOptions = useMemo(() => {
    const all = new Set<string>();
    for (const s of scenarios) for (const t of s.tags ?? []) all.add(t);
    return Array.from(all)
      .sort()
      .map((t) => ({ value: t, label: t }));
  }, [scenarios]);

  useEffect(() => {
    if (!open) {
      setJudge('');
      setScope('all');
      setSelectedTags([]);
    }
  }, [open]);

  const submit = async () => {
    try {
      const result = await trigger.mutateAsync({
        judge_model: judge.trim() || undefined,
        tags: scope === 'tags' && selectedTags.length ? selectedTags : undefined,
      });
      showToast.success(
        'Eval queued',
        `Job #${result.job_id} — results appear once the worker completes.`,
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Run LLM eval"
      description="Enqueues an async job. Refresh in a few seconds to see the run."
      width="max-w-lg"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={trigger.isPending}>
            Cancel
          </CustomButton>
          <CustomButton type="primary" onClick={submit} loading={trigger.isPending}>
            Run eval
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <SelectInput
          name="scope"
          label="Scope"
          value={scope}
          onValueChange={(v) => setScope((v as 'all' | 'tags') ?? 'all')}
          options={[
            { value: 'all', label: `Every scenario (${scenarios.length})` },
            { value: 'tags', label: 'Filter by tag' },
          ]}
        />
        {scope === 'tags' && tagOptions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tagOptions.map((t) => {
              const active = selectedTags.includes(t.value);
              return (
                <button
                  type="button"
                  key={t.value}
                  onClick={() =>
                    setSelectedTags((prev) =>
                      active ? prev.filter((x) => x !== t.value) : [...prev, t.value],
                    )
                  }
                  className={cn(
                    'rounded-full px-2.5 py-1 text-[11px] font-medium ring-1',
                    active
                      ? 'bg-primary text-primary-foreground ring-primary'
                      : 'bg-muted text-muted-foreground ring-border hover:bg-muted/80',
                  )}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
        )}
        <TextInput
          name="judge_model"
          label="Judge model override (optional)"
          placeholder="Leave blank to use the org default"
          value={judge}
          onChange={(e) => setJudge(e.target.value)}
        />
      </div>
    </CustomModal>
  );
}

// ── Generate scenarios modal ────────────────────────────────────────────

// Bound + default match the backend's ``_MAX_COUNT`` in
// ``scenario_generation/strategies/llm.py`` — the server clamps anyway, but
// mirroring the bound here saves a round-trip on a mistyped input.
const GENERATE_DEFAULT_COUNT = 10;
const GENERATE_MAX_COUNT = 50;

function GenerateScenariosModal({
  open,
  onClose,
  agentId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
}) {
  const generate = useGenerateAgentLlmEvalScenarios(agentId);
  const [count, setCount] = useState(String(GENERATE_DEFAULT_COUNT));

  useEffect(() => {
    if (!open) {
      setCount(String(GENERATE_DEFAULT_COUNT));
    }
  }, [open]);

  const submit = async () => {
    const parsedCount = Math.max(
      1,
      Math.min(GENERATE_MAX_COUNT, Number(count) || GENERATE_DEFAULT_COUNT),
    );
    try {
      const result = await generate.mutateAsync({
        // Only one strategy is surfaced in v1. ``noop`` stays on the backend
        // as a safety net + test target.
        strategy: 'llm',
        count: parsedCount,
        // Persist directly — the ``persisted`` list on the response drives
        // the scenarios-table refresh via ``useGenerateAgentLlmEvalScenarios``'s
        // shared invalidator.
        dry_run: false,
      });
      const added = result.persisted.length;
      if (added === 0) {
        showToast.info(
          'Auto-generate',
          result.note ??
            'The generator returned no usable scenarios. Try again, or tweak the agent’s system prompt.',
        );
      } else {
        showToast.success(
          `${added} scenario${added === 1 ? '' : 's'} added`,
          'Generated from the agent’s published system prompt.',
        );
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
      title="Auto-generate scenarios"
      description="Uses the org’s judge model + this agent’s system prompt to draft scenarios and save them."
      width="max-w-lg"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={generate.isPending}>
            Cancel
          </CustomButton>
          <CustomButton type="primary" onClick={submit} loading={generate.isPending}>
            Generate
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <TextInput
          name="count"
          label="How many scenarios?"
          type="number"
          min={1}
          max={GENERATE_MAX_COUNT}
          value={count}
          onChange={(e) => setCount(e.target.value)}
          helperText={`Between 1 and ${GENERATE_MAX_COUNT}. Existing scenarios are never overwritten — duplicates skip.`}
        />
      </div>
    </CustomModal>
  );
}

// ── Results drawer ──────────────────────────────────────────────────────

function AgentLlmEvalResultsDrawer({
  open,
  onClose,
  agentId,
  runId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  runId: string | null;
}) {
  const detailQuery = useAgentLlmEvalRunDetail(open ? agentId : null, open ? runId : null);
  const summary = detailQuery.data?.summary;
  const totals = summary?.summary as Record<string, number> | undefined;

  // Every scenario in a run scores against the SAME snapshotted agent
  // config, so the system prompt is identical row-to-row. Pull it once from
  // the first scored scenario and render it in a single collapsible panel
  // at the top of the drawer — the per-row "System prompt at run time"
  // section is removed to avoid duplicating the same text N times.
  const scenarios = detailQuery.data?.scenarios ?? [];
  const sharedSystemPrompt = scenarios.find((s) => s.system_prompt)?.system_prompt ?? null;

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={summary ? `LLM eval run #${summary.run_number}` : 'LLM eval run'}
      description="Every scored scenario in this batch."
      width="w-[900px] sm:max-w-[95vw]"
    >
      <div className="flex flex-col gap-4">
        {detailQuery.isLoading && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            Loading run…
          </div>
        )}
        {summary && totals && (
          <section className="rounded-lg border border-border/60 bg-card p-3">
            <div className="grid grid-cols-3 gap-3 text-[12.5px] sm:grid-cols-5">
              <SummaryCell label="Score" value={`${totals.pass ?? 0} / ${totals.total ?? 0}`} />
              <SummaryCell
                label="Pass rate"
                value={`${Math.round(((totals.pass_rate ?? 0) as number) * 100)}%`}
              />
              <SummaryCell label="Partial" value={String(totals.partial ?? 0)} />
              <SummaryCell label="Fail" value={String(totals.fail ?? 0)} />
              <SummaryCell label="Judge" value={summary.judge_model ?? '—'} />
            </div>
          </section>
        )}
        {sharedSystemPrompt && <AgentPromptPanel prompt={sharedSystemPrompt} />}
        {detailQuery.data?.scenarios.map((s) => (
          <ScoredScenarioRow key={s.id} scored={s} />
        ))}
        {detailQuery.data && detailQuery.data.scenarios.length === 0 && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            No scored scenarios yet.
          </div>
        )}
      </div>
    </CustomDrawer>
  );
}

function AgentPromptPanel({ prompt }: { prompt: string }) {
  // Expanded by default so users see the full prompt as they enter — it's
  // the most-referenced context in the drawer. Collapsible so long prompts
  // don't push scored scenarios off-screen.
  const [expanded, setExpanded] = useState(true);
  return (
    <section className="rounded-lg border border-border/60 bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
        )}
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Agent system prompt at run time
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/70">
          {expanded ? 'Hide' : 'Show'}
        </span>
      </button>
      {expanded && (
        <div className="max-h-72 overflow-auto whitespace-pre-wrap border-t border-border/60 px-3 py-3 font-mono text-[12px] text-foreground">
          {prompt}
        </div>
      )}
    </section>
  );
}

function SummaryCell({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-medium tabular-nums text-foreground">{value}</div>
    </div>
  );
}

function ScoredScenarioRow({ scored }: { scored: AgentLlmEvalScoredScenario }) {
  const [expanded, setExpanded] = useState(false);
  // Per-scenario "system prompt at run time" section was removed — the
  // prompt is identical across every scored row in a run, so it lives once
  // at the top of the drawer (see ``AgentPromptPanel``).
  return (
    <div className="rounded-md border border-border/60 bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start gap-2 px-3 py-2 text-left"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <VerdictChip verdict={scored.verdict} />
            <span className="text-[11px] text-muted-foreground">{scored.scenario_key}</span>
            {scored.latency_ms != null && (
              <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">
                {scored.latency_ms}ms
              </span>
            )}
          </div>
          <div className="mt-1 line-clamp-2 text-[13px] font-medium text-foreground">
            {scored.prompt}
          </div>
        </div>
      </button>
      {expanded && (
        <div className="grid grid-cols-1 gap-3 border-t border-border/60 px-3 py-3 text-[12.5px] md:grid-cols-2">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Expected
            </div>
            <div className="mt-1 whitespace-pre-wrap text-foreground">
              {scored.expected_answer ?? '—'}
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Actual</div>
            <div className="mt-1 whitespace-pre-wrap text-foreground">
              {scored.actual_answer ?? '—'}
            </div>
          </div>
          {scored.judge_reasoning && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Judge reasoning
              </div>
              <div className="mt-1 whitespace-pre-wrap text-foreground">
                {scored.judge_reasoning}
              </div>
            </div>
          )}
          {/* Tool call intents (Phase 2). Only surfaces when the executor
              actually captured tool_calls — no-tool scenarios stay quiet.
              The deterministic ``tool_selection`` metric verdict + reason
              live under Metrics + Judge reasoning above, so this section
              is inspection-only ("what did the LLM ask to call?"). */}
          {scored.tools_called && scored.tools_called.length > 0 && (
            <div className="md:col-span-2">
              <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
                <Wrench className="size-3" />
                Tool call intents
              </div>
              <div className="mt-1 flex flex-col gap-2">
                {scored.tools_called.map((intent, i) => (
                  <div
                    // Tool call intents are ordered + repeatable (same tool
                    // may be called twice), so index-in-list is the stable
                    // React key; ``name`` alone would collide.
                    key={`${intent.name}-${i}`}
                    className="rounded border border-border/60 bg-muted/40 px-2 py-1.5"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[11.5px] font-medium text-foreground">
                        {intent.name}
                      </span>
                    </div>
                    {intent.arguments && Object.keys(intent.arguments).length > 0 && (
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-all text-[11px] text-muted-foreground">
                        {JSON.stringify(intent.arguments, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {scored.metric_scores && Object.keys(scored.metric_scores).length > 0 && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Metrics
              </div>
              <div className="mt-1 flex flex-wrap gap-3">
                {Object.entries(scored.metric_scores).map(([name, entry]) => (
                  <div key={name} className="rounded bg-muted px-2 py-1 text-[11px]">
                    <span className="font-medium text-foreground">{name}</span>{' '}
                    <span className="tabular-nums text-muted-foreground">
                      {entry?.score != null ? entry.score.toFixed(2) : '—'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(scored.answer_error || scored.judge_error) && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Errors
              </div>
              {scored.answer_error && (
                <div className="mt-1 text-destructive">Answer: {scored.answer_error}</div>
              )}
              {scored.judge_error && (
                <div className="mt-1 text-destructive">Judge: {scored.judge_error}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
