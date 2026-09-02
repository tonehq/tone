'use client';

import callLogsAtom, {
  callFacetsAtom,
  callMetricsSummaryAtom,
  fetchCallFacets,
  fetchCallLogs,
  fetchCallMetricsSummary,
} from '@/atoms/CallLogAtom';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import {
  CustomButton,
  CustomPopover,
  CustomTable,
  PhoneNumberDisplay,
  TokenSearchBar,
} from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { getFilterValues } from '@/services/callLogService';
import type {
  CallFacetsParams,
  CallLogFilterParam,
  CallLogQueryParams,
  CallLogRow,
} from '@/types/callLog';
import type {
  CustomTableColumn,
  CustomTableSortState,
  SearchToken,
  TokenSearchField,
} from '@/types/components';
import { formatDuration, formatTimestamp, getBrowserTimeZone } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { useAtom } from 'jotai';
import { BarChart3, Columns3, Phone, SlidersHorizontal, X } from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import CallHistoryMetricsStrip from './CallHistoryMetricsStrip';
import { getDisplayDurationSeconds } from './callDuration';
import { getCallStatusLabel, getCallStatusTone } from './callStatus';
import { formatAudioMs } from './metrics/utils';
import CallHistoryFilterDrawer, {
  countDrawerFilters,
  createEmptyFilterState,
  DRAWER_FACET_SECTIONS,
  DRAWER_FIELD_KEYS,
  isLatencyActive,
  titleCase,
  type CallFilterState,
} from './filter-drawer';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const BROWSER_TZ = getBrowserTimeZone();

// The token search mirrors the drawer's facets (all live in the drawer now).
// Selections sync both ways through filterState.facets, so a value chosen in the
// drawer shows up as a chip here and vice versa. Values autocomplete from
// /filter-values (lazy-loaded + cached by TokenSearchBar).
const TOKEN_FIELDS: TokenSearchField[] = DRAWER_FACET_SECTIONS.map((s) => ({
  key: s.field,
  label: s.label,
  type: 'enum',
  fetchValues: () => getFilterValues(s.field).then((r) => r.values),
  formatValue: s.titleCase ? titleCase : undefined,
}));

const formatSeconds = (v: number | null) => (v == null ? '-' : `${v.toFixed(2)}s`);
const formatCount = (v: number | null) => (v == null ? '-' : v.toLocaleString());

// Single source of truth for the column-visibility popover. Columns are
// grouped so the user can toggle a whole section in one click. `agent_name`
// and `actions` are intentionally absent: the Agent and Quick View columns are
// always rendered and not exposed as togglable.
const COLUMN_GROUPS: Array<{
  name: string;
  columns: Array<{ key: string; label: string }>;
}> = [
  {
    name: 'Call History',
    columns: [
      { key: 'status', label: 'Status' },
      { key: 'duration_seconds', label: 'Duration' },
      { key: 'from_number', label: 'From' },
      { key: 'to_number', label: 'To' },
      { key: 'provider_call_id', label: 'Call SID' },
      { key: 'started_at', label: 'Started At' },
      { key: 'ended_at', label: 'Ended At' },
    ],
  },
  {
    name: 'Call Metrics',
    columns: [
      { key: 'avg_latency', label: 'Avg Latency' },
      { key: 'llm_tokens', label: 'LLM Tokens' },
      { key: 'tts_chars', label: 'TTS Chars' },
      { key: 'stt_audio', label: 'STT Audio' },
      { key: 'turns', label: 'Turns' },
    ],
  },
];
const ALL_COLUMN_KEYS = COLUMN_GROUPS.flatMap((g) => g.columns.map((c) => c.key));
/** Columns that are pinned to the table regardless of popover selection. */
const ALWAYS_VISIBLE_COLUMN_KEYS = new Set<string>(['agent_name']);

