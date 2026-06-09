import { fetchFacetedList, fetchFacets, fetchFilterValues } from '@/services/facetedApi';
import type { FacetedListConfig } from '@/types/facetedList';
import type { Tool } from '@/types/tool';

const BASE = '/tool';

/** Faceted-list config for the Tools page (filter by type + status). */
export const toolsListConfig: FacetedListConfig<Tool> = {
  entityName: 'tool',
  searchField: { key: 'name', label: 'Name' },
  facetSections: [
    { field: 'tool_type', label: 'Type', titleCase: true },
    { field: 'status', label: 'Status', titleCase: true },
  ],
  defaultSort: { field: 'updated_at', order: 'desc' },
  defaultPageSize: 20,
  pageSizeOptions: [10, 20, 50],
  fetchList: (q) => fetchFacetedList<Tool>(`${BASE}/list`, q),
  fetchFacets: (q) => fetchFacets(`${BASE}/facets`, q),
  fetchFilterValues: (field) => fetchFilterValues(`${BASE}/filter-values`, field),
};
