'use client';

import React from 'react';
import { Layers, Plus, Sparkles } from 'lucide-react';

import CustomButton from '@/components/shared/CustomButton';
import CustomDrawer from '@/components/shared/CustomDrawer';
import TextAreaField from '@/components/shared/TextAreaField';

/** One-tap building blocks for the global prompt drawer. */
const GLOBAL_PROMPT_SNIPPETS = [
  'Be warm, professional, and concise.',
  'Ask only one question at a time and wait for the answer.',
  'Always read key details back to confirm before acting.',
  'Never make up information you have not been given.',
];

interface GlobalPromptDrawerProps {
  open: boolean;
  onClose: () => void;
  value: string;
  /** Called with the full next value; the parent updates its state + dirty flag. */
  onChange: (next: string) => void;
}

const GlobalPromptDrawer: React.FC<GlobalPromptDrawerProps> = ({
  open,
  onClose,
  value,
  onChange,
}) => {
  const appendSnippet = (snippet: string) =>
    onChange(value.trim() ? `${value.trim()}\n${snippet}` : snippet);

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      side="right"
      width="w-[440px] sm:max-w-[440px]"
      title="Global prompt"
      description="Applied to every node, layered above the agent persona and each node's prompt."
      footer={
        <div className="flex justify-end">
          <CustomButton type="primary" size="sm" onClick={onClose}>
            Done
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {/* layered-prompt explainer */}
        <div className="rounded-xl border border-border bg-muted/40 p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
            <Layers className="h-3.5 w-3.5 text-primary" />
            How prompts apply
          </div>
          <p className="mt-1.5 text-[12px] text-muted-foreground">
            In workflow mode the workflow drives the call on its own — the agent&apos;s system
            prompt is not used. Set the call-wide persona and tone here.
          </p>
          <ol className="mt-2.5 space-y-1.5 text-[12px] text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
              <span>
                <span className="font-medium text-foreground/80">Global prompt</span> — this text,
                applied to every node.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/40" />
              <span>
                <span className="font-medium text-foreground/80">Node prompt</span> — what to do at
                each step.
              </span>
            </li>
          </ol>
        </div>

        <TextAreaField
          name="global-prompt"
          label="Global instructions"
          rows={10}
          maxLength={4000}
          placeholder="e.g. Be calm, warm, and concise. Always read details back to confirm before acting."
          helperText="Keep it about call-wide tone and rules — leave step-specific instructions to each node."
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />

        <div className="-mt-1 flex items-center justify-between">
          <span className="text-[11px] text-muted-foreground">
            Use <code className="font-mono text-foreground/70">{'{{variables}}'}</code> to insert
            collected values.
          </span>
          <span className="font-mono text-[11px] text-muted-foreground">{value.length}/4000</span>
        </div>

        {/* quick starters */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            <Sparkles className="h-3 w-3" />
            Quick add
          </div>
          <div className="flex flex-wrap gap-1.5">
            {GLOBAL_PROMPT_SNIPPETS.map((snippet) => (
              <CustomButton
                key={snippet}
                type="default"
                size="xs"
                icon={<Plus className="h-3 w-3" />}
                onClick={() => appendSnippet(snippet)}
                className="!h-auto whitespace-normal py-1 text-left text-[11px] font-normal"
              >
                {snippet}
              </CustomButton>
            ))}
          </div>
        </div>
      </div>
    </CustomDrawer>
  );
};

export default GlobalPromptDrawer;
