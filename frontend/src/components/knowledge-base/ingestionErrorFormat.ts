// Provider errors (OpenAI, etc.) sometimes reach the UI as their raw Python
// string form — e.g. `Error code: 404 - {'error': {'message': '…', 'type': '…',
// 'code': 'model_not_found'}}`. Backend humanization catches most of these at
// ingestion time, but legacy rows and non-ingestion failures can still slip
// through. Sanitize once here so the modal, the Ingestion Runs table, and its
// tooltip all render a short, readable message.

const PROVIDER_HINTS: Array<{ match: RegExp; message: string }> = [
  {
    match: /model_not_found|does not exist or you do not have access/i,
    message:
      'Embedding model not found. Check the model name in the ingestion config (e.g. text-embedding-3-small).',
  },
  {
    match: /invalid_api_key|incorrect api key|invalid api key/i,
    message: 'Invalid API key for the embedding provider. Update the provider key and retry.',
  },
  {
    // OpenAI ("insufficient_quota" / "exceeded your current quota") AND
    // Google/Vertex ("RESOURCE_EXHAUSTED" / "Quota exceeded for
    // …requests_per_minute…" / "submit a quota increase").
    match:
      /insufficient_quota|exceeded your current quota|quota exceeded|resource_?exhausted|quota increase|requests_per_minute|billing/i,
    message: "Embedding provider quota exceeded. Check the provider's quota/billing and retry.",
  },
  {
    match: /rate_?limit|too many requests|\b429\b/i,
    message: 'Embedding provider rate limit hit. Retry in a moment.',
  },
  {
    match: /timed? ?out/i,
    message: 'Embedding provider request timed out. Retry in a moment.',
  },
  {
    match: /unauthorized|\b401\b/i,
    message: 'Provider rejected credentials. Update the API key and retry.',
  },
];

const MAX_LEN = 240;

// Pull the inner `'message': '…'` from a stringified Python dict without
// running JSON.parse — single quotes and `None` make the raw string invalid
// JSON, and swapping quotes globally corrupts messages that themselves
// contain apostrophes (e.g. "The model 'text-embedding-3' does not exist").
function extractProviderMessage(raw: string): string | null {
  const match = raw.match(
    /['"]message['"]\s*:\s*(['"])([\s\S]*?)\1(?=\s*,\s*['"](?:type|code|param)['"]|\s*\})/,
  );
  return match ? match[2].trim() : null;
}

function truncate(text: string): string {
  const first = text.split(/\r?\n/)[0]?.trim() ?? text;
  return first.length > MAX_LEN ? `${first.slice(0, MAX_LEN - 1).trimEnd()}…` : first;
}

/**
 * Convert any ingestion / upload failure string into a short, user-readable
 * one-liner. Returns null for empty / non-string input so callers can render
 * "—" or hide the row.
 */
export function formatIngestionError(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;

  // Known provider failures → a short, safe, actionable message. Checked FIRST
  // regardless of the string's shape, so a raw provider string that reached the
  // row (a legacy row stored before backend humanization, or a non-ingestion
  // failure) is cleaned here too.
  for (const { match, message } of PROVIDER_HINTS) {
    if (match.test(trimmed)) return message;
  }

  // Structured provider dumps — OpenAI "Error code: NNN - {…}", a bare
  // {'error': …} envelope, or a Google/Vertex "ClientError: 4xx … {…}" — carry
  // internal dicts / URLs we must not surface. Pull the inner message only when
  // it is itself clean; otherwise keep a short code prefix or a generic line.
  const looksStructured =
    /Error code:\s*\d+\s*-\s*\{/i.test(trimmed) ||
    /\{\s*['"]error['"]/.test(trimmed) ||
    /RESOURCE_EXHAUSTED|ClientError|[A-Za-z.]+googleapis\.com/i.test(trimmed);

  if (looksStructured) {
    const inner = extractProviderMessage(trimmed);
    if (inner && !/https?:\/\/|googleapis\.com|\{/i.test(inner)) return truncate(inner);
    const codeOnly = trimmed.match(/^([A-Za-z]*Error(?:\s*code)?:\s*\d+)/i);
    if (codeOnly) return codeOnly[1];
    return 'Processing failed due to a provider error. Please retry — if it persists, contact support.';
  }

  return truncate(trimmed);
}
