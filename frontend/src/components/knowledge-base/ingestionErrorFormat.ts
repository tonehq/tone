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
    match: /insufficient_quota|exceeded your current quota|billing/i,
    message: 'Embedding provider quota exhausted. Check your billing and retry.',
  },
  {
    match: /rate_?limit|too many requests/i,
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

  // Already-humanized strings don't contain the raw dict marker — pass through.
  const looksStructured =
    /Error code:\s*\d+\s*-\s*\{/i.test(trimmed) || /^\{.*['"]error['"]/.test(trimmed);

  if (looksStructured) {
    for (const { match, message } of PROVIDER_HINTS) {
      if (match.test(trimmed)) return message;
    }
    const inner = extractProviderMessage(trimmed);
    if (inner) return truncate(inner);
    // Unknown structured shape — at least drop the trailing dict dump and
    // keep the "Error code: NNN" prefix if present.
    const codeOnly = trimmed.match(/^(Error code:\s*\d+)/i);
    if (codeOnly) return codeOnly[1];
  }

  return truncate(trimmed);
}
