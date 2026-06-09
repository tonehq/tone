import { fetchFacetedList, fetchFacets, fetchFilterValues } from '@/services/facetedApi';
import type { FacetedListConfig } from '@/types/facetedList';
import type { MCPServer } from '@/types/mcp';

const BASE = '/mcp-server';

/**
 * Faceted-list config for the MCP Servers page (a card grid). Sorting is exposed
 * via a select (`sortableColumns`) since there are no table headers, and the
 * grid shows all matching servers (page size 0 → "all" on the backend).
 */
export const mcpListConfig: FacetedListConfig<MCPServer> = {
  entityName: 'MCP server',
  searchField: { key: 'name', label: 'Name' },
  facetSections: [
    { field: 'status', label: 'Status', titleCase: true },
    { field: 'transport_type', label: 'Transport', titleCase: true },
  ],
  sortableColumns: [
    { key: 'name', label: 'Name' },
    { key: 'created_at', label: 'Created' },
    { key: 'updated_at', label: 'Updated' },
  ],
  defaultSort: { field: 'created_at', order: 'desc' },
  defaultPageSize: 0,
  fetchList: (q) => fetchFacetedList<MCPServer>(`${BASE}/list`, q),
  fetchFacets: (q) => fetchFacets(`${BASE}/facets`, q),
  fetchFilterValues: (field) => fetchFilterValues(`${BASE}/filter-values`, field),
};
