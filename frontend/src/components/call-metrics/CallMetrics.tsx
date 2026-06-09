'use client';

import callMetricsAtom, { fetchCallMetrics } from '@/atoms/CallMetricsAtom';
import MetricsModal from '@/components/call-history/MetricsModal';
import { PageHeader } from '@/components/layout/page-header';
import { CustomButton, CustomTable } from '@/components/shared';
import SearchBar from '@/components/shared/SearchBar';
import { getCallMetricsByCallId } from '@/services/callMetricsService';
import type {
  CallMetricsDetail,
  CallMetricsFilterParam,
  CallMetricsQueryParams,
  CallMetricsRow,
} from '@/types/callMetrics';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import { formatDuration, formatTimestamp } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { useAtom } from 'jotai';
import { BarChart3, CalendarDays, X } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

// Local to this page — the modal already has its own seconds-based formatMs
// in metrics/utils.ts; these handle the table-column units (milliseconds and
// seconds as numbers, optional null) so we keep them inline.
const formatMillis = (value: number | null): string => {
  if (value == null) return '-';
  return value < 1000 ? `${value.toFixed(0)}ms` : `${(value / 1000).toFixed(2)}s`;
};

const formatSeconds = (value: number | null): string => {
  if (value == null) return '-';
  return `${value.toFixed(3)}s`;
};

const formatNumber = (value: number | null): string => {
  if (value == null) return '-';
  return value.toLocaleString();
};

const CallMetrics: React.FC = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Deep-link from Call History puts ?call_id=<id> on the URL. URL is the
  // single source of truth — back/forward and Sidebar re-clicks all work.
  const callIdFilter = searchParams.get('call_id') ?? '';

  const [data] = useAtom(callMetricsAtom);
  const [, doFetchCallMetrics] = useAtom(fetchCallMetrics);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [startDateTime, setStartDateTime] = useState('');
  const [endDateTime, setEndDateTime] = useState('');

  const [selectedRow, setSelectedRow] = useState<CallMetricsRow | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<CallMetricsDetail | null>(null);

  // When a row is clicked we fetch the full detail (with all six per-sample
  // arrays) and open the modal once it arrives. The list endpoint only
  // returns summary scalars to keep the page payload small.
  useEffect(() => {
    if (!selectedRow) {
      setSelectedDetail(null);
      return;
    }
    let cancelled = false;
    getCallMetricsByCallId(selectedRow.call_id)
      .then((detail) => {
        if (!cancelled) setSelectedDetail(detail);
      })
      .catch((error) => {
        if (!cancelled) {
          handleApiError(error);
          setSelectedRow(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRow]);

  const closeMetricsModal = useCallback(() => {
    setSelectedRow(null);
    setSelectedDetail(null);
  }, []);

  const params = useMemo<CallMetricsQueryParams>(() => {
    const q: CallMetricsQueryParams = {
      page_no: page,
      page_size: pageSize,
    };

    const filters: CallMetricsFilterParam[] = [];
    if (callIdFilter) {
      filters.push({ field: 'call_id', operator: 'equal_to', value: callIdFilter });
    }
    if (search.trim()) {
      filters.push({ field: 'agent_name', operator: 'contains', value: search.trim() });
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
  }, [callIdFilter, page, pageSize, search, startDateTime, endDateTime, sortBy, sortOrder]);

  const refresh = useCallback(async () => {
    try {
      await doFetchCallMetrics(params);
    } catch (error) {
      handleApiError(error);
    }
  }, [doFetchCallMetrics, params]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
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

  const handleClearCallIdFilter = useCallback(() => {
    router.replace('/call-metrics');
    setPage(1);
  }, [router]);

  const hasDates = startDateTime || endDateTime;

  const columns: CustomTableColumn<CallMetricsRow>[] = [
    {
      key: 'agent_name',
      title: 'Agent',
      dataIndex: 'agent_name',
      sorter: true,
      render: (value) => (
        <span className="text-sm font-medium">{(value as string | null) || '-'}</span>
      ),
    },
    {
      key: 'started_at',
      title: 'Started At',
      dataIndex: 'started_at',
      sorter: true,
      render: (value) => formatTimestamp(value as string | null),
    },
    {
      key: 'duration_seconds',
      title: 'Duration',
      dataIndex: 'duration_seconds',
      sorter: true,
      render: (value) => formatDuration(value as number | null),
    },
    {
      key: 'avg_ttfb_ms',
      title: 'Avg TTFB',
      dataIndex: 'avg_ttfb_ms',
      render: (value) => formatMillis(value as number | null),
    },
    {
      key: 'avg_latency_s',
      title: 'Avg Latency',
      dataIndex: 'avg_latency_s',
      render: (value) => formatSeconds(value as number | null),
    },
    {
      key: 'total_tokens',
      title: 'Total Tokens',
      dataIndex: 'total_tokens',
      render: (value) => formatNumber(value as number | null),
    },
    {
      key: 'total_tts_chars',
      title: 'TTS Chars',
      dataIndex: 'total_tts_chars',
      render: (value) => formatNumber(value as number | null),
    },
    {
      key: 'turn_count',
      title: 'Turns',
      dataIndex: 'turn_count',
      render: (value) => String((value as number | null) ?? 0),
    },
  ];

  return (
    <div className="animate-page flex h-full flex-col gap-6">
      <PageHeader
        kicker="Call metrics"
        title="Call metrics."
        description="Per-call pipeline metrics — TTFB, latency, token usage, TTS characters and turns."
      />

      {callIdFilter && (
        <div className="flex w-fit items-center gap-2 rounded-full border border-border bg-card py-1 pl-3 pr-1 text-sm">
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Call
          </span>
          <span className="font-mono text-[13px] text-foreground">{callIdFilter.slice(0, 8)}…</span>
          <CustomButton type="text" size="icon-xs" onClick={handleClearCallIdFilter}>
            <X className="size-3.5 text-muted-foreground" />
          </CustomButton>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <SearchBar
          placeholder="Search by agent name..."
          value={search}
          onSearch={handleSearchChange}
          debounceMs={400}
          containerClassName="max-w-xs flex-1"
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
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={data.rows}
          rowKey="id"
          loading={data.loading}
          onRowClick={(record) => setSelectedRow(record)}
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
              <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-background">
                <BarChart3 className="size-6 text-foreground" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-foreground">No call metrics yet</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Metrics will appear here after your agents complete calls
                </p>
              </div>
            </div>
          }
        />
      </div>

      <MetricsModal
        open={!!selectedDetail}
        onClose={closeMetricsModal}
        metrics={selectedDetail}
        agentName={selectedRow?.agent_name ?? ''}
      />
    </div>
  );
};

export default CallMetrics;
