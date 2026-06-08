'use client';

import { MessageSquare, Sparkles, Wand2 } from 'lucide-react';
import { useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { CustomButton, RichPromptEditorField } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { generateSystemPrompt, improveSystemPrompt } from '@/services/aiService';
import type { AgentFormState } from '@/types/agent';
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

export default function PromptStep() {
  const { control, setValue } = useFormContext<AgentFormState>();
  const prompt = useWatch({ control, name: 'config.system_prompt_template' }) ?? '';
  const name = useWatch({ control, name: 'name' }) ?? '';
  const description = useWatch({ control, name: 'description' }) ?? '';
  const agentType = useWatch({ control, name: 'agent_type' }) ?? '';

  const [busy, setBusy] = useState(false);

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
      <SectionCard
        icon={<MessageSquare className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.violet}
        title="System prompt"
        description="Steers every turn after the call connects. Keep it short and instruction-style."
        action={actions}
        className="min-h-0 flex-1"
        bodyClassName="min-h-0 flex-1"
      >
        {/* fill mode: the editor flex-grows and scrolls internally, so only the
            prompt content scrolls — not the whole page. */}
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
    </div>
  );
}
