import { fetchFacetedList, fetchFacets, fetchFilterValues } from '@/services/facetedApi';
import type { FacetedListConfig } from '@/types/facetedList';
import type { ModelRow } from '@/types/service';

const BASE = '/services/models';

/**
 * Faceted-list config for the Model Providers table view — one row per model.
 * `name` (model name) is the token-bar search field; Provider and Type (kind)
 * are the drawer facets with server-computed counts.
 */
export const modelsListConfig: FacetedListConfig<ModelRow> = {
  entityName: 'model',
  searchField: { key: 'name', label: 'Name' },
  facetSections: [
    { field: 'provider', label: 'Provider' },
    // Model kinds render in caps (LLM / STT / TTS) in both the token bar and drawer.
    { field: 'kind', label: 'Type', formatValue: (v) => v.toUpperCase() },
  ],
  defaultSort: { field: 'name', order: 'asc' },
  defaultPageSize: 50,
  pageSizeOptions: [25, 50, 100],
  fetchList: (q) => fetchFacetedList<ModelRow>(`${BASE}/list`, q),
  fetchFacets: (q) => fetchFacets(`${BASE}/facets`, q),
  fetchFilterValues: (f) => fetchFilterValues(`${BASE}/filter-values`, f),
};
