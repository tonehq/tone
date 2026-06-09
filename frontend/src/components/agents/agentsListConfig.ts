import { fetchFacetedList, fetchFacets, fetchFilterValues } from '@/services/facetedApi';
import type { ApiAgent } from '@/types/agent';
import type { FacetedListConfig } from '@/types/facetedList';

const BASE = '/agent';

/**
 * Faceted-list config for the Agents page. The `status` facet mirrors the list
 * UI (active = has a phone number), computed server-side.
 */
export const agentsListConfig: FacetedListConfig<ApiAgent> = {
  entityName: 'agent',
  searchField: { key: 'name', label: 'Name' },
  facetSections: [
    { field: 'agent_type', label: 'Type', titleCase: true },
    { field: 'status', label: 'Status', titleCase: true },
  ],
  defaultSort: { field: 'updated_at', order: 'desc' },
  defaultPageSize: 10,
  pageSizeOptions: [10, 25, 50, 100],
  fetchList: (q) => fetchFacetedList<ApiAgent>(`${BASE}/list`, q),
  fetchFacets: (q) => fetchFacets(`${BASE}/facets`, q),
  fetchFilterValues: (field) => fetchFilterValues(`${BASE}/filter-values`, field),
};
