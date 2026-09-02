import { Gauge } from 'lucide-react';

import SectionCard from '@/components/agents/agent-form/SectionCard';

export default function LlmEvalsSaveFirstEmptyState() {
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
