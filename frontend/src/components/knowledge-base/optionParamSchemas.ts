// Static per-option param schemas for the Ingestion Config drawer.
//
// Each entry maps a section (parser / tokeniser / embedding / vector_store)
// + option slug (e.g. "docling", "recursive_char") to a list of user-editable
// fields. Field keys are chosen to match the corresponding backend class
// constructor kwargs, so the params object saved here is passed through as-is
// to parser_config / tokeniser_config / vector_store_ref JSONB columns and
// flows into get_parser(name, config=...) / get_tokeniser(name, config=...) /
// vector-store factory (backend-side) unchanged.
//
// Options with no meaningful user-facing params are absent from the map — the
// UI disables the "Configure params" button for those.

export type ParamFieldType = 'number' | 'string' | 'boolean';

export interface ParamFieldSpec {
  key: string;
  label: string;
  type: ParamFieldType;
  placeholder?: string;
  helperText?: string;
  min?: number;
  step?: number;
  defaultValue?: string | number | boolean;
}

export type ParamSection = 'parser' | 'tokeniser' | 'embedding' | 'vector_store';

export type OptionParamSchemaMap = Record<ParamSection, Record<string, ParamFieldSpec[]>>;

export const OPTION_PARAM_SCHEMAS: OptionParamSchemaMap = {
  parser: {
    // DoclingReader(page_range=None, ocr=True, tables=True)
    docling: [
      {
        key: 'ocr',
        label: 'Enable OCR',
        type: 'boolean',
        helperText: 'Recognize text from scanned images inside the PDF.',
        defaultValue: true,
      },
      {
        key: 'tables',
        label: 'Extract tables',
        type: 'boolean',
        helperText: 'Detect and parse tabular content.',
        defaultValue: true,
      },
    ],
    // PdfReader / DocxReader / TextReader take no user params.
    // CompositeReader takes nested readers (not JSON-safe) — hidden.
  },
  tokeniser: {
    // RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=200)
    recursive_char: [
      {
        key: 'chunk_size',
        label: 'Chunk size (chars)',
        type: 'number',
        min: 1,
        placeholder: '1000',
        helperText: 'Maximum characters per chunk.',
        defaultValue: 1000,
      },
      {
        key: 'chunk_overlap',
        label: 'Chunk overlap (chars)',
        type: 'number',
        min: 0,
        placeholder: '200',
        helperText: 'Characters repeated between adjacent chunks.',
        defaultValue: 200,
      },
    ],
    // DoclingHybridChunker(max_tokens=512, embedding_model="text-embedding-3-small")
    docling_hybrid: [
      {
        key: 'max_tokens',
        label: 'Max tokens per chunk',
        type: 'number',
        min: 1,
        placeholder: '512',
        defaultValue: 512,
      },
      {
        key: 'embedding_model',
        label: 'Embedding model (for token counting)',
        type: 'string',
        placeholder: 'text-embedding-3-small',
        helperText: 'Model used only to count tokens while chunking.',
      },
    ],
    // _TokenAwareChunkerAdapter(tokenizer_model=None, max_tokens=512, overlap_tokens=64)
    token_aware: [
      {
        key: 'tokenizer_model',
        label: 'Tokenizer model',
        type: 'string',
        placeholder: 'text-embedding-3-small or sentence-transformers/all-MiniLM-L6-v2',
        helperText: 'OpenAI model slug or a HuggingFace model id.',
      },
      {
        key: 'max_tokens',
        label: 'Max tokens per chunk',
        type: 'number',
        min: 1,
        placeholder: '512',
        defaultValue: 512,
      },
      {
        key: 'overlap_tokens',
        label: 'Overlap tokens',
        type: 'number',
        min: 0,
        placeholder: '64',
        defaultValue: 64,
      },
    ],
  },
  embedding: {
    // OpenAIEmbedder(api_key, model, batch_size=100, max_retries=6, tokens_per_minute=900000, dimensions)
    // api_key / model / dimensions live at the top level of the config.
    openai: [
      {
        key: 'batch_size',
        label: 'Batch size',
        type: 'number',
        min: 1,
        placeholder: '100',
        helperText: 'Texts embedded per API call.',
        defaultValue: 100,
      },
      {
        key: 'max_retries',
        label: 'Max retries',
        type: 'number',
        min: 0,
        placeholder: '6',
        defaultValue: 6,
      },
      {
        key: 'tokens_per_minute',
        label: 'Rate limit (tokens/min)',
        type: 'number',
        min: 1,
        placeholder: '900000',
        helperText: 'Client-side rate limit to stay under provider quotas.',
        defaultValue: 900000,
      },
    ],
  },
  vector_store: {
    // pgvector + memory take no user params — they build off the session /
    // process. Left empty so the "Configure params" button stays disabled.
  },
};

/** True when the given (section, option) combination has any user-editable params. */
export function hasParams(section: ParamSection, option: string | null | undefined): boolean {
  if (!option) return false;
  const bucket = OPTION_PARAM_SCHEMAS[section];
  return !!bucket && !!bucket[option] && bucket[option].length > 0;
}

// Shared empty array so the `no schema entry` fallback returns a referentially
// stable reference — callers can safely put the result in a useEffect dep list.
const EMPTY_SPECS: readonly ParamFieldSpec[] = Object.freeze([]);

/** Read the field list for a given (section, option); shared empty array when none. */
export function getFieldSpecs(
  section: ParamSection,
  option: string | null | undefined,
): ParamFieldSpec[] {
  if (!option) return EMPTY_SPECS as ParamFieldSpec[];
  return (OPTION_PARAM_SCHEMAS[section]?.[option] ?? EMPTY_SPECS) as ParamFieldSpec[];
}

// One-line human hint per option, shown under the SelectInput in the create/
// edit drawer so users can see at a glance which file types a parser
// supports (or which parser a tokeniser pairs with). Kept next to the schemas
// so slug → hint mapping lives in one place. Keys match the registry slugs
// from core/services/rag/{parser_factory,tokeniser_factory,embedder_factory,factory}.py.
const OPTION_COMPATIBILITY_HINTS: Partial<Record<ParamSection, Record<string, string>>> = {
  parser: {
    docling: 'Handles PDF, DOCX, PPTX, XLSX, HTML, MD, images (PNG/JPEG/TIFF), CSV',
    pypdf: 'PDF only',
    docx: 'DOCX / DOC only',
    text: 'Plain text, MD, CSV, JSON',
    composite: 'Auto-picks: falls back through docling → pypdf → docx → text (all types)',
  },
  tokeniser: {
    recursive_char: 'Works with any parser; splits by character count',
    docling_hybrid:
      'Best paired with the docling parser — silently falls back to recursive_char otherwise',
    token_aware:
      'Works with any parser; splits by token count using an OpenAI or HuggingFace tokenizer',
  },
};

/** Read the one-line compatibility hint for an option, or undefined when none is defined. */
export function getCompatibilityHint(
  section: ParamSection,
  option: string | null | undefined,
): string | undefined {
  if (!option) return undefined;
  return OPTION_COMPATIBILITY_HINTS[section]?.[option];
}
