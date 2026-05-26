'use client';

import { MessageSquare, Sparkles } from 'lucide-react';
import { useFormContext, useWatch } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { TextAreaField } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { AgentFormState } from '@/types/agent';

export default function PromptStep() {
  const { control } = useFormContext<AgentFormState>();
  const prompt = useWatch({ control, name: 'config.system_prompt_template' }) ?? '';

  return (
    <div className="flex flex-col gap-4">
      <SectionCard
        icon={<MessageSquare className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.violet}
        title="System prompt"
        description="Steers every turn after the call connects. Keep it short and instruction-style."
        action={
          <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
            {prompt.length} chars
          </Badge>
        }
      >
        <TextAreaField
          id="system_prompt_template"
          name="config.system_prompt_template"
          label="Prompt template"
          control={control}
          rows={14}
          className="min-h-[220px] resize-y"
          placeholder={`You are a helpful, concise voice agent for Acme.

Always:
- Greet the caller by name when you know it.
- Confirm appointments back to the caller.
- Hand off to a human if asked.

Never:
- Quote prices you weren't given.
- Promise refunds without checking the policy.`}
          helperText="Markdown is fine. Variables in {{ curly_braces }} are substituted at runtime."
        />
        <p className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <Sparkles className="size-3" />
          Tip: short, instruction-style prompts work best for voice.
        </p>
      </SectionCard>
    </div>
  );
}
