'use client';

import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';

import { isKnownPromptVariable, promptVariableLabel } from '@/constants/promptVariables';
import { cn } from '@/utils/cn';

/**
 * Atomic chip rendered for a `variableMention` node. The node is `atom: true`, so the
 * whole chip is a single non-editable unit (one backspace deletes it).
 */
export default function VariableChip({ node, selected }: NodeViewProps) {
  const key = (node.attrs.key as string) ?? '';
  const def = node.attrs.default as string | null | undefined;
  const isCustom = def !== null && def !== undefined;
  const known = isKnownPromptVariable(key);
  const title = isCustom ? `{{${key}}} → "${def}"` : `{{${key}}}`;

  return (
    <NodeViewWrapper as="span" className="inline">
      <span
        contentEditable={false}
        title={title}
        data-variable-chip
        className={cn(
          'mx-0.5 inline-flex select-none items-center gap-0.5 rounded-md border px-1.5 py-px align-baseline text-[0.8125rem] font-medium',
          known
            ? 'border-teal-500/30 bg-teal-500/10 text-teal-700 dark:text-teal-300'
            : 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300',
          selected && 'ring-2 ring-teal-500/40',
        )}
      >
        <span className="opacity-50">{'{'}</span>
        {promptVariableLabel(key)}
        <span className="opacity-50">{'}'}</span>
      </span>
    </NodeViewWrapper>
  );
}
