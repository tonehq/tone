'use client';

import { forwardRef, useEffect, useImperativeHandle, useState } from 'react';

import type { PromptVariable } from '@/constants/promptVariables';
import { cn } from '@/utils/cn';

export interface SuggestionListRef {
  /** Returns true when the key was consumed (so the editor should not also handle it). */
  onKeyDown: (event: KeyboardEvent) => boolean;
}

interface SuggestionListProps {
  items: PromptVariable[];
  command: (item: PromptVariable) => void;
}

/**
 * Keyboard- and mouse-navigable dropdown for the `{{` variable suggestion. Mounted by
 * the Suggestion utility via ReactRenderer; the editor forwards key events through the
 * imperative `onKeyDown` handle.
 */
const SuggestionList = forwardRef<SuggestionListRef, SuggestionListProps>(
  ({ items, command }, ref) => {
    const [index, setIndex] = useState(0);

    useEffect(() => setIndex(0), [items]);

    const select = (i: number) => {
      const item = items[i];
      if (item) command(item);
    };

    useImperativeHandle(ref, () => ({
      onKeyDown: (event) => {
        if (!items.length) return false;
        if (event.key === 'ArrowUp') {
          setIndex((index + items.length - 1) % items.length);
          return true;
        }
        if (event.key === 'ArrowDown') {
          setIndex((index + 1) % items.length);
          return true;
        }
        if (event.key === 'Enter') {
          select(index);
          return true;
        }
        return false;
      },
    }));

    if (!items.length) {
      return (
        <div className="w-72 rounded-lg border border-border bg-popover px-3 py-2 text-sm text-muted-foreground shadow-md">
          No matching variables
        </div>
      );
    }

    return (
      <div
        role="listbox"
        className="max-h-64 w-72 overflow-auto rounded-lg border border-border bg-popover p-1 shadow-md"
      >
        {items.map((item, i) => (
          <button
            key={item.key}
            type="button"
            role="option"
            aria-selected={i === index}
            onMouseEnter={() => setIndex(i)}
            // mousedown (not click) so the editor doesn't lose its selection first.
            onMouseDown={(e) => {
              e.preventDefault();
              select(i);
            }}
            className={cn(
              'flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-1.5 text-left',
              i === index ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/50',
            )}
          >
            <span className="flex items-baseline gap-1.5 text-sm font-medium">
              {item.label}
              <span className="font-mono text-[11px] text-muted-foreground">{`{{${item.key}}}`}</span>
            </span>
            <span className="text-xs text-muted-foreground">{item.description}</span>
          </button>
        ))}
      </div>
    );
  },
);

SuggestionList.displayName = 'SuggestionList';

export default SuggestionList;
