'use client';

import type { CustomTableSortState, SearchToken, TokenSearchField } from '@/types/components';
import type {
  FacetedFacetsQuery,
  FacetedListConfig,
  FacetedListQuery,
  Facets,
} from '@/types/facetedList';
import { handleApiError } from '@/utils/helpers';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  countFacetFilters,
  facetsToFilterParams,
  facetsToTokens,
  titleCase,
  tokensToFacets,
} from './utils';

export interface UseFacetedListResult<TRow> {
  rows: TRow[];
  total: number;
  listLoading: boolean;
  facets: Facets;
  facetsLoading: boolean;
  page: number;
  pageSize: number;
  pageSizeOptions?: number[];
  /** Selected drawer facets (drawer source of truth). */
  facetSelections: Record<string, string[]>;
  /** Token chips for the search bar (search-field multi-select + facets). */
  tokens: SearchToken[];
  /** Field definitions for the token search bar. */
  tokenFields: TokenSearchField[];
  drawerFilterCount: number;
  hasActiveFilters: boolean;
  setTokens: (tokens: SearchToken[]) => void;
  applyDrawer: (next: Record<string, string[]>) => void;
  clearAll: () => void;
  handleSortChange: (sort: CustomTableSortState | null) => void;
  handlePaginationChange: (page: number, pageSize: number) => void;
  refresh: () => void;
}

/**
 * Server-driven faceted list state: a tokenized search bar (multi-select value
 * dropdowns — a search field plus the enum facets, two-way synced with the
 * filter drawer), server-computed facet counts, sort and pagination. Mirrors
 * the Call History page but is generic and
 * framework-neutral — it calls the entity's `fetch*` fns directly. The facets
 * request depends only on the active facet filters, so searching, sorting or
 * paginating never re-issues `/facets`.
 */
