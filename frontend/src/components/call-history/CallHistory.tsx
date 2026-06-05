'use client';

import agentsAtom, { fetchAllAgentsAtom } from '@/atoms/AgentsAtom';
import callLogsAtom, { fetchCallLogs } from '@/atoms/CallLogAtom';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import {
  CustomButton,
  CustomDrawer,
  CustomPopover,
  CustomTable,
  CustomTooltip,
  PhoneNumberDisplay,
} from '@/components/shared';
import SelectInput from '@/components/shared/SelectInput';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import { CALL_STATUS_OPTIONS } from '@/lib/constants/filters';
import { getFilterValues } from '@/services/callLogService';
import { useAuthStore } from '@/stores/auth';
import type { CallLogFilterParam, CallLogQueryParams, CallLogRow } from '@/types/callLog';
import type { CustomTableColumn, CustomTableSortState, SelectOption } from '@/types/components';
import { buildGrafanaLogsUrl, isGrafanaConfigured } from '@/utils/grafana';
import { formatDuration, formatTimestamp } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { useAtom } from 'jotai';
import {
  BarChart3,
  CalendarDays,
  Columns3,
  MessageSquareText,
  Phone,
  ScrollText,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import CallDetailDrawer from './CallDetailDrawer';
import TranscriptionModal from './TranscriptionModal';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const STATUS_BADGE_CLASSES: Record<string, string> = {
  completed: 'bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/15 dark:text-emerald-400',
  in_progress: 'bg-amber-500/15 text-amber-600 hover:bg-amber-500/15 dark:text-amber-400',
  failed: 'bg-red-500/15 text-red-600 hover:bg-red-500/15 dark:text-red-400',
};

const formatSeconds = (v: number | null) => (v == null ? '-' : `${v.toFixed(2)}s`);
const formatCount = (v: number | null) => (v == null ? '-' : v.toLocaleString());

// Single source of truth for the column-visibility popover. Columns are
// grouped so the user can toggle a whole section in one click. The table
// itself doesn't reorder based on these groups — visibility just filters
// the existing column array in place.
// `agent_name` and `actions` are intentionally absent here: the Agent and
// Quick View columns are required for the table to be usable, so they're
// always rendered and not exposed as togglable in the UI.
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
      { key: 'turns', label: 'Turns' },
    ],
  },
];
const ALL_COLUMN_KEYS = COLUMN_GROUPS.flatMap((g) => g.columns.map((c) => c.key));

// Bounds for the avg-latency slider in the pipeline-filters drawer.
const MIN_LATENCY_SECONDS = 0;
const MAX_LATENCY_SECONDS = 5;
const LATENCY_STEP = 0.1;
const DEFAULT_LATENCY_RANGE: [number, number] = [MIN_LATENCY_SECONDS, MAX_LATENCY_SECONDS];
/** Columns that are pinned to the table regardless of popover selection. */
const ALWAYS_VISIBLE_COLUMN_KEYS = new Set<string>(['agent_name', 'actions']);

function summarizeMetrics(metrics: CallLogRow['metrics']) {
  if (!metrics) return null;
  const latencies = metrics.user_bot_latency.map((l) => l.latency);
  const avgLatencyS = latencies.length
    ? latencies.reduce((s, v) => s + v, 0) / latencies.length
    : null;
  const totalTokens = metrics.llm_usage.reduce((s, u) => s + u.total_tokens, 0);
  const totalChars = metrics.tts_usage.reduce((s, u) => s + u.characters, 0);
  const turnCount = metrics.turns.length;
  return { avgLatencyS, totalTokens, totalChars, turnCount };
}

