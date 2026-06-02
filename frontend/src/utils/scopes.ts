/**
 * OAuth scope helpers — mirror of the backend `normalize_scopes` / `validate_scopes` logic so the
 * UI can show scope status without a round-trip. The backend remains the source of truth and
 * enforces scopes on save; these helpers drive the inline `<ScopeStatus>` affordance.
 */

/** Coerce a scope value (list, space/comma string, or null) into a clean de-duped list. */
export const normalizeScopes = (scopes?: string[] | string | null): string[] => {
  if (!scopes) return [];
  const parts = Array.isArray(scopes) ? scopes : scopes.replace(/,/g, ' ').split(/\s+/);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of parts) {
    const scope = String(part).trim();
    if (scope && !seen.has(scope)) {
      seen.add(scope);
      out.push(scope);
    }
  }
  return out;
};

export interface ScopeEvaluation {
  granted: string[];
  required: string[];
  missing: string[];
  ok: boolean;
}

/** Compute whether `granted` scopes cover `required` scopes. */
export const evaluateScopes = (
  granted?: string[] | string | null,
  required?: string[] | string | null,
): ScopeEvaluation => {
  const grantedList = normalizeScopes(granted);
  const requiredList = normalizeScopes(required);
  const grantedSet = new Set(grantedList);
  const missing = requiredList.filter((scope) => !grantedSet.has(scope));
  return { granted: grantedList, required: requiredList, missing, ok: missing.length === 0 };
};

/** Trim an OAuth scope to a short, human-friendly label (drops the long Google URL prefix). */
export const shortScopeLabel = (scope: string): string => {
  const cleaned = scope.replace(/^https:\/\/www\.googleapis\.com\/auth\//, '');
  const segments = cleaned.split('/');
  return segments[segments.length - 1] || cleaned;
};