function summarizeMetrics(metrics: CallLogRow['metrics']) {
  if (!metrics) return null;
  const latencies = metrics.user_bot_latency.map((l) => l.latency);
  const avgLatencyS = latencies.length
    ? latencies.reduce((s, v) => s + v, 0) / latencies.length
    : null;
  const totalTokens = metrics.llm_usage.reduce((s, u) => s + u.total_tokens, 0);
  const totalChars = metrics.tts_usage.reduce((s, u) => s + u.characters, 0);
  // Defensive shim — `stt_usage` is null/missing on legacy rows persisted
  // before the column existed.
  const sttUsage = Array.isArray(metrics.stt_usage) ? metrics.stt_usage : [];
  const totalSttAudioMs = sttUsage.reduce((s, u) => s + u.audio_ms, 0);
  // Count real user→bot exchanges when per-turn data is available — matches
  // the Turns stat card on the metrics detail page. Falls back to the raw
  // pipecat turn count for legacy calls without `turn_metrics`.
  const turnMetrics = Array.isArray(metrics.turn_metrics) ? metrics.turn_metrics : [];
  const turnCount =
    turnMetrics.length > 0
      ? turnMetrics.filter((t) => t.end_to_end != null).length
      : metrics.turns.length;
  return { avgLatencyS, totalTokens, totalChars, totalSttAudioMs, turnCount };
}

