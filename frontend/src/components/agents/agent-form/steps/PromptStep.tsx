'use client';

import { ExternalLink, GitBranch, MessageSquare, Sparkles, Wand2, Workflow } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { useAtomValue, useSetAtom } from 'jotai';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { CustomButton, RichPromptEditorField } from '@/components/shared';
import SearchableSelect from '@/components/shared/SearchableSelect';
import { Badge } from '@/components/ui/badge';
import { fetchWorkflowListAtom, workflowsAtom } from '@/atoms/WorkflowAtom';
import { generateSystemPrompt, improveSystemPrompt } from '@/services/aiService';
import type { AgentFormState } from '@/types/agent';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const PLACEHOLDER = `You are a helpful, concise voice agent for Acme.

Always:
- Greet the caller by name when you know it.
- Confirm appointments back to the caller.
- Hand off to a human if asked.

Never:
- Quote prices you weren't given.
- Promise refunds without checking the policy.`;

const HELPER_TEXT =
  'Type {{ to insert a variable, or use “Insert variable”. Variables are substituted at runtime.';

type Mode = 'prompt' | 'workflow';

const MODES: { key: Mode; label: string; icon: typeof MessageSquare; hint: string }[] = [
  {
    key: 'prompt',
    label: 'Single prompt',
    icon: MessageSquare,
    hint: 'One instruction set drives the whole call',
  },
  {
    key: 'workflow',
    label: 'Workflow',
    icon: Workflow,
    hint: 'A visual conversation pathway drives the call',
  },
];

