'use client';

import callLogsAtom, { fetchCallLogs } from '@/atoms/CallLogAtom';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import { CustomButton, CustomTable, CustomTooltip, PhoneNumberDisplay } from '@/components/shared';
import SearchBar from '@/components/shared/SearchBar';
import SelectInput from '@/components/shared/SelectInput';
import { Badge } from '@/components/ui/badge';
import { AGENT_TYPE_OPTIONS, CALL_STATUS_OPTIONS } from '@/lib/constants/filters';
import type { CallLogFilterParam, CallLogQueryParams, CallLogRow } from '@/types/callLog';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import { buildGrafanaLogsUrl, isGrafanaConfigured } from '@/utils/grafana';
import { formatDuration, formatTimestamp } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { useAtom } from 'jotai';
import { BarChart3, CalendarDays, MessageSquareText, Phone, ScrollText, X } from 'lucide-react';
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

const CallHistory: React.FC = () => {
  const router = useRouter();
  const [data] = useAtom(callLogsAtom);
  const [, doFetchCallLogs] = useAtom(fetchCallLogs);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [agentTypeFilter, setAgentTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [startDateTime, setStartDateTime] = useState('');
  const [endDateTime, setEndDateTime] = useState('');

  const [selectedCallLog, setSelectedCallLog] = useState<CallLogRow | null>(null);
  const [transcriptionCallLog, setTranscriptionCallLog] = useState<CallLogRow | null>(null);

  const params = useMemo<CallLogQueryParams>(() => {
    const q: CallLogQueryParams = {
      page_no: page,
      page_size: pageSize,
    };

    const filters: CallLogFilterParam[] = [];
    if (search.trim()) {
      filters.push({ field: 'agent_name', operator: 'contains', value: search.trim() });
    }
    if (statusFilter !== 'all') {
      filters.push({ field: 'status', operator: 'in', value: [statusFilter] });
    }
    if (agentTypeFilter !== 'all') {
      filters.push({ field: 'agent_type', operator: 'in', value: [agentTypeFilter] });
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
    search,
    statusFilter,
    agentTypeFilter,
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

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    setPage(1);
  }, []);

  const handleStatusFilter = useCallback((value: string) => {
    setStatusFilter(value);
    setPage(1);
  }, []);

  const handleAgentTypeFilter = useCallback((value: string) => {
    setAgentTypeFilter(value);
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

  const columns: CustomTableColumn<CallLogRow>[] = [
    {
      key: 'agent_name',
      title: 'Agent',
      dataIndex: 'agent_name',
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
      key: 'actions',
      title: 'Quick View',
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
                router.push(`/call-metrics?call_id=${record.id}`);
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

  return (
    <div className="animate-page flex h-full flex-col gap-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Call History</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          View and filter your voice agent call logs
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SearchBar
          placeholder="Search by agent name..."
          value={search}
          onSearch={handleSearchChange}
          debounceMs={400}
          containerClassName="max-w-xs flex-1"
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
        <SelectInput
          name="agent-type-filter"
          options={AGENT_TYPE_OPTIONS}
          value={agentTypeFilter}
          onValueChange={handleAgentTypeFilter}
          placeholder="All types"
          size="sm"
          triggerClassName="min-w-[140px]"
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
