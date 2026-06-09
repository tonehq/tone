import { fetchFacetedList, fetchFacets, fetchFilterValues } from '@/services/facetedApi';
import type { FacetedListConfig } from '@/types/facetedList';
import type { ProviderUsage } from '@/types/service';

const BASE = '/services';

/**
 * Faceted-list config for the Model Providers page. Name is a multi-select
 * (provider display name); Type (service_type) is the drawer facet with counts.
 * The aggregated list caps at 100 cards (backend max) — realistic per org.
 */
export const servicesListConfig: FacetedListConfig<ProviderUsage> = {
  entityName: 'provider',
  searchField: { key: 'name', label: 'Name' },
  facetSections: [{ field: 'service_type', label: 'Type', titleCase: true }],
  defaultPageSize: 100,
  pageSizeOptions: [100],
  fetchList: (q) => fetchFacetedList<ProviderUsage>(`${BASE}/list`, q),
  fetchFacets: (q) => fetchFacets(`${BASE}/facets`, q),
  fetchFilterValues: (field) => fetchFilterValues(`${BASE}/filter-values`, field),
};
