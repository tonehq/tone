import { fetchFacetedList, fetchFacets, fetchFilterValues } from '@/services/facetedApi';
import type { FacetedListConfig } from '@/types/facetedList';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';

const BASE = '/knowledge-base';

/** Faceted-list config for the Knowledge Base page (filter by status). */
export const knowledgeBaseListConfig: FacetedListConfig<KnowledgeBaseDocument> = {
  entityName: 'document',
  searchField: { key: 'file_name', label: 'Name' },
  facetSections: [{ field: 'status', label: 'Status', titleCase: true }],
  defaultSort: { field: 'updated_at', order: 'desc' },
  defaultPageSize: 10,
  pageSizeOptions: [10, 20, 50],
  // Keep polling while any document is still processing (mirrors the old hook).
  pollWhile: (rows) => rows.some((d) => d.status === 'processing'),
  pollIntervalMs: 4000,
  fetchList: (q) => fetchFacetedList<KnowledgeBaseDocument>(`${BASE}/list`, q),
  fetchFacets: (q) => fetchFacets(`${BASE}/facets`, q),
  fetchFilterValues: (field) => fetchFilterValues(`${BASE}/filter-values`, field),
};
