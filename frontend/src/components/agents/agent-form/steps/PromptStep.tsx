'use client';

import { CircleAlert, MessageSquare, Sparkles, Wand2, Workflow } from 'lucide-react';
import { useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import AgentWorkflowsSection from '@/components/agents/agent-workflows/AgentWorkflowsSection';
import { useAgentEditor } from '@/components/agents/AgentEditorContext';
import { CustomButton, RichPromptEditorField } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
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
    label: 'Prompt',
    icon: MessageSquare,
    hint: 'A single instruction set steers the whole call.',
  },
  {
    key: 'workflow',
    label: 'Workflow',
    icon: Workflow,
    hint: 'A visual pathway drives the conversation.',
  },
];

/**
 * The agent's "Prompt" section — the single place a conversation is authored.
 * A Prompt/Workflow toggle picks how the call is driven: either the system
 * prompt editor, or the agent's workflows (agent-scoped, one copy per version).
 */
export default function PromptStep() {
  const { control, setValue } = useFormContext<AgentFormState>();
  const { detail, agentId, agentType } = useAgentEditor();

  const mode = (useWatch({ control, name: 'config.mode' }) ?? 'prompt') as Mode;
  const workflowId = useWatch({ control, name: 'config.workflow_id' }) ?? '';
  const prompt = useWatch({ control, name: 'config.system_prompt_template' }) ?? '';
  const name = useWatch({ control, name: 'name' }) ?? '';
  const description = useWatch({ control, name: 'description' }) ?? '';

  const [busy, setBusy] = useState(false);

  const basePath = agentId ? `/agents/edit/${agentType}/${agentId}` : `/agents/create/${agentType}`;

  // `config` is the version currently loaded in the editor; its `version` is
  // always present (non-optional), unlike the optional `versions` list.
  const viewedVersion = detail?.config?.version ?? null;
  const versionLabel = viewedVersion != null ? `v${viewedVersion}` : 'this agent';

  const needsSelection = mode === 'workflow' && !workflowId;

  const setMode = (m: Mode) => {
    setValue('config.mode', m, { shouldDirty: true });
    // Prompt mode never keeps a workflow assignment; workflow mode waits for the
    // user to pick one from the cards below.
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
    <div className="flex h-full flex-col gap-3">
      {/* ── Conversation-driver hero (compact) ───────────────────────────── */}
      <section className="relative shrink-0 overflow-hidden rounded-xl border border-border/80 bg-gradient-to-br from-primary/[0.05] via-transparent to-transparent px-3.5 py-3 ring-1 ring-inset ring-border/40">
        <div className="mb-2 flex flex-wrap items-baseline gap-x-2">
          <h2 className="text-[13px] font-semibold tracking-tight text-foreground">
            How {versionLabel} drives conversations
          </h2>
          <p className="text-[11.5px] text-muted-foreground">
            Pick one way to run the call — each version keeps its own setup.
          </p>
        </div>

        <div role="group" aria-label="Conversation mode" className="grid grid-cols-2 gap-2">
          {MODES.map((m) => {
            const Icon = m.icon;
            const active = mode === m.key;
            return (
              <CustomButton
                key={m.key}
                type="text"
                aria-pressed={active}
                onClick={() => setMode(m.key)}
                className={cn(
                  'h-auto min-h-0 items-center justify-start gap-2.5 whitespace-normal rounded-lg border px-3 py-2 text-left font-normal transition-all',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
                  active
                    ? 'border-primary/40 bg-card shadow-sm hover:bg-card'
                    : 'border-border/60 opacity-80 hover:border-foreground/20 hover:bg-card/60 hover:opacity-100',
                )}
              >
                <span
                  className={cn(
                    'inline-flex size-7 shrink-0 items-center justify-center rounded-md ring-1 ring-inset transition-colors',
                    active
                      ? 'bg-primary/10 text-primary ring-primary/20'
                      : 'bg-muted text-muted-foreground ring-border/60',
                  )}
                >
                  <Icon className="size-3.5" strokeWidth={2} />
                </span>
                <span className="min-w-0">
                  <span className="block text-[12.5px] font-semibold leading-tight text-foreground">
                    {m.label}
                  </span>
                  <span className="block truncate text-[11px] leading-tight text-muted-foreground">
                    {m.hint}
                  </span>
                </span>
              </CustomButton>
            );
          })}
        </div>
      </section>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
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
        <div className="flex shrink-0 flex-col gap-3">
          {needsSelection && agentId && (
            <p className="flex items-center gap-1.5 text-[12px] font-medium text-amber-700 dark:text-amber-300">
              <CircleAlert className="size-3.5 shrink-0" />
              Pick a workflow below to run {versionLabel}, or switch back to Prompt.
            </p>
          )}
          <AgentWorkflowsSection
            agentId={agentId}
            basePath={basePath}
            viewedVersion={viewedVersion}
          />
        </div>
      )}
    </div>
  );
}
