import type { FacetSectionConfig, ListFilterParam } from '@/types/facetedList';
import type { SearchToken } from '@/types/components';

/** `in_progress` → `In Progress`. */
export const titleCase = (v: string) =>
  v.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

/** Selected facets → one `in` filter per field with at least one value. */
export function facetsToFilterParams(facets: Record<string, string[]>): ListFilterParam[] {
  const out: ListFilterParam[] = [];
  for (const [field, vals] of Object.entries(facets)) {
    if (vals?.length) out.push({ field, operator: 'in', value: vals });
  }
  return out;
}

/** Selected facets → flat token list for the token search bar. */
export function facetsToTokens(
  facets: Record<string, string[]>,
  sections: FacetSectionConfig[],
): SearchToken[] {
  const out: SearchToken[] = [];
  for (const s of sections) {
    for (const v of facets[s.field] ?? []) out.push({ field: s.field, value: v });
  }
  return out;
}

/** Token list → selected facets (ignores tokens for unknown fields). */
export function tokensToFacets(
  tokens: SearchToken[],
  sections: FacetSectionConfig[],
): Record<string, string[]> {
  const keys = new Set(sections.map((s) => s.field));
  const facets: Record<string, string[]> = {};
  for (const t of tokens) {
    if (!keys.has(t.field)) continue;
    const current = facets[t.field] ?? [];
    if (!current.includes(t.value)) facets[t.field] = [...current, t.value];
  }
  return facets;
}

/** Number of facet fields with at least one selected value. */
export function countFacetFilters(facets: Record<string, string[]>): number {
  return Object.values(facets).reduce((n, v) => n + (v?.length ? 1 : 0), 0);
}