const CallHistory: React.FC = () => {
  const router = useRouter();
  const [data] = useAtom(callLogsAtom);
  const [, doFetchCallLogs] = useAtom(fetchCallLogs);
  const [{ agentList }] = useAtom(agentsAtom);
  const [, doFetchAllAgents] = useAtom(fetchAllAgentsAtom);
  // Distinct LLM/STT/TTS model lists are scoped to the active org by the
  // backend; refetch whenever the active org changes so a tenant switch
  // doesn't leak the previous workspace's models into the dropdowns.
  const activeOrgId = useAuthStore((s) => s.activeOrgId);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [agentFilter, setAgentFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [llmModelFilter, setLlmModelFilter] = useState('all');
  const [sttModelFilter, setSttModelFilter] = useState('all');
  const [ttsModelFilter, setTtsModelFilter] = useState('all');
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [sttModels, setSttModels] = useState<string[]>([]);
  const [ttsModels, setTtsModels] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [startDateTime, setStartDateTime] = useState('');
  const [endDateTime, setEndDateTime] = useState('');
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [minTurns, setMinTurns] = useState('');
  const [maxTurns, setMaxTurns] = useState('');
  const [latencyRange, setLatencyRange] = useState<[number, number]>(DEFAULT_LATENCY_RANGE);

  // Column visibility — sentinel 'all' means every column is shown so a fresh
  // session doesn't need to enumerate keys. Drafts live inside the popover
  // until the user clicks Apply, mirroring the pipeline-filters drawer.
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

  // Drafts live inside the drawer until the user clicks Apply. They are seeded
  // from the applied state every time the drawer opens, and discarded when the
  // drawer is closed via the X / backdrop without applying.
  const [draftLlmModel, setDraftLlmModel] = useState('all');
  const [draftSttModel, setDraftSttModel] = useState('all');
  const [draftTtsModel, setDraftTtsModel] = useState('all');
  const [draftMinTurns, setDraftMinTurns] = useState('');
  const [draftMaxTurns, setDraftMaxTurns] = useState('');
  const [draftLatencyRange, setDraftLatencyRange] =
    useState<[number, number]>(DEFAULT_LATENCY_RANGE);

  useEffect(() => {
    if (filterDrawerOpen) {
      setDraftLlmModel(llmModelFilter);
      setDraftSttModel(sttModelFilter);
      setDraftTtsModel(ttsModelFilter);
      setDraftMinTurns(minTurns);
      setDraftMaxTurns(maxTurns);
      setDraftLatencyRange(latencyRange);
    }
  }, [
    filterDrawerOpen,
    llmModelFilter,
    sttModelFilter,
    ttsModelFilter,
    minTurns,
    maxTurns,
    latencyRange,
  ]);

  const turnsActive = minTurns.trim() !== '' || maxTurns.trim() !== '';
  const latencyActive =
    latencyRange[0] > MIN_LATENCY_SECONDS || latencyRange[1] < MAX_LATENCY_SECONDS;
  const activeModelFilterCount =
    (llmModelFilter !== 'all' ? 1 : 0) +
    (sttModelFilter !== 'all' ? 1 : 0) +
    (ttsModelFilter !== 'all' ? 1 : 0) +
    (turnsActive ? 1 : 0) +
    (latencyActive ? 1 : 0);

  const draftTurnsActive = draftMinTurns.trim() !== '' || draftMaxTurns.trim() !== '';
  const draftLatencyActive =
    draftLatencyRange[0] > MIN_LATENCY_SECONDS || draftLatencyRange[1] < MAX_LATENCY_SECONDS;
  const draftActiveCount =
    (draftLlmModel !== 'all' ? 1 : 0) +
    (draftSttModel !== 'all' ? 1 : 0) +
    (draftTtsModel !== 'all' ? 1 : 0) +
    (draftTurnsActive ? 1 : 0) +
    (draftLatencyActive ? 1 : 0);

  const handleResetDrafts = useCallback(() => {
    setDraftLlmModel('all');
    setDraftSttModel('all');
    setDraftTtsModel('all');
    setDraftMinTurns('');
    setDraftMaxTurns('');
    setDraftLatencyRange(DEFAULT_LATENCY_RANGE);
  }, []);

  const handleApplyDrafts = useCallback(() => {
    setLlmModelFilter(draftLlmModel);
    setSttModelFilter(draftSttModel);
    setTtsModelFilter(draftTtsModel);
    setMinTurns(draftMinTurns);
    setMaxTurns(draftMaxTurns);
    setLatencyRange(draftLatencyRange);
    setPage(1);
    setFilterDrawerOpen(false);
  }, [
    draftLlmModel,
    draftSttModel,
    draftTtsModel,
    draftMinTurns,
    draftMaxTurns,
    draftLatencyRange,
  ]);

  useEffect(() => {
    doFetchAllAgents().catch(handleApiError);
  }, [doFetchAllAgents]);

  useEffect(() => {
    // Single failure shouldn't blank all three dropdowns — fall back per column.
    const safe = (col: string) =>
      getFilterValues(col)
        .then((r) => r.values)
        .catch(() => [] as string[]);
    Promise.all([safe('llm_model'), safe('stt_model'), safe('tts_model')]).then(
      ([llm, stt, tts]) => {
        setLlmModels(llm);
        setSttModels(stt);
        setTtsModels(tts);
      },
    );
  }, [activeOrgId]);

  const agentOptions = useMemo<SelectOption[]>(
    () => [
      { value: 'all', label: 'All agents' },
      ...agentList.filter((a) => !!a.uuid).map((a) => ({ value: a.uuid, label: a.name })),
    ],
    [agentList],
  );

  const modelOptions = (label: string, values: string[]): SelectOption[] => [
    { value: 'all', label },
    ...values.map((v) => ({ value: v, label: v })),
  ];
  const llmModelOptions = useMemo(() => modelOptions('All LLM models', llmModels), [llmModels]);
  const sttModelOptions = useMemo(() => modelOptions('All STT models', sttModels), [sttModels]);
  const ttsModelOptions = useMemo(() => modelOptions('All TTS models', ttsModels), [ttsModels]);

  const [selectedCallLog, setSelectedCallLog] = useState<CallLogRow | null>(null);
  const [transcriptionCallLog, setTranscriptionCallLog] = useState<CallLogRow | null>(null);

  const params = useMemo<CallLogQueryParams>(() => {
    const q: CallLogQueryParams = {
      page_no: page,
      page_size: pageSize,
    };

    const filters: CallLogFilterParam[] = [];
    if (agentFilter !== 'all') {
      filters.push({ field: 'agent_id', operator: 'equal_to', value: agentFilter });
    }
    if (statusFilter !== 'all') {
      filters.push({ field: 'status', operator: 'in', value: [statusFilter] });
    }
    if (llmModelFilter !== 'all') {
      filters.push({ field: 'llm_model', operator: 'equal_to', value: llmModelFilter });
    }
    if (sttModelFilter !== 'all') {
      filters.push({ field: 'stt_model', operator: 'equal_to', value: sttModelFilter });
    }
    if (ttsModelFilter !== 'all') {
      filters.push({ field: 'tts_model', operator: 'equal_to', value: ttsModelFilter });
    }
    {
      const minN = parseInt(minTurns, 10);
      const maxN = parseInt(maxTurns, 10);
      const hasMin = Number.isFinite(minN);
      const hasMax = Number.isFinite(maxN);
      if (hasMin || hasMax) {
        // Bounds chosen so BETWEEN behaves as a half-open range when only one
        // side is provided. NULL turn_count (no metrics row) is excluded by
        // BETWEEN, which matches the intent "calls with N turns in range".
        filters.push({
          field: 'turn_count',
          operator: 'between',
          value: [hasMin ? minN : 0, hasMax ? maxN : 999999],
        });
      }
    }
    if (latencyActive) {
      // Same NULL-excluding semantics: rows without metrics or with an empty
      // user_bot_latency array are dropped when this filter is engaged.
      filters.push({
        field: 'avg_latency_seconds',
        operator: 'between',
        value: [latencyRange[0], latencyRange[1]],
      });
    }
    if (filters.length > 0) {
      q.filters = filters;
    }

    if (startDateTime) {
      q.start_date_time = new Date(startDateTime).toISOString();
    }
    if (endDateTime) {
      q.end_date_time = new Date(endDateTime).toISOString();
    }

    if (sortBy) {
      q.sort_by = sortBy;
      q.sort_order = sortOrder;
    }

    return q;
  }, [
    page,
    pageSize,
    agentFilter,
    statusFilter,
    llmModelFilter,
    sttModelFilter,
    ttsModelFilter,
    minTurns,
    maxTurns,
    latencyActive,
    latencyRange,
    startDateTime,
    endDateTime,
    sortBy,
    sortOrder,
  ]);

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

  const handleAgentFilter = useCallback((value: string) => {
    setAgentFilter(value);
    setPage(1);
  }, []);

  const handleStatusFilter = useCallback((value: string) => {
    setStatusFilter(value);
    setPage(1);
  }, []);

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

  const handleClearDates = useCallback(() => {
    setStartDateTime('');
    setEndDateTime('');
    setPage(1);
  }, []);

  const hasDates = startDateTime || endDateTime;

  // Sticky class applied to the first and last columns so the agent column
  // stays pinned on the left and the quick-view column stays pinned on the
  // right while the user scrolls the inner columns horizontally. `bg-card`
  // matches the table surface so scrolling content stays fully masked. The
  // row-level `hover:bg-muted/50` is translucent (50%), so applying it to
  // these pinned cells would let scrolled content bleed through — we
  // intentionally keep the sticky background opaque at all times.
  const STICKY_LEFT = 'sticky left-0 z-[1] bg-card border-r border-border';
  const STICKY_RIGHT = 'sticky right-0 z-[1] bg-card border-l border-border';

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
        const classes = STATUS_BADGE_CLASSES[status] ?? 'bg-muted text-muted-foreground';
        const label = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        return <Badge className={classes}>{label}</Badge>;
      },
    },
    {
      key: 'duration_seconds',
      title: 'Duration',
      dataIndex: 'duration_seconds',
      sorter: true,
      render: (value) => formatDuration(value as number | null),
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
      key: 'turns',
      title: 'Turns',
      render: (_value, record) => {
        const s = summarizeMetrics(record.metrics);
        return <span className="tabular-nums text-sm">{formatCount(s?.turnCount ?? null)}</span>;
      },
    },
    {
      key: 'actions',
      title: 'Quick View',
      className: STICKY_RIGHT,
      render: (_value, record) => (
        <div className="flex items-center justify-center gap-1.5">
          <CustomTooltip content="Transcription">
            <CustomButton
              type="default"
              size="icon-xs"
              disabled={!(record.transcript && record.transcript.length > 0)}
              onClick={(e) => {
                e.stopPropagation();
                setTranscriptionCallLog(record);
              }}
            >
              <MessageSquareText className="size-3.5" />
            </CustomButton>
          </CustomTooltip>
          <CustomTooltip content="View metrics">
            <CustomButton
              type="default"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                router.push(`/call-metrics/${record.id}`);
              }}
            >
              <BarChart3 className="size-3.5" />
            </CustomButton>
          </CustomTooltip>
          {isGrafanaConfigured() && (
            <CustomTooltip content="View logs">
              <CustomButton
                type="default"
                size="icon-xs"
                disabled={!record.trace_id}
                onClick={(e) => {
                  e.stopPropagation();
                  const url = buildGrafanaLogsUrl(record);
                  if (url) window.open(url, '_blank', 'noopener,noreferrer');
                }}
              >
                <ScrollText className="size-3.5" />
              </CustomButton>
            </CustomTooltip>
          )}
        </div>
      ),
    },
  ];

  const visibleColumns =
    visibleColumnKeys === 'all'
      ? columns
      : columns.filter(
          (c) =>
            ALWAYS_VISIBLE_COLUMN_KEYS.has(String(c.key)) || visibleColumnKeys.has(String(c.key)),
        );

  return (
    <div className="animate-page flex h-full flex-col gap-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Call History</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          View and filter your voice agent call logs
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SelectInput
          name="agent-filter"
          options={agentOptions}
          value={agentFilter}
          onValueChange={handleAgentFilter}
          placeholder="All agents"
          size="sm"
          triggerClassName="min-w-[200px]"
          searchable
          searchPlaceholder="Search agents..."
        />
        <SelectInput
          name="status-filter"
          options={CALL_STATUS_OPTIONS}
          value={statusFilter}
          onValueChange={handleStatusFilter}
          placeholder="All statuses"
          size="sm"
          triggerClassName="min-w-[160px]"
        />
        <div className="flex items-center gap-2">
          <div className="relative">
            <CalendarDays className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="datetime-local"
              value={startDateTime}
              onChange={(e) => {
                setStartDateTime(e.target.value);
                setPage(1);
              }}
              className={`h-9 rounded-md border border-input bg-background pl-9 pr-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground hover:border-ring focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 ${startDateTime ? 'text-foreground' : 'text-muted-foreground'}`}
            />
          </div>
          <span className="text-sm text-muted-foreground">to</span>
          <div className="relative">
            <CalendarDays className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="datetime-local"
              value={endDateTime}
              onChange={(e) => {
                setEndDateTime(e.target.value);
                setPage(1);
              }}
              className={`h-9 rounded-md border border-input bg-background pl-9 pr-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground hover:border-ring focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 ${endDateTime ? 'text-foreground' : 'text-muted-foreground'}`}
            />
          </div>
          {hasDates && (
            <CustomButton type="text" size="icon-sm" onClick={handleClearDates}>
              <X className="size-4 text-muted-foreground" />
            </CustomButton>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2">
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
                    {/* Tree-line indents the children and visually marks
                        them as members of the group above. */}
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
            aria-label="Open model filters"
          >
            Filter
            {activeModelFilterCount > 0 && (
              <Badge className="ml-2 bg-primary/15 text-primary hover:bg-primary/15">
                {activeModelFilterCount}
              </Badge>
            )}
          </CustomButton>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={visibleColumns}
          dataSource={data.callLogs}
          rowKey="id"
          loading={data.loading}
          onRowClick={(record) => setSelectedCallLog(record)}
          onSortChange={handleSortChange}
          pagination={{
            current: page,
            pageSize,
            total: data.total,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            onChange: handlePaginationChange,
          }}
          emptyState={
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="flex size-12 items-center justify-center rounded-xl bg-muted">
                <Phone className="size-6 text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-foreground">No call logs found</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Call logs will appear here once your agents start handling calls
                </p>
              </div>
            </div>
          }
        />
      </div>

      <CustomDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        title="Pipeline filters"
        description="Filter calls by the LLM, STT, or TTS model used in the pipeline."
        side="right"
        width="w-full sm:max-w-md"
        footer={
          <div className="flex items-center justify-between gap-2">
            <CustomButton
              type="text"
              size="sm"
              onClick={handleResetDrafts}
              disabled={draftActiveCount === 0}
            >
              Reset
            </CustomButton>
            <CustomButton type="primary" size="sm" onClick={handleApplyDrafts}>
              Apply
            </CustomButton>
          </div>
        }
      >
        <div className="flex flex-col gap-5 pt-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="llm-model-filter" className="text-xs font-medium text-muted-foreground">
              LLM model
            </label>
            <SelectInput
              name="llm-model-filter"
              options={llmModelOptions}
              value={draftLlmModel}
              onValueChange={setDraftLlmModel}
              placeholder="All LLM models"
              size="sm"
              searchable
              searchPlaceholder="Search LLM models..."
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="stt-model-filter" className="text-xs font-medium text-muted-foreground">
              STT model
            </label>
            <SelectInput
              name="stt-model-filter"
              options={sttModelOptions}
              value={draftSttModel}
              onValueChange={setDraftSttModel}
              placeholder="All STT models"
              size="sm"
              searchable
              searchPlaceholder="Search STT models..."
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="tts-model-filter" className="text-xs font-medium text-muted-foreground">
              TTS model
            </label>
            <SelectInput
              name="tts-model-filter"
              options={ttsModelOptions}
              value={draftTtsModel}
              onValueChange={setDraftTtsModel}
              placeholder="All TTS models"
              size="sm"
              searchable
              searchPlaceholder="Search TTS models..."
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-muted-foreground">Turns range</span>
            <div className="flex items-center gap-2">
              <input
                id="min-turns-filter"
                type="number"
                inputMode="numeric"
                min={0}
                value={draftMinTurns}
                onChange={(e) => setDraftMinTurns(e.target.value)}
                placeholder="From"
                aria-label="Minimum turns"
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground hover:border-ring focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
              />
              <span className="text-sm text-muted-foreground">to</span>
              <input
                id="max-turns-filter"
                type="number"
                inputMode="numeric"
                min={0}
                value={draftMaxTurns}
                onChange={(e) => setDraftMaxTurns(e.target.value)}
                placeholder="To"
                aria-label="Maximum turns"
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground hover:border-ring focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
              />
            </div>
            <p className="text-[11px] text-muted-foreground">
              Calls with no metrics record are excluded when this range is set.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Avg latency (s)</span>
              <span className="text-xs font-medium tabular-nums text-foreground">
                {draftLatencyRange[0].toFixed(1)}s — {draftLatencyRange[1].toFixed(1)}s
              </span>
            </div>
            <Slider
              min={MIN_LATENCY_SECONDS}
              max={MAX_LATENCY_SECONDS}
              step={LATENCY_STEP}
              value={draftLatencyRange}
              onValueChange={(values) => {
                // Radix Slider sends an array of thumb positions; coerce to a
                // sorted [min, max] tuple to keep the consumer shape stable.
                const [a = MIN_LATENCY_SECONDS, b = MAX_LATENCY_SECONDS] = values;
                setDraftLatencyRange(a <= b ? [a, b] : [b, a]);
              }}
              aria-label="Average latency range"
            />
            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
              <span>{MIN_LATENCY_SECONDS}s</span>
              <span>{MAX_LATENCY_SECONDS}s</span>
            </div>
          </div>
        </div>
      </CustomDrawer>

      <CallDetailDrawer
        open={!!selectedCallLog}
        onClose={() => setSelectedCallLog(null)}
        callLog={selectedCallLog}
      />

      <TranscriptionModal
        open={!!transcriptionCallLog}
        onClose={() => setTranscriptionCallLog(null)}
        transcript={transcriptionCallLog?.transcript ?? null}
        agentName={transcriptionCallLog?.agent_name ?? ''}
      />
    </div>
  );
};

export default CallHistory;
