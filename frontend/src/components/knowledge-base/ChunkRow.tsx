'use client';

import { useId, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

import { CustomButton } from '@/components/shared';

interface ChunkRowProps {
  index: number;
  score: number | null | undefined;
  text: string | null | undefined;
}

export default function ChunkRow({ index, score, text }: ChunkRowProps) {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();
  return (
    <div className="rounded bg-muted/40">
      <CustomButton
        type="text"
        fullWidth
        onClick={() => setExpanded((v) => !v)}
        className="h-auto justify-start gap-2 rounded-none bg-transparent px-2 py-1.5 text-left font-sans text-[11px] font-normal text-muted-foreground hover:bg-transparent hover:text-muted-foreground"
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        {expanded ? (
          <ChevronDown className="size-3.5 shrink-0" />
        ) : (
          <ChevronRight className="size-3.5 shrink-0" />
        )}
        <span>chunk {index + 1}</span>
        {typeof score === 'number' && (
          <span className="tabular-nums">score {score.toFixed(3)}</span>
        )}
      </CustomButton>
      {expanded && (
        <div
          id={panelId}
          className="whitespace-pre-wrap border-t border-border/60 px-2 py-2 font-mono text-[12px] text-foreground"
        >
          {text ?? '—'}
        </div>
      )}
    </div>
  );
}
