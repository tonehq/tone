import type { IngestionRun } from '@/types/ingestionRun';

export default function IngestionRunRecipe({ run }: { run: IngestionRun }) {
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
