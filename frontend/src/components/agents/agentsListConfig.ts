import { fetchFacetedList, fetchFacets, fetchFilterValues } from '@/services/facetedApi';
import type { ApiAgent } from '@/types/agent';
import type { FacetedListConfig } from '@/types/facetedList';

const BASE = '/agent';

/**
 * Faceted-list config for the Agents page. Only Type is faceted — the page's
 * "Status" column is derived from phone-number presence (not `is_active`), so a
 * status facet would be misleading.
 */
export const agentsListConfig: FacetedListConfig<ApiAgent> = {
  entityName: 'agent',
  searchField: { key: 'name', label: 'Name' },
  facetSections: [{ field: 'agent_type', label: 'Type', titleCase: true }],
  defaultSort: { field: 'updated_at', order: 'desc' },
  defaultPageSize: 10,
  pageSizeOptions: [10, 25, 50, 100],
  fetchList: (q) => fetchFacetedList<ApiAgent>(`${BASE}/list`, q),
  fetchFacets: (q) => fetchFacets(`${BASE}/facets`, q),
  fetchFilterValues: (field) => fetchFilterValues(`${BASE}/filter-values`, field),
};