export function useFacetedList<TRow>(config: FacetedListConfig<TRow>): UseFacetedListResult<TRow> {
  const configRef = useRef(config);
  configRef.current = config;

  const [rows, setRows] = useState<TRow[]>([]);
  const [total, setTotal] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [facets, setFacets] = useState<Facets>({});
  const [facetsLoading, setFacetsLoading] = useState(false);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(config.defaultPageSize ?? 10);
  const [sortBy, setSortBy] = useState<string | undefined>(config.defaultSort?.field);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(config.defaultSort?.order ?? 'desc');
  // The search field (e.g. Name) is a multi-select filter shown in the token
  // bar but NOT in the drawer. Kept separate from the drawer facets.
  const [searchSelections, setSearchSelections] = useState<string[]>([]);
  const [facetSelections, setFacetSelections] = useState<Record<string, string[]>>({});

  // Facets are counted from the drawer facets only — the (high-cardinality,
  // exact-match) search field should not skew them.
  const facetFilters = useMemo(() => facetsToFilterParams(facetSelections), [facetSelections]);

  // The list is filtered by both the search-field selections and the facets.
  const listFilters = useMemo(() => {
    const combined: Record<string, string[]> = { ...facetSelections };
    const key = config.searchField?.key;
    if (key && searchSelections.length) combined[key] = searchSelections;
    return facetsToFilterParams(combined);
  }, [facetSelections, searchSelections, config.searchField]);

  const listQuery = useMemo<FacetedListQuery>(() => {
    const q: FacetedListQuery = { page_no: page, page_size: pageSize };
    if (listFilters.length) q.filters = listFilters;
    if (sortBy) {
      q.sort_by = sortBy;
      q.sort_order = sortOrder;
    }
    return q;
  }, [page, pageSize, listFilters, sortBy, sortOrder]);

  // Facet counts depend only on the active facet filters (not search/sort/page).
  const facetsQuery = useMemo<FacetedFacetsQuery>(
    () => (facetFilters.length ? { filters: facetFilters } : {}),
    [facetFilters],
  );

  // Refs so the fetch callbacks stay stable while reading the latest query.
  const listQueryRef = useRef(listQuery);
  listQueryRef.current = listQuery;
  const facetsQueryRef = useRef(facetsQuery);
  facetsQueryRef.current = facetsQuery;

  const listSeq = useRef(0);
  const runListFetch = useCallback((silent = false) => {
    const seq = ++listSeq.current;
    if (!silent) setListLoading(true);
    configRef.current
      .fetchList(listQueryRef.current)
      .then((res) => {
        if (seq !== listSeq.current) return;
        setRows(res.rows);
        setTotal(res.total);
      })
      .catch((err) => {
        if (seq !== listSeq.current) return;
        handleApiError(err);
      })
      .finally(() => {
        if (seq === listSeq.current && !silent) setListLoading(false);
      });
  }, []);

  const facetsSeq = useRef(0);
  const runFacetsFetch = useCallback(() => {
    if (!configRef.current.facetSections.length) return;
    const seq = ++facetsSeq.current;
    setFacetsLoading(true);
    configRef.current
      .fetchFacets(facetsQueryRef.current)
      .then((res) => {
        if (seq === facetsSeq.current) setFacets(res);
      })
      .catch((err) => {
        if (seq === facetsSeq.current) handleApiError(err);
      })
      .finally(() => {
        if (seq === facetsSeq.current) setFacetsLoading(false);
      });
  }, []);

  // List re-fetches on any query change (page/size/search/sort/filters).
  useEffect(() => {
    runListFetch();
  }, [listQuery, runListFetch]);

  // Facets re-fetch only when the active filters change.
  useEffect(() => {
    runFacetsFetch();
  }, [facetsQuery, runFacetsFetch]);

  // Optional polling (e.g. while documents are still processing).
  useEffect(() => {
    const cfg = configRef.current;
    if (!cfg.pollWhile || !cfg.pollWhile(rows)) return;
    const id = setInterval(() => runListFetch(true), cfg.pollIntervalMs ?? 4000);
    return () => clearInterval(id);
  }, [rows, runListFetch]);

  // Token bar fields: the optional search field (a value dropdown backed by
  // /filter-values), then the enum facets.
  const tokenFields = useMemo<TokenSearchField[]>(() => {
    const fields: TokenSearchField[] = [];
    if (config.searchField) {
      const searchKey = config.searchField.key;
      fields.push({
        key: searchKey,
        label: config.searchField.label,
        type: 'enum',
        fetchValues: () => configRef.current.fetchFilterValues(searchKey),
      });
    }
    for (const s of config.facetSections) {
      fields.push({
        key: s.field,
        label: s.label,
        type: 'enum',
        fetchValues: () => configRef.current.fetchFilterValues(s.field),
        formatValue: s.formatValue ?? (s.titleCase ? titleCase : undefined),
      });
    }
    return fields;
  }, [config.searchField, config.facetSections]);

  // Token chips: one per selected search value (multi-select) plus one per
  // selected facet value.
  const tokens = useMemo<SearchToken[]>(() => {
    const out: SearchToken[] = [];
    const key = config.searchField?.key;
    if (key) out.push(...searchSelections.map((value) => ({ field: key, value })));
    out.push(...facetsToTokens(facetSelections, config.facetSections));
    return out;
  }, [config.searchField, config.facetSections, searchSelections, facetSelections]);

  // The Filters drawer badge counts drawer facets only (Name lives in the bar).
  const drawerFilterCount = useMemo(() => countFacetFilters(facetSelections), [facetSelections]);
  const hasActiveFilters = useMemo(
    () => searchSelections.length > 0 || Object.values(facetSelections).some((v) => v.length > 0),
    [searchSelections, facetSelections],
  );

  const setTokens = useCallback((next: SearchToken[]) => {
    const cfg = configRef.current;
    const searchKey = cfg.searchField?.key;
    if (searchKey) {
      // All search-field tokens become the multi-select values (deduped).
      const values: string[] = [];
      for (const t of next) {
        if (t.field === searchKey && !values.includes(t.value)) values.push(t.value);
      }
      setSearchSelections(values);
    }
    setFacetSelections(tokensToFacets(next, cfg.facetSections));
    setPage(1);
  }, []);

  const applyDrawer = useCallback((nextFacets: Record<string, string[]>) => {
    setFacetSelections(nextFacets);
    setPage(1);
  }, []);

  const clearAll = useCallback(() => {
    setSearchSelections([]);
    setFacetSelections({});
    setPage(1);
  }, []);

  const handleSortChange = useCallback((sort: CustomTableSortState | null) => {
    if (sort) {
      setSortBy(sort.field);
      setSortOrder(sort.order);
    } else {
      setSortBy(configRef.current.defaultSort?.field);
      setSortOrder(configRef.current.defaultSort?.order ?? 'desc');
    }
    setPage(1);
  }, []);

  const handlePaginationChange = useCallback((nextPage: number, nextPageSize: number) => {
    setPage(nextPage);
    setPageSize(nextPageSize);
  }, []);

  // Re-fetch both the list and the facet counts. Mutations (create / delete /
  // upload / reprocess) call this, and the facet counts must reflect the change
  // too — the facets effect only fires when the active filters change.
  const refresh = useCallback(() => {
    runListFetch();
    runFacetsFetch();
  }, [runListFetch, runFacetsFetch]);

  return {
    rows,
    total,
    listLoading,
    facets,
    facetsLoading,
    page,
    pageSize,
    pageSizeOptions: config.pageSizeOptions,
    facetSelections,
    tokens,
    tokenFields,
    drawerFilterCount,
    hasActiveFilters,
    setTokens,
    applyDrawer,
    clearAll,
    handleSortChange,
    handlePaginationChange,
    refresh,
  };
}
