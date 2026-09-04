'use client';

import { useEffect, useState } from 'react';

import ChunkCard from '@/components/knowledge-base/ChunkCard';
import IngestionRunRecipe from '@/components/knowledge-base/IngestionRunRecipe';
import { CustomButton, CustomDrawer, SearchBar } from '@/components/shared';
import { useIngestionRunChunks } from '@/lib/api/ingestion-runs';
import type { IngestionRun } from '@/types/ingestionRun';

interface IngestionChunksDrawerProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
  ingestionRun: IngestionRun | null;
}

const DEFAULT_PAGE_SIZE = 20;

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
        {ingestionRun && <IngestionRunRecipe run={ingestionRun} />}

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
