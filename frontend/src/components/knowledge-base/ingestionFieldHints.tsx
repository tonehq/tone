'use client';

import { Info } from 'lucide-react';

import CustomTooltip from '@/components/shared/CustomTooltip';

export const INGESTION_FIELD_HINTS = {
  parser: 'Reads the raw file and splits it into text sections the AI can process.',
  tokeniser: "Breaks text into smaller chunks so it fits within the AI's context window.",
  embedding_provider:
    'The service that turns your text into numeric vectors used for semantic search.',
  embedding_model:
    'The specific model used to generate embeddings. Determines dimensions and quality.',
  embedding_dimensions: 'Vector size — set automatically by the selected model.',
  vector_store: 'Where embeddings are stored and searched at retrieval time.',
} as const;

export type IngestionFieldKey = keyof typeof INGESTION_FIELD_HINTS;

export function HintIcon({ text }: { text: string }) {
  return (
    <CustomTooltip content={text}>
      <Info className="size-3.5 cursor-help text-muted-foreground" />
    </CustomTooltip>
  );
}
