'use client';

import { useEffect, useMemo, useState } from 'react';

import { CustomButton, CustomDrawer, SearchBar } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { useIngestionRunChunks } from '@/lib/api/ingestion-runs';
import type { IngestionRun, IngestionRunChunk } from '@/types/ingestionRun';

interface IngestionChunksDrawerProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
  ingestionRun: IngestionRun | null;
}

const DEFAULT_PAGE_SIZE = 20;

function RecipeHeader({ run }: { run: IngestionRun }) {
  return (
    <section className="rounded-lg border border-border/60 bg-muted/30 p-3">
      <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Ingestion recipe (run #{run.run_number})
      </h4>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12.5px]">
        <div>
          <dt className="text-[11px] text-muted-foreground">Parser</dt>
          <dd className="mt-0.5 text-foreground">{run.parser}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-muted-foreground">Tokeniser</dt>
          <dd className="mt-0.5 text-foreground">{run.tokeniser}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-[11px] text-muted-foreground">Embedder</dt>
          <dd className="mt-0.5 text-foreground">
            {run.embedding_model}
            <span className="ml-1 text-muted-foreground">
              · {run.embedding_provider} · {run.embedding_dimensions}D
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-[11px] text-muted-foreground">Store</dt>
          <dd className="mt-0.5 text-foreground">{run.vector_store}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-muted-foreground">Chunks</dt>
          <dd className="mt-0.5 tabular-nums text-foreground">
            {run.chunk_count == null ? '—' : run.chunk_count.toLocaleString()}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function ChunkCard({ chunk }: { chunk: IngestionRunChunk }) {
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

export default function IngestionChunksDrawer({
  open,
  onClose,
  uploadId,
  ingestionRun,
}: IngestionChunksDrawerProps) {
  const runId = ingestionRun?.id ?? null;

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');

  // Reset local state whenever the drawer is opened against a different run
  // (or reopened) so page/search don't leak across rows.
  useEffect(() => {
    if (open) {
      setPage(1);
      setSearch('');
    }
  }, [open, runId]);

  const { data, isLoading, isFetching } = useIngestionRunChunks(
    open ? uploadId : null,
    open ? runId : null,
    { page_no: page, page_size: DEFAULT_PAGE_SIZE, search: search || undefined },
  );

  const chunks = data?.data ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / DEFAULT_PAGE_SIZE));
  const canPrev = page > 1;
  const canNext = page < totalPages;

  const showEmpty = !isLoading && chunks.length === 0;
  const isReady = ingestionRun?.status === 'ready';

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={ingestionRun ? `Chunks · ingestion run #${ingestionRun.run_number}` : 'Chunks'}
      description="Every chunk this ingestion run produced, in order."
      width="w-[900px] sm:max-w-[95vw]"
    >
      <div className="flex flex-col gap-4">
        {ingestionRun && <RecipeHeader run={ingestionRun} />}

        {ingestionRun && !isReady && (
          <div className="rounded-md border border-dashed border-border/60 p-4 text-center text-sm text-muted-foreground">
            This run is <span className="font-medium text-foreground">{ingestionRun.status}</span> —
            chunks will appear once ingestion finishes.
          </div>
        )}

        {isReady && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-[240px] flex-1">
                <SearchBar
                  value={search}
                  onSearch={(v) => {
                    setSearch(v);
                    setPage(1);
                  }}
                  placeholder="Search chunk text…"
                />
              </div>
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                {isFetching && !isLoading ? (
                  <span>Refreshing…</span>
                ) : (
                  <span className="tabular-nums">
                    {total.toLocaleString()} chunk{total === 1 ? '' : 's'}
                  </span>
                )}
              </div>
            </div>

            {isLoading && (
              <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
                Loading chunks…
              </div>
            )}

            {showEmpty && (
              <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
                {search ? 'No chunks match your search.' : 'This run produced no chunks.'}
              </div>
            )}

            {!isLoading && chunks.length > 0 && (
              <div className="flex flex-col gap-2">
                {chunks.map((chunk) => (
                  <ChunkCard key={chunk.id} chunk={chunk} />
                ))}
              </div>
            )}

            {total > DEFAULT_PAGE_SIZE && (
              <div className="flex items-center justify-between gap-2 border-t border-border/60 pt-3">
                <span className="text-[11px] tabular-nums text-muted-foreground">
                  Page {page} of {totalPages}
                </span>
                <div className="flex items-center gap-2">
                  <CustomButton
                    type="default"
                    size="sm"
                    disabled={!canPrev || isFetching}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </CustomButton>
                  <CustomButton
                    type="default"
                    size="sm"
                    disabled={!canNext || isFetching}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Next
                  </CustomButton>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </CustomDrawer>
  );
}
