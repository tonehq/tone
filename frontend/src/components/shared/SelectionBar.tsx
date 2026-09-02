'use client';

import { Trash2, X } from 'lucide-react';

import CustomButton from './CustomButton';
import { cn } from '@/utils/cn';

export interface SelectionBarProps {
  count: number;
  onClear: () => void;
  onDelete: () => void;
  /** Singular noun for the selected-count label, e.g. "tool". */
  singular: string;
  /** Plural noun for the selected-count label, e.g. "tools". */
  plural: string;
}

/**
 * Floating bulk-selection action bar (count + Clear + Delete). Shared across
 * list pages (tools, knowledge base). Animates in when `count > 0`.
 */
export default function SelectionBar({
  count,
  onClear,
  onDelete,
  singular,
  plural,
}: SelectionBarProps) {
  const open = count > 0;
  return (
    <div
      className={cn(
        'pointer-events-none fixed bottom-6 left-1/2 z-40 -translate-x-1/2 transition-all duration-300',
        open ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0',
      )}
      aria-hidden={!open}
    >
      <div className="pointer-events-auto flex items-center gap-3 rounded-2xl border border-border bg-card/95 px-3 py-2 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <span className="ml-2 inline-flex h-6 min-w-[1.5rem] items-center justify-center rounded-full bg-primary/15 px-2 text-xs font-semibold text-primary">
          {count}
        </span>
        <span className="text-sm text-muted-foreground">
          {count === 1 ? `${singular} selected` : `${plural} selected`}
        </span>
        <div className="mx-1 h-5 w-px bg-border" />
        <CustomButton type="text" size="sm" icon={<X className="size-3.5" />} onClick={onClear}>
          Clear
        </CustomButton>
        <CustomButton
          type="danger"
          size="sm"
          icon={<Trash2 className="size-3.5" />}
          onClick={onDelete}
        >
          Delete
        </CustomButton>
      </div>
    </div>
  );
}
