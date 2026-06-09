import type { ReactNode } from 'react';

import type { CustomTableSortState } from '@/types/components';

/** A single facet value with its server-computed count. */
export interface FacetValue {
  value: string;
  count: number;
}

/** Map of facet field → its values+counts, as returned by `/{entity}/facets`. */
export type Facets = Record<string, FacetValue[]>;

/** Config for one faceted (checkbox) filter field. */
export interface FacetSectionConfig {
  field: string;
  label: string;
  /** Title-case the values for display (e.g. `in_progress` → `In Progress`). */
  titleCase?: boolean;
}

/** Generic `{field, operator, value}` filter sent to a list/facets endpoint. */
export interface ListFilterParam {
  field: string;
  operator: string;
  value: string | number | boolean | Array<string | number>;
}

/** Request shape for a faceted list fetch. */
export interface FacetedListQuery {
  page_no: number;
  page_size: number;
  /** Free-text search (mapped to the backend `search` named param). */
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  filters?: ListFilterParam[];
}

/** Request shape for a facets fetch (depends only on the active filters). */
export interface FacetedFacetsQuery {
  filters?: ListFilterParam[];
}

/** A sortable column option (used by card grids that sort via a select). */
export interface SortableColumn {
  key: string;
  label: string;
}

/**
 * Per-entity configuration that drives the whole faceted-list UX. Each page owns
 * the transport (the three `fetch*` fns) so endpoint URLs stay out of the shared
 * layer. Define configs as module-level constants so their identity is stable.
 */
export interface FacetedListConfig<TRow> {
  /** Used in copy / aria (e.g. 'tool'). */
  entityName: string;
  /** Drives the drawer sections AND the token-search facet fields. */
  facetSections: FacetSectionConfig[];
  /**
   * Optional free-text field shown in the token search bar (type `text`). Its
   * token value maps to the backend `search` param so name search is preserved
   * alongside the enum facets.
   */
  searchField?: { key: string; label: string };
  /** Sort options for a card-grid sort select (tables sort via headers instead). */
  sortableColumns?: SortableColumn[];
  defaultSort?: CustomTableSortState | null;
  defaultPageSize?: number;
  pageSizeOptions?: number[];
  fetchList: (params: FacetedListQuery) => Promise<{ rows: TRow[]; total: number }>;
  fetchFacets: (params: FacetedFacetsQuery) => Promise<Facets>;
  fetchFilterValues: (field: string) => Promise<string[]>;
  /** While this returns true for the current rows, the list re-fetches on an interval. */
  pollWhile?: (rows: TRow[]) => boolean;
  /** Poll cadence in ms (default 4000). */
  pollIntervalMs?: number;
}

/** Searchable checkbox-list of facet values (with counts + search). */
export interface FacetOptionListProps {
  field: string;
  label: string;
  titleCase?: boolean;
  values: FacetValue[];
  selected: string[];
  loading: boolean;
  onToggle: (field: string, value: string) => void;
}

/** Collapsible section inside the filter drawer. */
export interface FilterSectionProps {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
}

/** A faceted checkbox section inside the drawer (FilterSection + FacetOptionList). */
export interface FacetSectionProps {
  field: string;
  label: string;
  titleCase?: boolean;
  values: FacetValue[];
  selected: string[];
  loading: boolean;
  onToggle: (field: string, value: string) => void;
}

/** Props for the generalized, config-driven filter drawer. */
export interface FacetFilterDrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  sections: FacetSectionConfig[];
  /** Applied facet selections used to seed the drawer draft. */
  value: Record<string, string[]>;
  facets: Facets;
  facetsLoading: boolean;
  onApply: (next: Record<string, string[]>) => void;
  /** Escape hatch for page-specific sections (e.g. date/range filters). */
  extraSections?: ReactNode;
}