export default function PromptStep() {
  const { control, setValue } = useFormContext<AgentFormState>();
  const mode = (useWatch({ control, name: 'config.mode' }) ?? 'prompt') as Mode;
  const workflowId = useWatch({ control, name: 'config.workflow_id' }) ?? '';
  const prompt = useWatch({ control, name: 'config.system_prompt_template' }) ?? '';
  const name = useWatch({ control, name: 'name' }) ?? '';
  const description = useWatch({ control, name: 'description' }) ?? '';
  const agentType = useWatch({ control, name: 'agent_type' }) ?? '';

  const [busy, setBusy] = useState(false);

  const { list, loading } = useAtomValue(workflowsAtom);
  const fetchList = useSetAtom(fetchWorkflowListAtom);

  useEffect(() => {
    if (mode === 'workflow' && list.length === 0 && !loading) {
      fetchList().catch(() => {});
    }
  }, [mode, list.length, loading, fetchList]);

  const publishedOptions = useMemo(
    () => list.filter((w) => w.status === 'published').map((w) => ({ value: w.id, label: w.name })),
    [list],
  );

  // If the agent already references a workflow that is no longer published (unpublished or
  // deleted), keep it visible in the dropdown so the assignment isn't silently lost.
  const assignedMissing =
    !!workflowId && !publishedOptions.some((o) => o.value === workflowId) && !loading;
  const wfOptions = useMemo(() => {
    const known = list.find((w) => w.id === workflowId);
    return assignedMissing
      ? [
          ...publishedOptions,
          {
            value: String(workflowId),
            label: `${known?.name ?? 'Assigned workflow'} (unpublished)`,
          },
        ]
      : publishedOptions;
  }, [publishedOptions, assignedMissing, workflowId, list]);

  const needsSelection = mode === 'workflow' && !workflowId;

  const setMode = (m: Mode) => {
    setValue('config.mode', m, { shouldDirty: true });
    if (m === 'prompt') setValue('config.workflow_id', null, { shouldDirty: true });
  };

  const hasContent = prompt.trim().length > 0;

  const applyPrompt = (text: string) => {
    if (!text) return;
    setValue('config.system_prompt_template', text, { shouldDirty: true });
  };

  const handleGenerateOrImprove = async () => {
    setBusy(true);
    try {
      if (hasContent) {
        const text = await improveSystemPrompt({
          text: prompt,
          agent_name: name,
          agent_description: description,
          agent_type: agentType,
        });
        applyPrompt(text);
        showToast.success('Prompt improved');
      } else {
        const text = await generateSystemPrompt({
          agent_name: name,
          agent_description: description,
          agent_type: agentType,
        });
        applyPrompt(text);
        showToast.success('Prompt generated');
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setBusy(false);
    }
  };

  const actions = (
    <div className="flex items-center gap-1.5">
      <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
        {prompt.length} chars
      </Badge>
      <CustomButton
        type="default"
        size="sm"
        loading={busy}
        onClick={handleGenerateOrImprove}
        icon={hasContent ? <Wand2 className="size-3.5" /> : <Sparkles className="size-3.5" />}
        className="text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300"
      >
        {hasContent ? 'Improve' : 'Generate'}
      </CustomButton>
    </div>
  );

  return (
    <div className="flex h-full flex-col gap-4">
      {/* conversation-flow driver toggle */}
      <div className="grid grid-cols-2 gap-2 rounded-xl border border-border bg-muted/30 p-1.5">
        {MODES.map((m) => {
          const Icon = m.icon;
          const active = mode === m.key;
          return (
            <button
              key={m.key}
              type="button"
              aria-pressed={active}
              onClick={() => setMode(m.key)}
              className={cn(
                'flex cursor-pointer items-center gap-3 rounded-lg px-3.5 py-2.5 text-left transition-all',
                active
                  ? 'bg-card shadow-sm ring-1 ring-border'
                  : 'opacity-70 hover:bg-card/60 hover:opacity-100',
              )}
            >
              <span
                className={cn(
                  'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                  active
                    ? 'bg-primary/10 text-primary ring-1 ring-inset ring-primary/20'
                    : 'bg-muted text-muted-foreground',
                )}
              >
                <Icon className="size-4" strokeWidth={2} />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-foreground">{m.label}</span>
                <span className="block truncate text-[11.5px] text-muted-foreground">{m.hint}</span>
              </span>
            </button>
          );
        })}
      </div>

      {mode === 'prompt' ? (
        <SectionCard
          icon={<MessageSquare className="size-3.5" strokeWidth={2.25} />}
          iconClassName={ACCENTS.violet}
          title="System prompt"
          description="Steers every turn after the call connects. Keep it short and instruction-style."
          action={actions}
          className="min-h-0 flex-1"
          bodyClassName="min-h-0 flex-1"
        >
          <RichPromptEditorField
            id="system_prompt_template"
            name="config.system_prompt_template"
            label="Prompt template"
            control={control}
            fill
            placeholder={PLACEHOLDER}
            helperText={HELPER_TEXT}
          />
          <p className="inline-flex shrink-0 items-center gap-1.5 text-[11px] text-muted-foreground">
            <Sparkles className="size-3" />
            Tip: short, instruction-style prompts work best for voice.
          </p>
        </SectionCard>
      ) : (
        <SectionCard
          icon={<Workflow className="size-3.5" strokeWidth={2.25} />}
          iconClassName={ACCENTS.violet}
          title="Assigned workflow"
          description="The selected workflow's flow is sent to the model so it follows the pathway. Only published workflows can be assigned."
        >
          <div className="flex flex-col gap-4">
            <SearchableSelect
              name="config.workflow_id"
              label="Workflow"
              options={wfOptions}
              value={String(workflowId)}
              onValueChange={(v) => setValue('config.workflow_id', v, { shouldDirty: true })}
              loading={loading}
              placeholder={
                publishedOptions.length
                  ? 'Select a published workflow'
                  : 'No published workflows yet'
              }
            />

            {needsSelection && (
              <p className="text-xs font-medium text-destructive">
                Select a published workflow, or switch back to Single prompt — Workflow mode needs
                an assigned workflow.
              </p>
            )}
            {assignedMissing && (
              <p className="text-xs font-medium text-amber-600 dark:text-amber-400">
                The assigned workflow is no longer published. Re-publish it or choose another before
                saving.
              </p>
            )}

            {!loading && publishedOptions.length === 0 && (
              <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4 text-center">
                <span className="mx-auto mb-2 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-muted-foreground ring-1 ring-inset ring-border">
                  <GitBranch className="size-4" />
                </span>
                <p className="text-sm font-medium text-foreground">No published workflows</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Create a workflow and publish it before assigning it here.
                </p>
                <Link href="/workflows" className="mt-3 inline-block">
                  <CustomButton
                    type="default"
                    size="sm"
                    icon={<ExternalLink className="size-3.5" />}
                  >
                    Open Workflows
                  </CustomButton>
                </Link>
              </div>
            )}

            {workflowId && (
              <Link
                href={`/workflows/${workflowId}`}
                className="inline-flex w-fit items-center gap-1.5 text-xs font-medium text-primary hover:underline"
              >
                <ExternalLink className="size-3.5" />
                Edit this workflow
              </Link>
            )}

            <div className="rounded-lg border border-border bg-muted/30 p-3 text-[12px] text-muted-foreground">
              <span className="font-medium text-foreground/80">Note:</span> in workflow mode the
              workflow drives the call on its own — your Single-prompt system prompt is not used.
              Put any persona or tone guidance in the workflow&apos;s global prompt instead.
            </div>
          </div>
        </SectionCard>
      )}
    </div>
  );
}
