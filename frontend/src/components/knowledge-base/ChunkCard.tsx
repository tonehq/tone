'use client';

import { useMemo } from 'react';

import { Badge } from '@/components/ui/badge';
import type { IngestionRunChunk } from '@/types/ingestionRun';

export default function ChunkCard({ chunk }: { chunk: IngestionRunChunk }) {
  const metaEntries = useMemo(() => {
    if (!chunk.chunk_metadata || typeof chunk.chunk_metadata !== 'object') return [];
    return Object.entries(chunk.chunk_metadata).filter(([, v]) => v !== null && v !== undefined);
  }, [chunk.chunk_metadata]);

  const charCount = chunk.chunk_text?.length ?? 0;

  return (
    <div className="rounded-md border border-border/60 bg-card">
      <div className="flex items-center justify-between gap-2 border-b border-border/60 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="rounded bg-muted px-2 py-0.5 text-[11px] font-medium tabular-nums text-foreground">
            #{chunk.chunk_index + 1}
          </span>
          <span className="text-[11px] tabular-nums text-muted-foreground">
            {charCount.toLocaleString()} chars
          </span>
        </div>
        {metaEntries.length > 0 && (
          <div className="flex flex-wrap items-center justify-end gap-1">
            {metaEntries.slice(0, 4).map(([k, v]) => (
              <Badge key={k} variant="secondary" className="text-[10px]">
                {k}: {typeof v === 'object' ? JSON.stringify(v) : String(v)}
              </Badge>
            ))}
          </div>
        )}
      </div>
      <div className="px-3 py-3">
        <div className="max-h-96 overflow-y-auto whitespace-pre-wrap break-words rounded bg-muted/40 p-2 font-mono text-[12px] leading-relaxed text-foreground">
          {chunk.chunk_text || '—'}
        </div>
      </div>
    </div>
  );
}
