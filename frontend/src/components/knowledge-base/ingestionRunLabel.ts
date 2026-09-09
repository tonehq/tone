import type { IngestionRun } from '@/types/ingestionRun';

// Display label for an ingestion run: the user-given name, or a stable
// "Ingestion run N" fallback. Single source so every picker/table stays
// consistent if the wording changes.
export function ingestionRunLabel(run: Pick<IngestionRun, 'name' | 'run_number'>): string {
  return run.name?.trim() || `Ingestion run ${run.run_number}`;
}