// When `agentId` is set the component runs in "embedded" (agent-scoped) mode:
// a non-removable `agent_id` filter is injected into every request, and the
// redundant Agent column + Agent facet are hidden. Absent it, behavior is
// identical to the global Call History page.
const CallHistory: React.FC<{ agentId?: string }> = ({ agentId }) => {
  const router = useRouter();
  const pathname = usePathname();
  const [data] = useAtom(callLogsAtom);
  const [, doFetchCallLogs] = useAtom(fetchCallLogs);
  const [facetsState] = useAtom(callFacetsAtom);
  const [, doFetchCallFacets] = useAtom(fetchCallFacets);
  const [metricsSummaryState] = useAtom(callMetricsSummaryAtom);
  const [, doFetchCallMetricsSummary] = useAtom(fetchCallMetricsSummary);
  const [metricsStripVisible, setMetricsStripVisible] = useState(false);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Single source of truth: date range, facets (toolbar + drawer), turns, latency.
  const [filterState, setFilterState] = useState<CallFilterState>(() =>
    createEmptyFilterState(BROWSER_TZ),
  );
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

  // Column visibility — sentinel 'all' means every column is shown. Drafts live
  // inside the popover until the user clicks Apply.
  const [visibleColumnKeys, setVisibleColumnKeys] = useState<Set<string> | 'all'>('all');
  const [columnFilterOpen, setColumnFilterOpen] = useState(false);
  const [draftColumnKeys, setDraftColumnKeys] = useState<Set<string>>(
    () => new Set(ALL_COLUMN_KEYS),
  );

  useEffect(() => {
    if (columnFilterOpen) {
      setDraftColumnKeys(
        visibleColumnKeys === 'all' ? new Set(ALL_COLUMN_KEYS) : new Set(visibleColumnKeys),
      );
    }
  }, [columnFilterOpen, visibleColumnKeys]);

  const toggleDraftColumn = useCallback((key: string) => {
    setDraftColumnKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleDraftGroup = useCallback((groupKeys: string[]) => {
    setDraftColumnKeys((prev) => {
      const next = new Set(prev);
      const allOn = groupKeys.every((k) => next.has(k));
      if (allOn) groupKeys.forEach((k) => next.delete(k));
      else groupKeys.forEach((k) => next.add(k));
      return next;
    });
  }, []);

  const handleResetColumns = useCallback(() => {
    setDraftColumnKeys(new Set(ALL_COLUMN_KEYS));
  }, []);

  const handleApplyColumns = useCallback(() => {
    setVisibleColumnKeys(
      draftColumnKeys.size === ALL_COLUMN_KEYS.length ? 'all' : new Set(draftColumnKeys),
    );
    setColumnFilterOpen(false);
  }, [draftColumnKeys]);

  const hiddenColumnCount =
    visibleColumnKeys === 'all' ? 0 : ALL_COLUMN_KEYS.length - visibleColumnKeys.size;

  // The Filters button badge reflects only the drawer-managed filters; the
  // date range, status and agent live in the toolbar with their own indicators.
  const drawerFilterCount = useMemo(() => countDrawerFilters(filterState), [filterState]);

  // Embedded mode hides the Agent facet (rows are all the same agent, and it
  // must not offer a way to view another agent). These drive the token search,
  // the drawer, and the two-way token↔facet sync so they stay consistent.
  const facetSections = useMemo(
    () =>
      agentId
        ? DRAWER_FACET_SECTIONS.filter((s) => s.field !== 'agent_name')
        : DRAWER_FACET_SECTIONS,
    [agentId],
  );
  const tokenFields = useMemo<TokenSearchField[]>(
    () => (agentId ? TOKEN_FIELDS.filter((f) => f.key !== 'agent_name') : TOKEN_FIELDS),
    [agentId],
  );

  // Filter predicates derived purely from filterState. All facet selections
  // (toolbar status/agent + drawer direction/channel/models, kept in sync with
  // the token search) become one `in` filter per field; turns/latency become
  // `between`. Kept separate from pagination/sort so the facets request below
  // stays stable across page and sort changes (it doesn't depend on either).
  const filters = useMemo<CallLogFilterParam[]>(() => {
    const out: CallLogFilterParam[] = [];

    // Embedded mode: scope every request (list, facets, metrics) to this agent.
    // Server-enforced and combined with the org scope, so it holds even if the
    // client is tampered with. `agent_id` maps to `Agent.id` in the backend
    // filter map (distinct from the display-only `agent_name` facet).
    if (agentId) out.push({ field: 'agent_id', operator: 'in', value: [agentId] });

    for (const [field, vals] of Object.entries(filterState.facets)) {
      if (vals?.length) out.push({ field, operator: 'in', value: vals });
    }

    const minN = parseInt(filterState.minTurns, 10);
    const maxN = parseInt(filterState.maxTurns, 10);
    const hasMin = Number.isFinite(minN);
    const hasMax = Number.isFinite(maxN);
    if (hasMin || hasMax) {
      // NULL turn_count (no metrics row) is excluded by BETWEEN, matching the
      // intent "calls with N turns in range".
      out.push({
        field: 'turn_count',
        operator: 'between',
        value: [hasMin ? minN : 0, hasMax ? maxN : 999999],
      });
    }

    if (isLatencyActive(filterState.latency)) {
      out.push({
        field: 'avg_latency_seconds',
        operator: 'between',
        value: [filterState.latency[0], filterState.latency[1]],
      });
    }

    return out;
  }, [filterState, agentId]);

  // Build the list query: filters + date range (start/end) + pagination + sort.
  const params = useMemo<CallLogQueryParams>(() => {
    const q: CallLogQueryParams = { page_no: page, page_size: pageSize };
    if (filters.length > 0) q.filters = filters;
    if (filterState.dateRange.start) q.start_date_time = filterState.dateRange.start;
    if (filterState.dateRange.end) q.end_date_time = filterState.dateRange.end;
    if (sortBy) {
      q.sort_by = sortBy;
      q.sort_order = sortOrder;
    }
    return q;
  }, [
    page,
    pageSize,
    filters,
    filterState.dateRange.start,
    filterState.dateRange.end,
    sortBy,
    sortOrder,
  ]);

  // Facet counts use the same filter scope (the backend excludes each facet's
  // own field) so the toolbar Status/Agent dropdowns and the drawer stay live.
  // Depends only on date range + filters — not page/sort — so paginating or
  // sorting doesn't re-issue the facets request.
  const facetParams = useMemo<CallFacetsParams>(
    () => ({
      start_date_time: filterState.dateRange.start ?? undefined,
      end_date_time: filterState.dateRange.end ?? undefined,
      filters: filters.length > 0 ? filters : undefined,
    }),
    [filterState.dateRange.start, filterState.dateRange.end, filters],
  );

  const refresh = useCallback(async () => {
    try {
      await doFetchCallLogs(params);
    } catch (error) {
      handleApiError(error);
    }
  }, [doFetchCallLogs, params]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    doFetchCallFacets(facetParams).catch(handleApiError);
  }, [facetParams, doFetchCallFacets]);

  const handleSortChange = useCallback((sort: CustomTableSortState | null) => {
    if (sort) {
      setSortBy(sort.field);
      setSortOrder(sort.order);
    } else {
      setSortBy(undefined);
      setSortOrder('desc');
    }
    setPage(1);
  }, []);

  const handlePaginationChange = useCallback((nextPage: number, nextPageSize: number) => {
    setPage(nextPage);
    setPageSize(nextPageSize);
  }, []);

  // The token search reflects the drawer facets (direction/channel/models) as
  // chips; editing chips writes back to those facet fields (two-way sync), while
  // leaving the toolbar-only status/agent facets untouched.
  const searchTokens = useMemo<SearchToken[]>(() => {
    const out: SearchToken[] = [];
    for (const s of facetSections) {
      for (const v of filterState.facets[s.field] ?? []) out.push({ field: s.field, value: v });
    }
    return out;
  }, [filterState.facets, facetSections]);

  const handleSearchTokensChange = useCallback((next: SearchToken[]) => {
    setFilterState((prev) => {
      const facets = { ...prev.facets };
      // Rebuild only the drawer-owned fields from the token list.
      for (const s of DRAWER_FACET_SECTIONS) delete facets[s.field];
      for (const t of next) {
        if (!DRAWER_FIELD_KEYS.has(t.field)) continue;
        const current = facets[t.field] ?? [];
        if (!current.includes(t.value)) facets[t.field] = [...current, t.value];
      }
      return { ...prev, facets };
    });
    setPage(1);
  }, []);

  const handleApplyFilters = useCallback((next: CallFilterState) => {
    setFilterState(next);
    setPage(1);
  }, []);

  const hasActiveFilters = useMemo(
    () =>
      !!(filterState.dateRange.start && filterState.dateRange.end) ||
      Object.values(filterState.facets).some((v) => v?.length) ||
      filterState.minTurns.trim() !== '' ||
      filterState.maxTurns.trim() !== '' ||
      isLatencyActive(filterState.latency),
    [filterState],
  );

  const handleClearAll = useCallback(() => {
    setFilterState((prev) => createEmptyFilterState(prev.dateRange.timeZone));
    setPage(1);
  }, []);

  // Reuses the exact filter scope the table is showing (facetParams already
  // omits pagination + sort), so the aggregates the strip renders can never
  // disagree with the visible row set. Show first, fetch second — the strip
  // renders its own loading state.
  const handleShowMetrics = useCallback(() => {
    setMetricsStripVisible(true);
    doFetchCallMetricsSummary({
      start_date_time: facetParams.start_date_time,
      end_date_time: facetParams.end_date_time,
      filters: facetParams.filters,
    }).catch(handleApiError);
  }, [facetParams, doFetchCallMetricsSummary]);

  const handleHideMetrics = useCallback(() => setMetricsStripVisible(false), []);

  // Sticky class pins the agent column on the left while the inner columns
  // scroll horizontally.
  const STICKY_LEFT = 'sticky left-0 z-[1] bg-card border-r border-border';

  const columns: CustomTableColumn<CallLogRow>[] = [
    {
      key: 'agent_name',
      title: 'Agent',
      dataIndex: 'agent_name',
      className: STICKY_LEFT,
      render: (_value, record) => (
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium">{record.agent_name || '-'}</span>
          <AgentTypeBadge agentType={record.agent_type} />
        </div>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      dataIndex: 'status',
      sorter: true,
      render: (value) => {
        const status = (value as string) || 'unknown';
        return <Badge className={getCallStatusTone(status)}>{getCallStatusLabel(status)}</Badge>;
      },
    },
    {
      key: 'duration_seconds',
      title: 'Duration',
      dataIndex: 'duration_seconds',
      sorter: true,
      // Display the recording's actual length when available so the cell
      // matches the audio player on the detail page; fall back to the raw
      // duration_seconds when the call has no recording. Sort still uses
      // duration_seconds (the indexed column) so the order is approximate
      // — the two values usually differ by only a few seconds.
      render: (_value, record) => formatDuration(getDisplayDurationSeconds(record)),
    },
    {
      key: 'from_number',
      title: 'From',
      dataIndex: 'from_number',
      render: (value) => {
        const num = value as string | null;
        return num ? <PhoneNumberDisplay phoneNumber={num} flagSize="sm" /> : '-';
      },
    },
    {
      key: 'to_number',
      title: 'To',
      dataIndex: 'to_number',
      render: (value) => {
        const num = value as string | null;
        return num ? <PhoneNumberDisplay phoneNumber={num} flagSize="sm" /> : '-';
      },
    },
    {
      key: 'provider_call_id',
      title: 'Call SID',
      dataIndex: 'provider_call_id',
      render: (value) => {
        const sid = value as string | null;
        return sid ? <span className="font-mono text-xs text-muted-foreground">{sid}</span> : '-';
      },
    },
    {
      key: 'started_at',
      title: 'Started At',
      dataIndex: 'started_at',
      sorter: true,
      render: (value) => formatTimestamp(value as string | null),
    },
    {
      key: 'ended_at',
      title: 'Ended At',
      dataIndex: 'ended_at',
      sorter: true,
      render: (value) => formatTimestamp(value as string | null),
    },
    {
      key: 'avg_latency',
      title: 'Avg Latency',
      render: (_value, record) => {
        const s = summarizeMetrics(record.metrics);
        return (
          <span className="tabular-nums text-sm">{formatSeconds(s?.avgLatencyS ?? null)}</span>
        );
      },
    },
    {
      key: 'llm_tokens',
      title: 'LLM Tokens',
      render: (_value, record) => {
        const s = summarizeMetrics(record.metrics);
        return <span className="tabular-nums text-sm">{formatCount(s?.totalTokens ?? null)}</span>;
      },
    },
    {
      key: 'tts_chars',
      title: 'TTS Chars',
      render: (_value, record) => {
        const s = summarizeMetrics(record.metrics);
        return <span className="tabular-nums text-sm">{formatCount(s?.totalChars ?? null)}</span>;
      },
    },
    {
      key: 'stt_audio',
      title: 'STT Audio',
      render: (_value, record) => {
        const s = summarizeMetrics(record.metrics);
        const ms = s?.totalSttAudioMs;
        return (
          <span className="tabular-nums text-sm">
            {ms == null || ms <= 0 ? '-' : formatAudioMs(ms)}
          </span>
        );
      },
    },
    {
      key: 'turns',
      title: 'Turns',
      render: (_value, record) => {
        const s = summarizeMetrics(record.metrics);
        return <span className="tabular-nums text-sm">{formatCount(s?.turnCount ?? null)}</span>;
      },
    },
  ];

  // Embedded mode drops the Agent column — every row is the same agent, so it's
  // noise. (It's pinned via ALWAYS_VISIBLE_COLUMN_KEYS, so filter it out here
  // rather than through the column-visibility popover.)
  const scopedColumns = agentId ? columns.filter((c) => c.key !== 'agent_name') : columns;

  const visibleColumns =
    visibleColumnKeys === 'all'
      ? scopedColumns
      : scopedColumns.filter(
          (c) =>
            ALWAYS_VISIBLE_COLUMN_KEYS.has(String(c.key)) || visibleColumnKeys.has(String(c.key)),
        );

  return (
    <div className="animate-page mx-auto flex h-full w-full max-w-6xl flex-col gap-4">
      {/* Embedded mode: the tab is already labeled "Call History" and lives in
          the agent editor, so drop the whole page header — heading, subtitle,
          and the call-count pill — and lead straight into the toolbar. */}
      {!agentId && (
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.34em] text-muted-foreground">
              Build
            </p>
            <div className="flex items-baseline gap-3">
              <h1 className="font-display text-[clamp(2rem,3.4vw,2.75rem)] font-semibold leading-none tracking-[-0.04em] text-foreground">
                Call History
              </h1>
              {!data.loading && data.total > 0 && (
                <span className="font-mono text-[13px] tabular-nums text-muted-foreground">
                  {data.total.toLocaleString()}
                </span>
              )}
            </div>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              View and filter your voice agent call logs
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <TokenSearchBar
          fields={tokenFields}
          value={searchTokens}
          onChange={handleSearchTokensChange}
          onClear={handleClearAll}
          showClear={hasActiveFilters}
          placeholder="Filter by field… (e.g. status:completed)"
          className="min-w-[240px] flex-1"
        />
        <div className="mx-0.5 hidden h-6 w-px shrink-0 bg-border sm:block" />
        <div className="flex items-center gap-2">
          <CustomButton
            type="default"
            size="sm"
            icon={<BarChart3 className="size-4" />}
            onClick={handleShowMetrics}
            aria-label="Show aggregated metrics for filtered calls"
          >
            Show Metrics
          </CustomButton>
          <CustomPopover
            open={columnFilterOpen}
            onOpenChange={setColumnFilterOpen}
            title="Visible columns"
            trigger={
              <CustomButton
                type="default"
                size="sm"
                icon={<Columns3 className="size-4" />}
                aria-label="Toggle column visibility"
              >
                Columns
                {hiddenColumnCount > 0 && (
                  <Badge className="ml-2 bg-primary/15 text-primary hover:bg-primary/15">
                    {hiddenColumnCount}
                  </Badge>
                )}
              </CustomButton>
            }
            footer={
              <>
                <CustomButton
                  type="text"
                  size="sm"
                  onClick={handleResetColumns}
                  disabled={draftColumnKeys.size === ALL_COLUMN_KEYS.length}
                >
                  Reset
                </CustomButton>
                <CustomButton type="primary" size="sm" onClick={handleApplyColumns}>
                  Apply
                </CustomButton>
              </>
            }
          >
            <div className="flex flex-col gap-4">
              {COLUMN_GROUPS.map((group) => {
                const groupKeys = group.columns.map((c) => c.key);
                const allOn = groupKeys.every((k) => draftColumnKeys.has(k));
                const groupId = `col-grp-${group.name.replace(/\s+/g, '-').toLowerCase()}`;
                return (
                  <div key={group.name} className="flex flex-col gap-1">
                    <label
                      htmlFor={groupId}
                      className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-[11px] font-bold uppercase tracking-wider text-foreground hover:bg-muted/50"
                    >
                      <Checkbox
                        id={groupId}
                        checked={allOn}
                        onCheckedChange={() => toggleDraftGroup(groupKeys)}
                      />
                      {group.name}
                    </label>
                    <div className="ml-[1.125rem] flex flex-col gap-0.5 border-l border-border pl-5">
                      {group.columns.map(({ key, label }) => (
                        <label
                          key={key}
                          htmlFor={`col-vis-${key}`}
                          className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                        >
                          <Checkbox
                            id={`col-vis-${key}`}
                            checked={draftColumnKeys.has(key)}
                            onCheckedChange={() => toggleDraftColumn(key)}
                            className="size-3.5"
                          />
                          <span>{label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </CustomPopover>
          <CustomButton
            type="default"
            size="sm"
            icon={<SlidersHorizontal className="size-4" />}
            onClick={() => setFilterDrawerOpen(true)}
            aria-label="Open filters"
            className={
              drawerFilterCount > 0
                ? 'border-primary/40 bg-primary/5 text-foreground hover:bg-primary/10'
                : undefined
            }
          >
            Filters
            {drawerFilterCount > 0 && (
              <Badge className="ml-2 bg-primary/15 text-primary tabular-nums hover:bg-primary/15">
                {drawerFilterCount}
              </Badge>
            )}
          </CustomButton>
        </div>
      </div>

      {metricsStripVisible && (
        <CallHistoryMetricsStrip
          data={metricsSummaryState.data}
          loading={metricsSummaryState.loading}
          onDismiss={handleHideMetrics}
        />
      )}

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={visibleColumns}
          dataSource={data.callLogs}
          rowKey="id"
          loading={data.loading}
          loadingLabel="Loading call logs"
          onRowClick={(record) =>
            // Embedded (agent-scoped) mode tags the detail URL with the current
            // agent Call History path so its back link returns here instead of
            // the global call history. `pathname` is query-free, so this can't
            // smuggle another `from`.
            router.push(
              agentId
                ? `/call-history/${record.id}?from=${encodeURIComponent(pathname)}`
                : `/call-history/${record.id}`,
            )
          }
          onSortChange={handleSortChange}
          pagination={{
            current: page,
            pageSize,
            total: data.total,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            onChange: handlePaginationChange,
          }}
          emptyState={
            <div className="flex flex-col items-center gap-5 py-14">
              <span className="inline-flex size-12 items-center justify-center rounded-xl border border-border bg-surface text-muted-foreground">
                <Phone className="size-5" strokeWidth={1.75} />
              </span>
              <div className="max-w-xs text-center">
                <p className="font-display text-[15px] font-semibold text-foreground">
                  No call logs found
                </p>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {hasActiveFilters
                    ? 'No calls match your current filters. Try adjusting or clearing them.'
                    : 'Call logs will appear here once your agents start handling calls.'}
                </p>
              </div>
              {hasActiveFilters && (
                <CustomButton type="default" size="sm" onClick={handleClearAll}>
                  <X className="size-3.5" />
                  Clear all filters
                </CustomButton>
              )}
            </div>
          }
        />
      </div>

      <CallHistoryFilterDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        value={filterState}
        facets={facetsState.facets}
        facetsLoading={facetsState.loading}
        onApply={handleApplyFilters}
        facetSections={facetSections}
      />
    </div>
  );
};

export default CallHistory;
